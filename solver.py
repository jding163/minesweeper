from sprites import *
import  copy
from collections import defaultdict
import numpy as np
from collections import Counter
import math
import itertools
import logging
from line_profiler import profile

# Set up logging
logging.basicConfig(
    filename='debug.log',            # File to write to
    filemode='w',                    # 'w' to overwrite, 'a' to append
    level=logging.DEBUG,             # Minimum logging level
    format='%(asctime)s - %(levelname)s - %(message)s'
)

import time
import probability as prob

paths_explored = 0
merge_encounters = 0

#MINECOUNT SEED = -75

class Region():
    def __init__(self, locs,locs_to_check):

        self.locs = list(locs)
        self.locs_to_check = locs_to_check
        self.groups = []
        self.group_sols = []
        self.group_counts = []
        self.sols_bit = []
        self.num_sols = 0
        self.freqs = {}
    def num_locs(self):
        return len(self.locs)
    def num_solutions(self):
        return len(self.sols_bit)
    def set_sols_bit(self,sols_bit):
        self.sols_bit=sols_bit

    def get_sols_as_sets(self):

        return [
            {loc for loc, bit in zip(self.locs, sol) if bit == 1}
            for sol in self.sols_bit
        ]
    def get_sols_as_bits(self,sols_set):
        return [
            [1 if loc in sol_set else 0 for loc in self.locs]
            for sol_set in sols_set
        ]

    def is_equal(self,region):
        return self.locs == region.locs and self.locs_to_check == region.locs_to_check and region.groups==self.groups
    
    def is_loc_in_region(self,loc):
        return loc in self.locs
    
    def is_subset_of_region(self,region):
        return set(self.locs).issubset(set(region.locs))
    
    def combine_region_data(regions):
        all_locs = []
        all_locs_to_check = []
        all_groups = []
        all_group_sols = [[]]
        all_group_counts = [1]

        for region in regions:
            all_locs += region.locs
            all_locs_to_check += region.locs_to_check
            all_groups += region.groups

            # Expand group_sols via Cartesian product
            all_group_sols = [
                sol1 + sol2
                for sol1 in all_group_sols
                for sol2 in region.group_sols
            ]

            # Expand group_counts via Cartesian product with product of counts
            all_group_counts = [
                c1 * c2
                for c1 in all_group_counts
                for c2 in region.group_counts
            ]

        return all_locs, all_locs_to_check, all_groups, all_group_sols, all_group_counts

    def merge_regions(self, r2):
        r1 = self
        combined_locs = r1.locs + r2.locs
        combined_locs_to_check = r1.locs_to_check + r2.locs_to_check
        r = Region(combined_locs,combined_locs_to_check)
        combined_groups = r1.groups + r2.groups
        r.groups = combined_groups
        combined_group_sols = list(itertools.product(r1.group_sols,r2.group_sols))
        for i,sol in enumerate(combined_group_sols):
            combined_sol = []
            for sub_sol in sol:
                combined_sol += sub_sol
            combined_group_sols[i] = combined_sol
        combined_counts = list(itertools.product(r1.group_counts,r2.group_counts))
        for i,counts in enumerate(combined_counts):
            combined_counts[i] = math.prod(counts)
        r.group_sols = combined_group_sols
        r.group_counts = combined_counts
        r.num_sols = sum(r.group_counts)
        r.freqs = get_minecount_freqs(r)
        return r

class Solver(Board):
    collected_seeds = []
    def __init__(self,first_click=(0,0),run_pygame=True):
        super().__init__(run_pygame=run_pygame)
        self.first_click = first_click
        self.nonfrontier_tiles = []
        self.regions_list = []
        self.region_freqs = []
        #self.populate(first_click)
        #self.reveal_tiles(first_click[0],first_click[1])
    def is_loc_candidate_for_analysis(self,loc):
        if loc not in self.nonfrontier_tiles:
            return True
        neighbor_coords = get_neighbors(loc)
        count_nonfrontier = 0
        count_frontier = 0
        for x,y in neighbor_coords:
            if (x,y) in self.nonfrontier_tiles:
                count_nonfrontier += 1
            elif self.tiles[x][y].is_unknown():
                x,y=loc
                count_frontier += 1
        return count_nonfrontier- count_frontier < 4
    
    def group_equivalent_tiles(self,region):
        locs = region.locs
        groups = set()
        for loc in locs:
            group = set()
            number_neighbors = set(tile.loc for tile in self.get_number_neighbor_tiles(loc))

            for other_loc in locs:
                other_neighbors = set(tile.loc for tile in self.get_number_neighbor_tiles(other_loc))

                if number_neighbors == other_neighbors:
                    group.add(other_loc)
            groups.add(frozenset(group))
        sorted_groups = [sorted(group, key=lambda t: (t[0], t[1])) for group in groups]

        sorted_groups.sort(key=lambda group: (group[0][0], group[0][1]))
        return sorted_groups
    


    # flags neighbors if they are known to be mines
    def flag_neighbors(self,loc):
        neighbor_mines = self.tiles[loc[0]][loc[1]].get_adj_mines()
        neighbor_unknowns = 0
        neighbors = self.get_neighbor_tiles(loc)
        for neighbor in neighbors:
            neighbor_flagged = neighbor.is_flagged()
            neighbor_revealed = neighbor.is_revealed()
            if neighbor_flagged:
                neighbor_mines -=1
            elif not neighbor_revealed:
                neighbor_unknowns += 1
        if neighbor_unknowns == neighbor_mines:
            for neighbor in neighbors:
                neighbor_revealed = neighbor.is_revealed()
                neighbor_flagged = neighbor.is_flagged()
                if not neighbor_revealed and not neighbor_flagged:
                    self.toggle_flag_at_loc(neighbor.row,neighbor.col)
    
    def flag_board(self):
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                if self.tiles[row][col].is_revealed():
                    self.flag_neighbors((row,col))
    
    def chord_board(self):
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                if self.tiles[row][col].is_revealed():
                    self.chord((row,col))

    def solve_trivial_and_open(self):
        init_mines = self.flag_count
        init_revealed = self.num_revealed
        prev_mines = init_mines
        prev_revealed = init_revealed
        self.flag_board()
        self.chord_board()
        while self.flag_count != prev_mines or self.num_revealed != prev_revealed:
            self.flag_board()
            self.chord_board()
            prev_revealed = self.num_revealed
            prev_mines = self.flag_count
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                if self.tiles[row][col].is_revealed():
                    self.tiles[row][col].prob_mine_local = 0
                    if self.tiles[row][col].type is OPENING:
                        self.tiles[row][col].prob_opening = 1
                    else:
                        self.tiles[row][col].prob_opening = 0
                elif self.tiles[row][col].is_flagged():
                    self.tiles[row][col].prob_mine_local = 0
                    self.tiles[row][col].prob_opening = 0
        return not ((init_mines == prev_mines) and (prev_revealed == init_revealed)) # solution found or not
        
    def get_ccs(self):
        adj_sets = []
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                tile = self.tiles[row][col]
                if tile.type == NUMBER:
                    neighbors = self.get_neighbor_tiles((row,col))
                    adj_set = set()
                    for neighbor in neighbors:
                        if neighbor.is_unknown():
                            adj_set.add((neighbor.row,neighbor.col))
                    if len(adj_set) > 0: 
                        adj_sets.append(adj_set) 
        merged = merge_sets(adj_sets)
        return merged
    
    def convert_ccs_to_regions(self,ccs):
        regions = []
        for cc in ccs:
            cc,locs_to_check = self.optimize_backtrack_order(cc)
            cc = sorted(cc,key=lambda coord: (coord[0], coord[1]))
            regions.append(Region(cc,locs_to_check))
        return regions
    
    def get_regions(self):
        ccs = self.get_ccs()
        regions = self.convert_ccs_to_regions(ccs)
        return regions
    
    def get_region_index_with_loc(self,loc):
        for i,r in enumerate(self.regions_list):
            if loc in r.locs:
                return i
        return -1
    def verify_region(self, region):
        for loc in region.locs_to_check:
            tile = self.tiles[loc[0]][loc[1]]


            # Gather the relevant neighboring tiles (including the tile itself if needed)
            neighbors = self.get_neighbor_tiles((tile.row, tile.col))

            unknown_count = 0
            mine_count = 0
            for neighbor in neighbors:
                if neighbor.type == MINE:
                    mine_count += 1
                elif neighbor.type == UNKNOWN:
                    unknown_count+=1

            target_mines = tile.num_adj_mines

            # Check for constraint violation
            if mine_count > target_mines:
                return False
            if unknown_count == 0 and mine_count != target_mines:
                return False

        return True
    
    def verify_neighbors_of_loc(self,tiles_to_check):
        for tile in tiles_to_check:
            # Gather the relevant neighboring tiles
            neighbors = self.get_neighbor_tiles((tile.row,tile.col))

            # Count tile types only once
            unknown_count = 0
            mine_count = 0
            for neighbor in neighbors:
                if neighbor.type == MINE:
                    mine_count += 1
                elif neighbor.type == UNKNOWN:
                    unknown_count += 1

            target_mines = tile.num_adj_mines
            # Check for constraint violation
            if mine_count > target_mines:
                return False
            if unknown_count + mine_count < target_mines:
                return False

        return True

    
    def merge_multiple_regions(self, regions):
        if not regions:
            return None

        locs, locs_to_check, groups, group_sols, group_counts = Region.combine_region_data(regions)
        
        r = Region(locs, locs_to_check)
        r.groups = groups
        r.group_sols = group_sols
        r.group_counts = group_counts
        r.num_sols = sum(group_counts)
        r.freqs = get_minecount_freqs(r)
        return r
    
    def verify_group_sol(self,sol,region):
        self.inject_group_sol(sol,region)
        valid = False
        if self.verify_region(region):
            valid = True
        self.undo_sol_inject(region)
        return valid

    def get_sol_counts(regions,nonfrontier_tiles,flag_count):
        local_freqs = [region.freqs for region in regions]
        
        global_freqs = prob.convolve_freqs(local_freqs)
        if len(global_freqs) == 0:
            mines_nonfrontier = GSM.mine_count - flag_count
            num_sols_for_nonfrontier = math.comb(len(nonfrontier_tiles),mines_nonfrontier)
            return {0:num_sols_for_nonfrontier}
        sols_per_mines_in_frontier = defaultdict(int)
        for num_mines,freq in global_freqs.items():
            
            mines_nonfrontier = GSM.mine_count - flag_count - num_mines
            if mines_nonfrontier >=0:
                num_sols_for_nonfrontier = math.comb(len(nonfrontier_tiles),mines_nonfrontier)
                sols_per_mines_in_frontier[num_mines] = num_sols_for_nonfrontier * freq
        
        return sols_per_mines_in_frontier

    def get_sol_counts_at_loc_for_val(self,loc,val):
        x,y = loc
        tile = self.tiles[x][y]
        orig_val_at_loc = tile.num_adj_mines
        tile.num_adj_mines = val
        tile.type = NUMBER
        regions = self.get_regions()
        num_safe = 0
        regions_to_solve = []
        regions_with_sols = []
        for r1 in regions:
            solved = False
            for r2 in self.regions_list:
                if r1.is_equal(r2):
                    regions_with_sols.append(r2)
                    solved = True
                    break
            if not solved:
                regions_to_solve.append(r1)

        for region in regions_to_solve:
            groups = self.group_equivalent_tiles(region)
            groups = self.order_groups_by_information(groups)
            region.groups = groups
            group_sols = self.find_solutions_group(region,groups)
            #board is not solvable
            if len(group_sols) == 0:
                tile.num_adj_mines = orig_val_at_loc
                tile.type = UNKNOWN
                return 0,0,0

            group_probs,group_counts = prob.calc_probs_from_grouped_sols(groups,group_sols)
            for i in range(len(group_probs)):
                if group_probs[i] == 0:
                    num_safe += len(groups[i])
            
            region.group_sols = group_sols
            region.group_counts = group_counts
            region.num_sols = sum(group_counts)
            region.freqs = get_minecount_freqs(region)
            regions_with_sols.append(region)
        frontier_tiles = set()
        for r in regions_with_sols:
            for loc in r.locs:
                frontier_tiles.add(loc)
        nonfrontier_tiles = []
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                if self.get_type_at_loc((row,col)) == UNKNOWN and (row,col) not in frontier_tiles:
                    nonfrontier_tiles.append((row,col))
        sols_per_mines_in_frontier = Solver.get_sol_counts(regions_with_sols,nonfrontier_tiles,self.flag_count)
        total_count = sum(sols_per_mines_in_frontier.values())
        if len(regions_to_solve) == 0:
            mines_left = len(self.mines) - self.flag_count
            tile.num_adj_mines = orig_val_at_loc
            tile.type = UNKNOWN
            return total_count, mines_left/len(nonfrontier_tiles)

        probs = []
        merged_regions = regions_with_sols[0]
        for i in range(1,len(regions_with_sols)):
            merged_regions = merged_regions.merge_regions(regions_with_sols[i])
        for region in regions_with_sols:
            groups = region.groups
            group_probs = []
            for i in range(len(groups)):
                group = groups[i]
                group_prob = prob.calc_global_prob_for_group(merged_regions,group,sols_per_mines_in_frontier)
                group_probs.append(group_prob)
            min_prob = min(group_probs)
            probs.append(min_prob)

        best_prob = min(probs)
        if best_prob > 0:
            local_freqs = [region.freqs for region in regions_with_sols]
            global_freqs = prob.convolve_freqs(local_freqs)        
            num_sols_total = sum(global_freqs.values())
            prob_dist = {mc: num_sols_for_mc / num_sols_total for mc, num_sols_for_mc in global_freqs.items()}
            mines_left = len(self.mines) - self.flag_count
            prob_for_nonfrontier_tiles = prob.calc_prob_for_nonfrontier_tiles(prob_dist,mines_left,len(self.nonfrontier_tiles))
            best_prob = min(prob_for_nonfrontier_tiles,best_prob)

        tile.num_adj_mines = orig_val_at_loc
        tile.type = UNKNOWN
        return total_count,best_prob, num_safe


        




    def find_solutions_group(self,region,groups):
        if region.num_locs() == 0:
            return
        sols = []
        constraint_tracker = {}
        for group in groups:
            loc = group[0]
            neighbors = self.get_neighbor_tiles(loc)
            neighbors = [n for n in neighbors if n.loc in region.locs_to_check]
            constraint_tracker[loc] = neighbors

        # count flagged mines from previous play
        mine_count = 0 # includes flagged mines and unflagged mines deduced from prior calls to find_solution
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                if self.get_type_at_loc((row,col)) is MINE: 
                    mine_count += 1 
        index = 0
        group = groups[index]
        for i in range(len(group)):
            self.inject_num(group[i])
        for total_mines in range(len(group)+1):
            if total_mines > 0:
                self.inject_mine(group[total_mines-1])
            tiles_to_check = constraint_tracker[group[0]]
            if self.verify_neighbors_of_loc(tiles_to_check):
                curr_sol = [total_mines]
                self.find_solutions_group_helper(region,groups,sols,index + 1,mine_count + total_mines,constraint_tracker,curr_sol)
        for i in range(len(group)):
            self.undo_inject(group[i])

        return sols
    
    def find_solutions_group_helper(self,region,groups,sols,index,mine_count,constraint_tracker,curr_sol):
        if mine_count > len(self.mines):
            return
        if index == len(groups): # valid solution found
            sols.append(curr_sol[:])
            return
            # #if self.verify_solution(region):
            #     sol = []
            #     for group in groups:
            #         num_mines = 0
            #         for i in range(len(group)):
            #             x,y = group[i]
            #             curr = self.tiles[x][y]
            #             if curr.type is MINE:
            #                 num_mines +=1
            #         sol.append(num_mines)

            #     sols.append(sol)
        else:
            group = groups[index]
            for i in range(len(group)):
                self.inject_num(group[i])
            for total_mines in range(len(group)+1):
                if total_mines > 0:
                    self.inject_mine(group[total_mines-1])
                tiles_to_check = constraint_tracker[group[0]]
                if self.verify_neighbors_of_loc(tiles_to_check):
                    curr_sol.append(total_mines)
                    self.find_solutions_group_helper(region,groups,sols,index + 1,mine_count + total_mines,constraint_tracker,curr_sol)
                    curr_sol.pop()
            for i in range(len(group)):
                self.undo_inject(group[i])
            


    def find_solutions(self,region):
        #print(locs)
        if region.num_locs() == 0:
            return
        sols = []

        loc = region.locs[0]

        # count flagged mines from previous play
        mine_count = 0 # includes flagged mines and unflagged mines deduced from prior calls to find_solution
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                if self.get_type_at_loc((row,col)) is MINE: 
                    mine_count += 1 

        if self.get_type_at_loc(loc) is not UNKNOWN:
            # don't increment mine count even if loc contains a flag; it was already counted 
            self.find_solutions_helper(region,sols,1,mine_count) 
        else:
            self.inject_mine(loc)
            if self.verify_region(region):
                self.find_solutions_helper(region,sols,1,mine_count+1)
            self.inject_num(loc)
            if self.verify_region(region):
                self.find_solutions_helper(region,sols,1,mine_count)
            self.undo_inject(loc)
        return sols


    def find_solutions_helper(self,region,sols,index,mine_count):
        global paths_explored
        paths_explored += 1
        if mine_count > len(self.mines):
            return
            
        if index == region.num_locs(): # valid solution found
            #if self.verify_solution(region):
                sol = []
                for x,y in region.locs:
                    curr = self.tiles[x][y]
                    if curr.type is MINE:
                        sol.append(1)
                    else:
                        sol.append(0)
                sols.append(sol)
        else:
            loc = region.locs[index]
            if self.get_type_at_loc(loc) is MINE:
                self.find_solutions_helper(region,sols,index+1,mine_count+1)
            elif self.get_type_at_loc(loc) is NUMBER:
                self.find_solutions_helper(region,sols,index+1,mine_count)
                
            #b = copy.deepcopy(self)
            #b = timer.timed_deepcopy(self)
            else:
                self.inject_mine(loc)
                if self.verify_region(region):
                    self.find_solutions_helper(region,sols,index+1,mine_count+1)
                self.inject_num(loc)
                if self.verify_region(region):
                    self.find_solutions_helper(region,sols,index+1,mine_count)
                self.undo_inject(loc)

    def find_solutions_subdiv(self,region,unsolved_locs=None):

        split = region.num_locs()//5
        subdivs = subdivide_locs(region.locs,split)
        subdiv_set = set()
        for s in subdivs:
            subdiv_set = set(s) | subdiv_set
        #print(subdivs)
        subdivs = [Region(subdiv,region.locs_to_check) for subdiv in subdivs]
        if unsolved_locs is not None:
            unsolved_subdivs = subdivide_locs(unsolved_locs,split)
            unsolved_subdivs = [Region(subdiv,region.locs_to_check) for subdiv in unsolved_subdivs]
            subdivs = unsolved_subdivs + subdivs
        sols_to_merge = []
        for subdiv in subdivs:
            subdiv.set_sols_bit(self.find_solutions(subdiv))
            sols_set = subdiv.get_sols_as_sets()
            sols_to_merge.append(sols_set)

        #print(sols_to_merge)
        merged_sols,merged_subdiv = self.merge_and_validate(region, sols_to_merge,subdivs)
        assert set(merged_subdiv.locs) == set(region.locs)

        valid_sols_bit = region.get_sols_as_bits(merged_sols)
        return valid_sols_bit

    def merge_and_validate(self, region, sols_to_merge, subdivs):
        if len(sols_to_merge) == 1:
            return sols_to_merge[0], subdivs[0]

        # Divide
        mid = len(sols_to_merge) // 2
        left_sols, left_subdiv = self.merge_and_validate(region, sols_to_merge[:mid], subdivs[:mid])
        right_sols, right_subdiv = self.merge_and_validate(region, sols_to_merge[mid:], subdivs[mid:])
        
        # Merge subdiv regions
        merged_subdiv = Region(left_subdiv.locs + right_subdiv.locs, region.locs_to_check)
        
        # Merge solutions
        start=time.time()
        merged_sols = []
        for lsol in left_sols:
            for rsol in right_sols:
                combined = lsol | rsol

                for loc in merged_subdiv.locs:
                    if loc in combined:
                        self.inject_mine(loc)
                    else:
                        self.inject_num(loc)
                valid = self.verify_region(merged_subdiv)
                if valid:
                    merged_sols.append(combined)
                for loc in merged_subdiv.locs:
                    self.undo_inject(loc)
        return merged_sols, merged_subdiv
                    
    def mark_group_probs(self,groups,group_probs):
        for i in range(len(groups)):
            group = groups[i]
            length = len(group)
            for j in range(length):
                x,y = group[j]
                self.tiles[x][y].prob_mine_local = group_probs[i]/length

    def mark_tile_probs(self,locs,sols):
        mine_locs = []
        safe_locs = []
        probs = get_probs(sols)
        for i in range(len(probs)):
            x,y = locs[i]
            self.tiles[x][y].prob_mine_local = probs[i]
            if probs[i] == 0:
                safe_locs.append((x,y))
            elif probs[i] == 1:
                mine_locs.append((x,y))
        return safe_locs, mine_locs
    

    def update_solutions_with_new_constraints(self,region,updated_region):
        if region.locs != updated_region.locs or region.is_equal(updated_region):
            return
        region.locs_to_check = updated_region.locs_to_check
        new_sols = []
        for sol in region.group_sols:
            if(self.verify_group_sol(sol,region)):
                new_sols.append(sol)
        region.group_sols = new_sols

    def merge_region_with_existing_regions(self,region,existing_subregions):
        sols_to_merge = []
        subdivs = []
        solved_locs = set()

        for r in existing_subregions:
            sols_set = r.get_sols_as_sets()
            sols_to_merge.append(sols_set)
            subdivs.append(r)
            for loc in r.locs:
                solved_locs.add(loc)
        unsolved_locs = set(region.locs)-solved_locs
        if unsolved_locs:
            unsolved_region = self.convert_ccs_to_regions([unsolved_locs]).pop()

            unsolved_region.set_sols_bit(self.find_solutions(unsolved_region))
            sols_set = unsolved_region.get_sols_as_sets()
            sols_to_merge.append(sols_set)
            subdivs.append(unsolved_region)
        merged_sols,merged_subdiv = self.merge_and_validate(region, sols_to_merge,subdivs)
        assert set(merged_subdiv.locs) == set(region.locs)          
        merged_region = Region(region.locs, region.locs_to_check)
        valid_sols_bit = merged_region.get_sols_as_bits(merged_sols)            
        merged_region.set_sols_bit(valid_sols_bit)
        return merged_region
    def solve_exhaustive(self,merge=True):
        global merge_encounters
        ccs = self.get_ccs()
        regions = self.convert_ccs_to_regions(ccs)
        for region in regions:
            groups = self.group_equivalent_tiles(region)
            groups = self.order_groups_by_information(groups)
            region.groups = groups
        self.start_time = time.time()
        safe_locs = []
        mine_locs = []
        for region in regions:
            region_solved = self.check_for_existing_solutions_in_set(region,self.regions_list)
            if region_solved is not None and region_solved.is_equal(region):
                continue
            else:
                subregions = []
                remaining = set()

                for subregion in self.regions_list:
                    if subregion.is_subset_of_region(region):
                        subregions.append(subregion)
                    else:
                        remaining.add(subregion)
                if len(subregions) < 0:
                    merge_encounters +=1
                    if merge:
                        merged_region = self.merge_region_with_existing_regions(region,subregions)
                        self.mark_tile_probs(merged_region.locs,merged_region.sols_bit)

                        self.regions_list = remaining
                        self.regions_list.append(merged_region)
                    else:
                        if region.num_locs() <=10:
                            sols = self.find_solutions(region)
                            self.mark_tile_probs(region.locs,sols)
                            region.sols_bit = sols
                            self.regions_list.append(region)

                        else:
                            #start=time.time()
                            sols = self.find_solutions_subdiv(region)
                            self.mark_tile_probs(region.locs,sols)
                            region.sols_bit = sols
                            self.regions_list.append(region)
                            
                            #print(time.time()-start)

                        
                    

                else:
                    if region.num_locs() <=100:
                        start = time.time()

                        groups = region.groups
                        group_sols = self.find_solutions_group(region,groups)
                        group_probs,group_counts = prob.calc_probs_from_grouped_sols(groups,group_sols)

                        for i in range(len(groups)):
                        
                            group = groups[i]
                            length = len(group)
                            for j in range(length):
                                prob_tile = group_probs[i]/length
                                x,y = group[j]
                                self.tiles[x][y].prob_mine_local = prob_tile
                                if prob_tile == 1:
                                    mine_locs.append((x,y))
                                elif prob_tile == 0:
                                    safe_locs.append((x,y))
                        region.group_sols = group_sols
                        region.group_counts = group_counts
                        region.num_sols = sum(group_counts)
                        region.freqs = get_minecount_freqs(region)
                        self.regions_list.append(region)

                    else:
                        #start=time.time()
                        sols = self.find_solutions_subdiv(region)
                        self.mark_tile_probs(region.locs,sols)
                        region.sols_bit = sols
                        self.regions_list.append(region)
                        #print(time.time()-start)
        return safe_locs, mine_locs                


    def solve_exhaustive_and_open(self):
        #print(self.flag_count)

        safe_locs, mine_locs=self.solve_exhaustive()
        info_found = self.open_info(safe_locs,mine_locs)

        # self.solve_exhaustive()
        # info_found = self.open_known_tiles()
        regions = self.get_regions()
        updated = []

        for region in self.regions_list:
            
            matching = False
            for r in regions:
                if set(r.locs) == set(region.locs) and set(r.locs_to_check) == set(region.locs_to_check):
                    matching=True
                    break
            if matching:
                updated.append(region)
        self.regions_list = updated


        return info_found

                            
    def open_remaining(self):
        if self.flag_count == GSM.mine_count:
            for row in range(GSM.rows):
                for col in range(GSM.cols):
                    self.reveal_tiles(row,col)


    def inject_mine(self,loc):
        tile = self.tiles[loc[0]][loc[1]]
        tile.set_type(MINE)

    def inject_num(self,loc):
        self.tiles[loc[0]][loc[1]].set_type(NUMBER)

    def undo_inject(self,loc):
        self.tiles[loc[0]][loc[1]].set_type(UNKNOWN)

    def inject_bit_solution(self,sol,region):
        locs = region.locs
        for i in range(len(locs)):
            if sol[i] == 1:
                self.inject_mine(locs[i])
            else:
                self.inject_num(locs[i])
    def inject_group_sol(self,sol,region):
        groups = region.groups
        for i in range(len(groups)):
            group = groups[i]
            mines_in_group = sol[i]
            for j in range(len(group)):
                if j < mines_in_group:
                    self.inject_mine(group[j])
                else:
                    self.inject_num(group[j])


    def undo_sol_inject(self,region):
        locs = region.locs
        for i in range(len(locs)):
            self.undo_inject(locs[i])

    def verify_board(self):
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                curr = self.tiles[row][col]
                if curr.is_revealed():
                    neighbors = self.get_neighbor_tiles((row,col))
                    neighbor_types = {UNKNOWN: 0, MINE: 0, NUMBER: 0, OPENING: 0}
                    for neighbor in neighbors:
                        neighbor_types[neighbor.type] += 1
                    if neighbor_types[MINE] > curr.get_adj_mines() or (neighbor_types[UNKNOWN] == 0 and neighbor_types[MINE] != curr.get_adj_mines()):
                        return False
                        
        return True
    
    def score_group(self,group):
        score = 0
        number_neighbors = set()
        for (x,y) in group:
            neighbors = self.get_neighbor_tiles((x, y))
            for n in neighbors:
                if n.type == NUMBER:
                    number_neighbors.add(n.loc)



        score = len(number_neighbors)
        return score
    

    def order_groups_by_information(self,groups):
        #print(groups)
        # random_groups = random.sample(groups,k=len(groups))
        # return random_groups
        # return groups
        # Sort groups to ensure deterministic iteration
        groups = sorted(groups, key=lambda g: sorted(g))

        # Step 1: Compute group scores
        group_scores = {}
        for group in groups:
            group_key = tuple(sorted(group))  
            group_scores[group_key] = self.score_group(group)

        ordered = []
        visited_keys = set()

        # Step 2: Start with best-scoring group, break ties by coordinate
        start_key = max(group_scores.keys(), key=lambda g: (group_scores[g], g))
        ordered.append(list(start_key))
        visited_keys.add(start_key)

        # Step 3: Greedy deterministic expansion
        while len(visited_keys) < len(groups):
            current_tiles = {t for group in ordered for t in group}
            frontier_keys = set()

            for group in groups:
                group_key = tuple(sorted(group))
                if group_key in visited_keys:
                    continue
                if any(any(n in current_tiles for n in get_neighbors(t)) for t in group):
                    frontier_keys.add(group_key)

            if frontier_keys:
                next_key = max(frontier_keys, key=lambda g: (group_scores[g], g))
            else:
                remaining_keys = set(group_scores.keys()) - visited_keys
                next_key = max(remaining_keys, key=lambda g: (group_scores[g], g))

            ordered.append(list(next_key))
            visited_keys.add(next_key)
        return ordered


        
    def optimize_backtrack_order(self,locs):

        constraint_map = defaultdict(set)  # clue -> set of (x, y)

        # tile_neighbors: maps each tile to other tiles it shares a constraint with
        tile_neighbors = defaultdict(set)

        for loc in locs:
            neighbors = self.get_neighbor_tiles(loc)
            for neighbor in neighbors:
                if neighbor.type is NUMBER:
                    constraint_map[(neighbor.row,neighbor.col)].add(loc)

        # Build tile_neighbors from constraints
        for tiles in constraint_map.values():
            sorted_tiles = sorted(tiles)  # ensure deterministic pairings
            for i, a in enumerate(sorted_tiles):
                for b in sorted_tiles[i + 1:]:
                    tile_neighbors[a].add(b)
                    tile_neighbors[b].add(a)
        order = sorted(locs,key=lambda coord: (coord[0], coord[1]))
        locs_to_check = list(constraint_map.keys())
        return order, locs_to_check
    
    def check_for_existing_solutions_in_set(self, region,set_to_check):
        for r in set_to_check:
            if set(r.locs) == set(region.locs):
                return r
        return None
    # assume all known mines are flagged
    # assume that solve_board() was called previously and failed
    def solve_endgame(self):
        regions = self.get_regions()

        #assert(len(regions) == len(self.regions_list))
        min_flags = 0
        max_flags = 0

        frontier_tiles = set()
        regions = self.get_regions()
        for region in regions:
            for loc in region.locs:
                frontier_tiles.add(loc)


        nonfrontier_tiles = []
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                if self.get_type_at_loc((row,col)) == UNKNOWN and (row,col) not in frontier_tiles:
                    nonfrontier_tiles.append((row,col))
        self.nonfrontier_tiles = nonfrontier_tiles

        remaining_mines = GSM.mine_count-self.flag_count

        safe_locs = []
        mine_locs = []
        if remaining_mines == 0:
            #Solver.collected_seeds.append(self.seed)
            #return nonfrontier_tiles, []
            for x,y in nonfrontier_tiles:
                tile = self.tiles[x][y]
                tile.prob_mine_local = 0
                safe_locs.append((x,y))
            return safe_locs,mine_locs
        
        region_min={}
        region_max={}
        self.region_freqs = []

        for region in self.regions_list:
            freqs = region.freqs

            local_min = min(freqs)
            local_max = max(freqs)
            region_min[region] = local_min
            region_max[region] = local_max
            min_flags += local_min
            max_flags += local_max

        if max_flags + len(nonfrontier_tiles) == remaining_mines:
            #Solver.count += 1
            #for region in regions:
            for region in self.regions_list:

            #     if region not in regions:
            #         continue
                local_max = region_max[region]
                valid_sols = [sol for sol in region.group_sols if sum(sol) == local_max]
                # print('valid_sols:',valid_sols)
                #valid_sols = [sol for sol in region.sols_bit if sum(sol) == local_max]

                groups = region.groups
                group_probs,_ = prob.calc_probs_from_grouped_sols(groups,valid_sols)
                self.mark_group_probs(groups,group_probs)
            self.mark_tile_probs(nonfrontier_tiles,[[1] * len(nonfrontier_tiles)])
            for x,y in nonfrontier_tiles:
                # tile = self.tiles[x][y]
                mine_locs.append((x,y))
            #group_probs = [group_probs[i]/len(groups[i]) for i in range(len(group_probs))]
            for i in range(len(groups)):
                gp = group_probs[i]/len(groups[i])
                if gp == 1:
                    for x,y in groups[i]:
                        mine_locs.append((x,y))
                elif gp == 0:
                    for x,y in groups[i]:
                        safe_locs.append((x,y))
            # if any(element in (0, 1) for element in group_probs):
            #     return True
        # all non-border tiles are safe, solution uses min amount of mines
        elif min_flags == remaining_mines:
            #Solver.count += 1
            # Solver.collected_seeds.append(self.seed)
            # print('here')
            # for region in regions:
                # print(region.locs)
            for region in self.regions_list:
                local_min = region_min[region]
                valid_sols = [sol for sol in region.group_sols if sum(sol) == local_min]
                groups = region.groups
                group_probs,_ = prob.calc_probs_from_grouped_sols(groups,valid_sols)

                self.mark_group_probs(groups,group_probs)
                # if len(region.group_sols) != len(valid_sols):
                #     Solver.collected_seeds.append(self.seed)

                # valid_sols = [sol for sol in region.group_sols if sum(sol) == local_min]
                # # valid_sols = [sol for sol in region.sols_bit if sum(sol) == local_min]

                # self.mark_tile_probs(region.locs,valid_sols)
                # print('valid_sols:',valid_sols)

            self.mark_tile_probs(nonfrontier_tiles,[[0] * len(nonfrontier_tiles)])
            for x,y in nonfrontier_tiles:
                # tile = self.tiles[x][y]
                safe_locs.append((x,y))
            for i in range(len(groups)):
                gp = group_probs[i]/len(groups[i])
                if gp == 1:
                    for x,y in groups[i]:
                        mine_locs.append((x,y))
                elif gp == 0:
                    for x,y in groups[i]:
                        safe_locs.append((x,y))
        else:
            prob.update_nonfrontier_tile_probs(self)
        return safe_locs,mine_locs

    def solve_endgame_and_open(self):
        safe_locs,mine_locs = self.solve_endgame()
        solved = self.open_info(safe_locs,mine_locs)

        if not solved:
            if len(self.regions_list) > 0:
                sols_per_mines_in_frontier = Solver.get_sol_counts(self.regions_list,self.nonfrontier_tiles,self.flag_count)
                self.sols_per_mines_in_frontier = sols_per_mines_in_frontier
                self.total_sols = sum(sols_per_mines_in_frontier.values())
                merged_regions = self.regions_list[0]
                for i in range(1,len(self.regions_list)):
                    merged_regions = merged_regions.merge_regions(self.regions_list[i])
                # print(sols_per_mines_in_frontier)
                # print(self.total_sols)
                for group in merged_regions.groups:
                    global_prob = prob.calc_global_prob_for_group(merged_regions,group,sols_per_mines_in_frontier)
                    for x,y in group:
                        self.tiles[x][y].prob_mine_local = global_prob
                #info_found = self.open_known_tiles()

            else:
                #Solver.collected_seeds.append(self.seed)
                #prob.update_nonfrontier_tile_probs(self)
                self.sols_per_mines_in_frontier = {}
                self.total_sols = math.comb(len(self.nonfrontier_tiles),GSM.mine_count - self.flag_count)
        return solved
    def open_info(self,safe_locs,mine_locs):
        for x,y in safe_locs:
            self.reveal_tiles(x,y)
        for x,y in mine_locs:
            self.toggle_flag_at_loc(x,y)
        return len(safe_locs) > 0 or len(mine_locs) > 0

    def open_known_tiles(self):
        opened = False
        for x in range(GSM.rows):
            for y in range(GSM.cols):
                tile = self.tiles[x][y]
                if not tile.is_revealed() and not tile.is_flagged():
                    if tile.prob_mine_local == 1:
                        opened = True
                        self.toggle_flag_at_loc(x,y)
                    elif tile.prob_mine_local == 0:
                        opened = True
                        self.reveal_tiles(x,y)
        return opened

    def mark_known_tiles(self):

        info_found = False
        for x in range(GSM.rows):
            for y in range(GSM.cols):
                tile = self.tiles[x][y]
                if not tile.is_revealed() and not tile.is_flagged():
                    if tile.prob_mine_local == 1:
                        info_found = True
                        self.inject_mine((x,y))
                    elif tile.prob_mine_local == 0:
                        info_found = True
                        self.inject_num((x,y))
        return info_found

    # def open_known_tiles(self,locs,sols):
    #     probs = get_probs(sols)
    #     for i, prob in enumerate(probs):
    #         x, y = locs[i]
    #         if prob == 1:
    #             self.toggle_flag_at_loc(x,y) 
    #         elif prob == 0:
    #             self.reveal_tiles(x,y)
    
    def mark_known_tiles_given_sols(self,locs,sols):
        probs = get_probs(sols)
        info_found = False
        for i, prob in enumerate(probs):
            x, y = locs[i]
            if prob == 1:
                info_found = True
                self.inject_mine((x,y)) 
            elif prob == 0:
                info_found = True
                self.inject_num((x,y))
        return info_found
    
    # def mark_tile_probs(self,locs,sols):
    #     probs = get_probs(sols)
    #     for i in range(len(probs)):
    #         x,y = locs[i]
    #         self.tiles[x][y].prob_mine_local = probs[i]

    def open_marked_tiles(self,locs):
        for loc in locs:
            if self.get_type_at_loc(loc) is MINE:
                self.toggle_flag_at_loc(loc[0],loc[1]) 
            elif self.get_type_at_loc(loc) is NUMBER:
                self.reveal_tiles(loc[0],loc[1])




def intersect_regions(list1, list2):
    result = []
    for r1 in list1:
        if any(r1.is_equal(r2) for r2 in list2):
            result.append(r1)
    return result


def merge_sets(sets):
    merged = []
    while sets:
        base = sets.pop()
        changed = True
        while changed:
            changed = False
            for s in sets[:]:
                if base & s:  # intersection found
                    base |= s
                    sets.remove(s)
                    changed = True
        merged.append(base)
    return sorted(merged,key=len)


def order_tiles_by_connectivity(tile_neighbors):
    visited = set()
    order = []

    # Deterministically pick the start_tile with highest degree and smallest position as tiebreaker
    start_tile = min(
        tile_neighbors,
        key=lambda k: (-len(tile_neighbors[k]), k)
    )

    stack = [start_tile]

    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        order.append(current)

        # Sort neighbors by descending degree and then by position
        neighbors = sorted(
            tile_neighbors[current],
            key=lambda t: (-len(tile_neighbors[t]), t)
        )
        # Reverse to maintain stack behavior (DFS with highest priority first)
        stack.extend(reversed(neighbors))

    return order

def subdivide_locs(locs, split):
    np_locs= np.array(locs)
    parts = np.array_split(np_locs,split)
    list_parts = []
    for part in parts:
        sublist = []
        for coord in part:
            coords = (int(coord[0]),int(coord[1]))
            sublist.append(coords)
        list_parts.append(sublist)

    return list_parts

def shift_and_subdivide_locs(locs, split):
    shift = len(locs)//2
    shifted_locs = locs[shift:] + locs[:shift]
    return subdivide_locs(shifted_locs,split)

def get_probs(sols):
    return [sum(bits) / len(sols) for bits in zip(*sols)]

def get_minecount_freqs(region):
    sols = region.group_sols
    counts = region.group_counts
    mine_counts = [sum(sol) for sol in sols]
    freqs = defaultdict(int)
    for num_mines, count in zip(mine_counts,counts):
        freqs[num_mines] += count
    return freqs

def get_minmax_minecount(sols):
    mine_counts = [sum(sol) for sol in sols]
    min_mines = min(mine_counts)
    max_mines = max(mine_counts)
    return (min_mines,max_mines)

def get_n_closest_coords(coords, target, n):
    # Compute (distance, coord) pairs
    distances = [
        (math.dist(coord, target), coord) for coord in coords
    ]
    
    # Sort by distance
    distances.sort(key=lambda x: x[0])
    
    # Extract the coordinates of the n closest
    closest_coords = [coord for _, coord in distances[:n]]
    
    return closest_coords

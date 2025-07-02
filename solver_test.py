from sprites import *
import  copy
from collections import defaultdict
import numpy as np
from collections import Counter
import math
import itertools
import logging

# Set up logging
logging.basicConfig(
    filename='debug.log',            # File to write to
    filemode='w',                    # 'w' to overwrite, 'a' to append
    level=logging.DEBUG,             # Minimum logging level
    format='%(asctime)s - %(levelname)s - %(message)s'
)

import time
import probability_test as prob
import pickle

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


class Solver(Board):

    def __init__(self,first_click=(0,0),run_pygame=True):
        super().__init__(run_pygame=run_pygame)
        self.first_click = first_click
        self.nonfrontier_tiles = []
        self.regions_list = []
        self.region_freqs = []
        #self.populate(first_click)
        #self.reveal_tiles(first_click[0],first_click[1])

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
                    if self.tiles[row][col].get_type() is OPENING:
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
                if self.tiles[row][col].is_revealed():
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
        regions = set()
        for cc in ccs:
            cc,locs_to_check = self.optimize_backtrack_order(cc)
            #cc = sorted(cc,key=lambda coord: (coord[0], coord[1]))
            regions.add(Region(cc,locs_to_check))
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

    def verify_region(self,region):
        for loc in region.locs_to_check:
            tile = self.tiles[loc[0]][loc[1]]
            tiles_to_check = self.get_neighbor_tiles((tile.row,tile.col))
            tiles_to_check.append(tile)
            for t in tiles_to_check:
                if t.get_type() is NUMBER:
                    tile_types = {UNKNOWN: 0, MINE: 0, NUMBER: 0, OPENING: 0}
                    for t in tiles_to_check:
                        tile_types[t.get_type()] += 1
                    if tile_types[MINE] > tile.get_adj_mines() or (tile_types[UNKNOWN] == 0 and tile_types[MINE] != tile.get_adj_mines()):
                        return False
        return True
    def merge_regions(self, r1, r2):
        # constructor: locs and locs_to_check
        # self.locs = list(locs)
        # self.locs_to_check = locs_to_check
        # self.groups = []
        # self.group_sols = []
        # self.group_counts = []
        # self.sols_bit = []
        # self.num_sols = 0
        combined_locs = r1.locs + r2.locs
        combined_locs_to_check = r1.locs_to_check + r2.locs_to_check
        r = Region(combined_locs,combined_locs_to_check)
        combined_groups = r1.groups + r2.groups
        r.groups = combined_groups
        # combined_group_sols = []
        # for r1sol in r1.group_sols:
        #     for r2sol in r2.group_sols:
        #         combined_sol = list(itertools.product(r1sol,r2sol))
        #         combined_group_sols.append(combined_sol)
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
        # print(r1.group_sols)
        # print(r2.group_sols)
        # print(combined_groups)
        # print(combined_group_sols)
        # print(r1.group_counts)
        # print(r2.group_counts)
        # print(combined_counts)
        return r

    def verify_solution(self,region):
        for loc in region.locs_to_check:
            tile = self.tiles[loc[0]][loc[1]]
            tiles_to_check = self.get_neighbor_tiles((tile.row,tile.col))
            tiles_to_check.append(tile)
            for t in tiles_to_check:
                num_neighbors = 0
                safe_neighbors = 0
                mine_neighbors = 0
                for t in tiles_to_check:
                    if t.get_type() == MINE:
                        mine_neighbors += 1
                    else:
                        safe_neighbors+=1
                    num_neighbors+=1
                if mine_neighbors != t.get_adj_mines() or num_neighbors - mine_neighbors != safe_neighbors:
                    return False
        return True        
    
    def verify_bit_solution(self,sol,region):
        self.inject_bit_solution(sol,region)
        valid = False
        if self.verify_region(region):
            valid = True
        self.undo_sol_inject(region)
        return valid
    
    def verify_group_sol(self,sol,region):
        self.inject_group_sol(sol,region)
        valid = False
        if self.verify_region(region):
            valid = True
        self.undo_sol_inject(region)
        return valid


    def find_solutions_group(self,region,groups):
        if region.num_locs() == 0:
            return
        sols = []

        loc = groups[0]

        # count flagged mines from previous play
        mine_count = 0 # includes flagged mines and unflagged mines deduced from prior calls to find_solution
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                if self.get_type_at_loc((row,col)) is MINE: 
                    mine_count += 1 

        for total_mines in range(len(loc)+1):
            for i in range(len(loc)):
                if i < total_mines:
                    self.inject_mine(loc[i])
                else:
                    self.inject_num(loc[i])
            if self.verify_region(region):
                self.find_solutions_group_helper(region,groups,sols,1,mine_count + total_mines)
            for i in range(len(loc)):
                self.undo_inject(loc[i])


        return sols


    def find_solutions_group_helper(self,region,groups,sols,index,mine_count):
        global paths_explored
        paths_explored += 1
        if mine_count > len(self.mines):
            return
        if index == len(groups): # valid solution found
            #if self.verify_solution(region):
                sol = []
                for loc in groups:
                    num_mines = 0
                    for i in range(len(loc)):
                        x,y = loc[i]
                        curr = self.tiles[x][y]
                        if curr.get_type() is MINE:
                            num_mines +=1
                    sol.append(num_mines)

                sols.append(sol)
        else:
            loc = groups[index]
            for total_mines in range(len(loc)+1):
                for i in range(len(loc)):
                    if i < total_mines:
                        self.inject_mine(loc[i])
                    else:
                        self.inject_num(loc[i])
                if self.verify_region(region):
                    self.find_solutions_group_helper(region,groups,sols,index+1,mine_count + total_mines)
                for i in range(len(loc)):
                    self.undo_inject(loc[i])
            


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
                    if curr.get_type() is MINE:
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
                    

    def mark_tile_probs(self,locs,sols):
        probs = get_probs(sols)
        for i in range(len(probs)):
            x,y = locs[i]
            self.tiles[x][y].prob_mine_local = probs[i]
    
    def mark_tile_probs_by_group(self,groups,group_sols):
        group_probs = prob.calc_probs_from_grouped_sols(groups,group_sols)
        
        for i in range(len(groups)):
            
            group = groups[i]
            length = len(group)
            for j in range(length):
                x,y = group[j]
                self.tiles[x][y].prob_mine_local = group_probs[i]/length

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
            region.groups = groups

        self.start_time = time.time()
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
                                x,y = group[j]
                                self.tiles[x][y].prob_mine_local = group_probs[i]/length
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


    def solve_exhaustive_and_open(self):
        #print(self.flag_count)

        self.solve_exhaustive()

        info_found = self.open_known_tiles()
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
    
    # assume all known mines are flagged
    # assume that solve_board() was called previously and failed
    def solve_endgame(self):
        regions = self.get_regions()
        #assert(len(regions) == len(self.regions_list))
        min_flags = 0
        max_flags = 0

        # border_tiles = []
        # ccs = self.get_ccs()
        

        # for cc in ccs:
        #     for loc in cc:
        #         border_tiles.append(loc)
        frontier_tiles = set()
        regions = self.get_regions()
        #region_locs = [region.locs for region in regions]
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
        if remaining_mines == 0:
            for x,y in nonfrontier_tiles:
                self.reveal_tiles(x,y)
            return True
        
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
            for region in self.regions_list:
                if region not in regions:
                    continue
                local_max = region_max[region]
                valid_sols = [sol for sol in region.sols_bit if sum(sol) == local_max]
                self.mark_tile_probs(region.locs,valid_sols)
            self.mark_tile_probs(nonfrontier_tiles,[[1] * len(nonfrontier_tiles)])
        # all non-border tiles are safe, solution uses min amount of mines
        elif min_flags == remaining_mines:
            for region in self.regions_list:
                if region not in regions:
                    continue
                local_min = region_min[region]
                valid_sols = [sol for sol in region.sols_bit if sum(sol) == local_min]
                self.mark_tile_probs(region.locs,valid_sols)
            self.mark_tile_probs(nonfrontier_tiles,[[0] * len(nonfrontier_tiles)])
        prob.update_nonfrontier_tile_probs(self)
        return False

                            
    def open_remaining(self):
        if self.flag_count == GSM.mine_count:
            for row in range(GSM.rows):
                for col in range(GSM.cols):
                    self.reveal_tiles(row,col)


    def inject_mine(self,loc):
        self.tiles[loc[0]][loc[1]].set_type(MINE)

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
                        neighbor_types[neighbor.get_type()] += 1
                    if neighbor_types[MINE] > curr.get_adj_mines() or (neighbor_types[UNKNOWN] == 0 and neighbor_types[MINE] != curr.get_adj_mines()):
                        return False
                        
        return True

        
    def optimize_backtrack_order(self,locs):

        constraint_map = defaultdict(set)  # clue -> set of (x, y)

        # tile_neighbors: maps each tile to other tiles it shares a constraint with
        tile_neighbors = defaultdict(set)

        for loc in locs:
            neighbors = self.get_neighbor_tiles(loc)
            for neighbor in neighbors:
                if neighbor.is_revealed():
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

    def solve_endgame_and_open(self):
        solved = self.solve_endgame()
        if not solved and len(self.regions_list) > 0:
            info_found = self.open_known_tiles()
            sols_per_mines_in_frontier, subdivs = prob.get_sol_counts(self)
            self.sols_per_mines_in_frontier = sols_per_mines_in_frontier
            self.total_sols = sum(sols_per_mines_in_frontier.values())
            for region in self.regions_list:
                for group in region.groups:
                    global_prob = prob.calc_global_prob_for_group(self,group,sols_per_mines_in_frontier,subdivs)
                    for x,y in group:
                        self.tiles[x][y].prob_mine_local = global_prob
            #info_found = self.open_known_tiles()

            return info_found
        return solved

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


# locs = [(0,0),(1,1),(2,2)]

# r = Region(locs,locs)
# solutions = [
#     [0, 1, 1],
#     [1, 0, 0],
#     [1, 1, 0],
#     [0, 0, 0]
# ]
# r.set_sols_bit(solutions)
# sets=r.get_sols_as_sets()
# print(sets)
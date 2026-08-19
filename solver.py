from sprites import *
from collections import defaultdict, Counter
import math
import dataclasses
from itertools import product
import copy
import fifty_fifty_detection as ffd
from dataclasses import dataclass
import time
from itertools import chain
import probability as prob

# framework for comparisons
# Cumulative timers
_frontier_times = {"np mask": 0.0, "direct set": 0.0}
_frontier_calls = 0

def compare_builds(board,frontier_locs):
    global _frontier_calls

    # 1. numpy mask

            # unknown_mask = (self.tile_state_tracker == UNKNOWN)  # bool array
            # frontier_mask = np.zeros((self.rows, self.cols), dtype=bool)
            # for l in frontier_locs:
            #     frontier_mask[l] = True
            # mask = (~frontier_mask) & unknown_mask
            # nonfrontier_rows, nonfrontier_cols = np.where(mask)
            # nonfrontier_locs1 = set((int(r), int(c)) for r, c in zip(nonfrontier_rows, nonfrontier_cols))        
    start = time.perf_counter()
    unknown_mask = (board.tile_state_tracker == UNKNOWN)  # bool array
    frontier_mask = np.zeros((board.rows, board.cols), dtype=bool)
    for l in frontier_locs:
        frontier_mask[l] = True
    mask = (~frontier_mask) & unknown_mask
    nonfrontier_rows, nonfrontier_cols = np.where(mask)
    nonfrontier_locs1 = set((int(r), int(c)) for r, c in zip(nonfrontier_rows, nonfrontier_cols))        

    _frontier_times["np mask"] += time.perf_counter() - start

    # 2. list.extend + set()
    start = time.perf_counter()
    nonfrontier_locs2 = set(ul for ul in board.unrevealed_tiles if ul not in frontier_locs)

    _frontier_times["direct set"] += time.perf_counter() - start


    # Sanity check
    assert nonfrontier_locs1 == nonfrontier_locs2, "Results differ!"

    _frontier_calls += 1

def print_frontier_summary():
    print("\n=== Frontier Locs Build Timing Summary ===")
    print(f"Total calls: {_frontier_calls}")
    for method, total_time in _frontier_times.items():
        print(f"{method:12} -> {total_time:.6f} seconds total")


# # Set up logging
# logging.basicConfig(
#     filename='debug.log',            # File to write to
#     filemode='w',                    # 'w' to overwrite, 'a' to append
#     level=logging.DEBUG,             # Minimum logging level
#     format='%(asctime)s - %(levelname)s - %(message)s'
# )
class TimeoutException(Exception):
    pass


@dataclass 
class SolverHeuristics():
    total_count: int
    best_prob: float 
    num_safe: int
    has_ff: bool

@dataclass
class GroupInfo():
    tile_locs: list[tuple[int, int]]
    clue_indices: list[int]
    is_ff: bool = False

    def __str__(self):
        return (f"GroupInfo(tile_locs={self.tile_locs}, "
                f"clue_indices={self.clue_indices},"
                f'is_ff={self.is_ff}')

@dataclass
class Possibility():
    mines_per_group: dict
    total_mines: int = 0
    num_cases: int = 1

    def __str__(self):
        return (f"Possibility(total_mines={self.total_mines}, "
                f"num_cases={self.num_cases}, "
                f"mines_per_group={self.mines_per_group})")

class Region():
    def __init__(self, locs,locs_to_check):

        self.locs = list(locs)
        self.locs_to_check = locs_to_check
        self.groups = []
        self.ps = None
        self.group_ids = set()
        self.ic = False

    def __eq__(self, other):
        if not isinstance(other, Region):
            return NotImplemented
        return (frozenset(self.locs) == frozenset(other.locs) and
                frozenset(self.locs_to_check) == frozenset(other.locs_to_check))



class Solver(Board):
    collected_seeds = []
    def __init__(self,first_click=(0,0),empty=False):
        super().__init__(empty=empty)
        if not empty:
            self.first_click = first_click
            self.nonfrontier_tiles = []
            self.regions_list = []
            self.abort_flag = False
            self.deadline=None
            self.collected = False
            self.ic_regions = []
            self.ff_groups = []
            self.ff_influence_locs = []
            self.total_sols = 0


        #self.populate(first_click)
        #self.reveal_tiles(first_click[0],first_click[1])
    @classmethod
    def from_board(cls,board):
        solver = cls()
        solver.rows = board.rows
        solver.cols = board.cols
        solver.dims = board.dims
        solver.num_revealed = board.num_revealed
        solver.flag_count = board.flag_count
        solver.mines = board.mines
        solver.first_click= board.first_click
        solver.seed = board.seed
        solver.death_click = board.death_click
        solver.revealed_tiles = board.revealed_tiles
        solver.unrevealed_tiles = board.unrevealed_tiles

        solver.unfinished_clues = board.unfinished_clues
        solver.flagged_tiles = board.flagged_tiles
        solver.minecount = board.minecount
        solver.cloned = board.cloned
        solver.tile_neighbors = board.tile_neighbors
        solver.num_mine_tracker = board.num_mine_tracker
        solver.tile_state_tracker = board.tile_state_tracker
        solver.adj_flag_tracker = board.adj_flag_tracker
        solver.mine_probs = board.mine_probs
        solver.opening_probs = board.opening_probs
        return solver
    def copy_solver_info(self, board):
        self.nonfrontier_tiles = board.nonfrontier_tiles
        self.regions_list = [copy.copy(region) for region in board.regions_list]
        self.abort_flag = board.abort_flag
        self.deadline = board.deadline
        self.collected=board.collected
        self.ic_regions=board.ic_regions
        self.ff_groups=board.ff_groups
        self.ff_influence_locs=board.ff_influence_locs
        self.total_sols=board.total_sols



    def is_loc_candidate_for_analysis(self,loc):
        if loc not in self.nonfrontier_tiles:
            return True
        neighbor_coords = self.lookup_neighbors(loc)
        count_nonfrontier = 0
        count_frontier = 0
        for neighbor in neighbor_coords:
            if neighbor in self.nonfrontier_tiles:
                count_nonfrontier += 1
            elif self.tile_state_tracker[neighbor] == UNKNOWN:
                count_frontier += 1
            if count_nonfrontier - count_frontier >= 4:
                return False
        return count_nonfrontier- count_frontier < 4
    
    # for unrevealed tiles on the frontier
    def group_equivalent_tiles(self,region):
        locs = region.locs
        groups_dict = defaultdict(list)

        for loc in locs:
            # Get set of neighboring number tiles
            number_neighbors = frozenset(
                neighbor for neighbor in self.lookup_neighbors(loc) if self.tile_state_tracker[neighbor] == REVEALED
            )
            groups_dict[number_neighbors].append(loc)
        # Sort each group for determinism
        sorted_groups = [
            sorted(group, key=lambda t: (t[0], t[1]))
            for group in groups_dict.values()
        ]

        # Sort groups by first element for deterministic output
        sorted_groups.sort(key=lambda group: (group[0][0], group[0][1]))
        
        return sorted_groups

    def find_flags(self,loc):
        target_mines = self.num_mine_tracker[loc]
        curr_flags = self.adj_flag_tracker[loc]
        mines_to_find = target_mines - curr_flags
        unknown_neighbors = []
        neighbors = self.lookup_neighbors(loc)
        for neighbor in neighbors:
            if self.tile_state_tracker[neighbor] == UNKNOWN:
                unknown_neighbors.append(neighbor)
        flags_found = len(unknown_neighbors) == mines_to_find
        return flags_found,unknown_neighbors


    # flags neighbors if they are known to be mines
    def flag_neighbors(self,loc):

        flags_found,unknown_neighbors = self.find_flags(loc)
        if flags_found:
            for neighbor in unknown_neighbors:
                self.toggle_flag_at_loc(neighbor)
        return unknown_neighbors
    
    
    def flag_board(self):
        flags_found = False
        for loc in list(self.unfinished_clues):
            if self.flag_neighbors(loc):
                flags_found = True
        return flags_found
    
    
    def chord_board(self):
        for loc in list(self.unfinished_clues):
            self.chord(loc)


    # def find_trivial_moves(self):
    def solve_trivial_and_open(self):
        init_mines = self.flag_count
        init_revealed = self.num_revealed

        flags_found = self.flag_board()
        if flags_found:
            self.chord_board()
        new_mines = self.flag_count
        new_revealed = self.num_revealed
        return new_revealed != init_revealed or init_mines != new_mines
    


    def get_ccs(self):
        adj_sets = []
        for loc in self.unfinished_clues:
            neighbors = self.lookup_neighbors(loc)
            adj_set = set()

            for neighbor in neighbors:
                if self.tile_state_tracker[neighbor] == UNKNOWN:
                    adj_set.add(neighbor)
            if len(adj_set) > 0: 
                adj_sets.append(adj_set)
        merged = merge_sets(adj_sets)
        return merged
    
    def convert_ccs_to_regions(self,ccs):
        regions = []
        for cc in ccs:
            cc,locs_to_check = self.optimize_backtrack_order(cc)
            cc = sorted(cc,key=lambda coord: (coord[0], coord[1]))
            locs_to_check = sorted(locs_to_check,key=lambda coord: (coord[0], coord[1]))
            regions.append(Region(cc,locs_to_check))
        return regions
    
    def get_regions(self):
        ccs = self.get_ccs()
        regions = self.convert_ccs_to_regions(ccs)
        return regions

    def assign_tile_value(self,loc,val):

        orig_val_at_loc = self.num_mine_tracker[loc]
        self.num_mine_tracker[loc] = val
        self.tile_state_tracker[loc] = REVEALED

        self.unfinished_clues.add(loc)
        self.unrevealed_tiles.remove(loc)
        self.revealed_tiles.add(loc)
        return orig_val_at_loc
    
    def unassign_tile_value(self,loc,orig_val_at_loc):


        self.num_mine_tracker[loc] = orig_val_at_loc
        self.tile_state_tracker[loc] = UNKNOWN
        self.unfinished_clues.discard(loc)
        self.unrevealed_tiles.add(loc)
        self.revealed_tiles.remove(loc)
    @profile
    def get_sol_counts_at_loc_for_val(self,loc,val):
        saved_total_sols = self.total_sols
        orig_val_at_loc = self.assign_tile_value(loc,val)
        regions = self.get_updated_regions_list()
        regions_to_solve = []
        for region in regions:
            if region.ps == None:
                regions_to_solve.append(region)
            else:
                regions_to_solve.append(copy.copy(region))
        total_count = 0
        best_prob = 1
        num_safe = 0
        has_ff = False
        solvable = True

        groups_list= self.find_possibilities(regions_to_solve)
        for region in regions_to_solve:
            if len(region.ps) == 0:
                solvable = False
                break
        if solvable:
            frontier_locs = []
            for region in regions_to_solve:
                frontier_locs.extend(region.locs)
            frontier_locs = set(frontier_locs)
            nonfrontier_locs = set(ul for ul in self.unrevealed_tiles if ul not in frontier_locs)
            safe_locs, _,best_prob,total_count = self.calc_probs_for_board(regions_to_solve,groups_list,nonfrontier_locs,update_self=False)
            num_safe = len(safe_locs)
        self.unassign_tile_value(loc,orig_val_at_loc)
        self.total_sols = saved_total_sols
        return SolverHeuristics(total_count=total_count,best_prob=best_prob, num_safe=num_safe,has_ff=has_ff)


    def check_timeout(self):
        if self.deadline is not None and time.time() > self.deadline:
            self.abort_flag = True
            raise TimeoutException("Recursive solver exceeded timeout")

    
    def get_updated_regions_list(self):

        ccs = self.get_ccs()
        regions = self.convert_ccs_to_regions(ccs)
        existing_region_map = {
            (frozenset(r.locs), frozenset(r.locs_to_check)): r
            for r in self.regions_list
        }

        new_regions_list = []
        for region in regions:
            key = (frozenset(region.locs), frozenset(region.locs_to_check))
            if key in existing_region_map:
                existing_region = existing_region_map[key]
                new_regions_list.append(existing_region)
            else:
                groups = self.group_equivalent_tiles(region)
                #groups = self.order_groups_by_information(groups)
                region.groups = groups
                new_regions_list.append(region)
        new_regions_list = sorted(new_regions_list, key=lambda r: len(r.groups))
        return new_regions_list


    def find_groupings(self,regions):
        unfinished_clues_list = list(self.unfinished_clues)
        all_groups = []

        for region in regions:
            for group in region.groups:
                all_groups.append(group)
        
        clue_index_dict = {}
        for i in range(len(unfinished_clues_list)):
            clue = unfinished_clues_list[i]
            clue_index_dict[clue] = i
        groups_list = []
        for i in range(len(all_groups)):
            group = all_groups[i]
            rep_loc = group[0]
            neighbors = self.lookup_neighbors(rep_loc)
            clue_neighbors = [n for n in neighbors if n in unfinished_clues_list]

            clue_indices_for_group = [clue_index_dict[n] for n in clue_neighbors]
            groups_list.append(GroupInfo(tile_locs=group,clue_indices=clue_indices_for_group))

        return groups_list, unfinished_clues_list,clue_index_dict

    def reformat_possibilities_in_existing_region(self, region, tile_to_group_index):
        ps = region.ps
        rep_loc = region.groups[0][0]
        old_start_index = region.first_group_index

        new_start_index = tile_to_group_index.get(rep_loc, -1)
        if new_start_index == -1:
            raise ValueError("Couldn't find rep_loc in updated groups_list")

        new_ps = []
        total_groups = len(tile_to_group_index)

        for p in ps: 
            updated_mines_per_group = [0] * total_groups
            for i in range(region.num_groups):
                updated_mines_per_group[new_start_index + i] = p.mines_per_group[old_start_index + i]
            new_p = dataclasses.replace(p, mines_per_group=updated_mines_per_group)
            new_ps.append(new_p)

        region.group_ids = set(range(new_start_index, new_start_index + region.num_groups))

        return new_start_index, new_ps
    def find_possibilities(self,regions_to_solve):
        groups_list = {}
        if len(regions_to_solve) > 0:

            #groups_list: dict(group id: GroupInfo(tile_locs,clue_indices))
            #unfinished_clues_list: list of locs of clues to be used
            #clue_index_dict: dict(loc of clue: index of clue in unfinished_clues_list)
            groups_list, unfinished_clues_list, clue_index_dict = self.find_groupings(regions_to_solve)
            tile_to_group_index = {}
            for i, group_info in enumerate(groups_list):
                tile_to_group_index[group_info.tile_locs[0]] = i
            for region in regions_to_solve:

                if region.ps == None:
                    first_group_index = -1
                    num_groups = 0
                    for group_index,group_info in enumerate(groups_list):
                        rep_loc = group_info.tile_locs[0]
                        if rep_loc in region.locs:
                            if first_group_index == -1:
                                first_group_index = group_index
                            num_groups += 1
                    region.first_group_index = first_group_index
                    region.num_groups = num_groups
                    ps = self.find_possibilities_for_region(region,groups_list, unfinished_clues_list, clue_index_dict)
                    region.ps = ps
                else:
                    new_start_index, new_ps = self.reformat_possibilities_in_existing_region(region,tile_to_group_index)
                    region.first_group_index = new_start_index
                    region.ps = new_ps
        return groups_list
    

    def find_possibilities_for_region(self,region,groups_list, unfinished_clues_list, clue_index_dict):
        #groups_list: dict(group id: GroupInfo(tile_locs,clue_indices))
        #unfinished_clues_list: list of locs of clues to be used
        #clue_index_dict: dict(loc of clue: index of clue in unfinished_clues_list)


        #groups_by_clue: dict(index of clue in unfinished_clues_list: adjacent group ids)
        groups_by_clue = get_groupings_by_clue(groups_list, unfinished_clues_list, clue_index_dict)

        #update region group ids:
        group_ids_in_region = []
        for group_index, group_info in enumerate(groups_list):
            rep_loc = group_info.tile_locs[0]
            if rep_loc in region.locs:
                group_ids_in_region.append(group_index)
        region.group_ids = group_ids_in_region

        region_tiles = set(region.locs)
        relevant_clues = set()

        for loc in region_tiles:
            neighbors = self.lookup_neighbors(loc)
            for neighbor in neighbors:
                if neighbor in self.unfinished_clues:
                    relevant_clues.add(clue_index_dict[neighbor])
        relevant_clues = list(relevant_clues)

        used_clues = [False] * len(unfinished_clues_list)
        used_groups = [False] * len(groups_list)
        num_used_clues = 0
        
        # possibility fields:
        # total_mines (default:0)
        # num_cases (default:1)
        # mines_per_group: list where the ith element represents how many mines are in the group at 
        #                  groups_list[i]
        ps = [Possibility(mines_per_group=[0] * len(groups_list))]

        # mines_added_per_clue: list where the ith element represents how many mines need to be added to
        # satisfy the clue at unfinished_clues_list[i]
        mines_added_per_clue = [0] * len(clue_index_dict)
        for clue_loc, clue_index in clue_index_dict.items():
            if clue_index in relevant_clues:
                mines_added_per_clue[clue_index] = int(self.num_mine_tracker[clue_loc]-self.adj_flag_tracker[clue_loc])
        while (num_used_clues < len(relevant_clues)):
            best_clue = -1
            best_clue_boundary = len(groups_list) + 1
            for clue_index in relevant_clues:
                if used_clues[clue_index]:
                    continue
                used_clues[clue_index] = True
                boundary = get_boundary(groups_list,used_clues)
                supergroups = get_boundary_supergroups(groups_list,used_clues,boundary)
                used_clues[clue_index] = False
                boundary_change = len(supergroups)
                if boundary_change < best_clue_boundary:
                    best_clue = clue_index
                    best_clue_boundary = boundary_change
        
            used_clues[best_clue] = True
            num_used_clues += 1
            boundary = get_boundary(groups_list,used_clues)
            supergroups = get_boundary_supergroups(groups_list,used_clues,boundary)

            groups_to_use = []
            for group_id in groups_by_clue[best_clue]:
                if not used_groups[group_id]:
                    used_groups[group_id] = True
                    groups_to_use.append(group_id)
            new_ps = []

            for p in ps:
                mines_to_add = mines_added_per_clue[best_clue]


                mines_in_used_groups = 0
                for group_id in groups_by_clue[best_clue]:

                    mines_in_used_groups += p.mines_per_group[group_id]
                mines_to_add -= mines_in_used_groups

                extend_possibility(p,mines_to_add,groups_to_use,new_ps,len(groups_to_use)-1,groups_list,board=self)
            ps = new_ps
        return ps
    

    def merge_all_possibilities(self,regions):
        p_lists = [region.ps for region in regions]

        all_combinations = product(*p_lists)
        merged_possibilities = [
            merge_possibilities(list(combo),board=self) for combo in all_combinations
        ]
        return merged_possibilities
    
    @profile
    def calc_prob_at_board_test(self, regions, groups_list, nonfrontier_locs):
        a = {}
        num_nf = len(nonfrontier_locs)
        mines_left = self.minecount - self.flag_count
        nf_loc = next(iter(nonfrontier_locs), None)
        all_global_sols = {}
        if len(regions) > 0:
            for region in regions:
                region.freq_dict = defaultdict(int)
                for p in region.ps:
                    region.freq_dict[p.total_mines] += p.num_cases

            all_global_sols = convolve_freqs([region.freq_dict for region in regions])
        else:
            all_global_sols = {0: 1}
        all_global_sols = {k:v for k,v in all_global_sols.items() if k <= mines_left}
        for mc in all_global_sols:
            all_global_sols[mc] *= math.comb(num_nf, mines_left - mc)
        sum_global_sols = sum(all_global_sols.values())
        if sum_global_sols == 0:
            return {}, 0

        if len(regions) > 0:
            for region in regions:
                freqs_to_convolve = [other.freq_dict for other in regions if other != region]
                if not freqs_to_convolve:
                    cfreqs = {0:1}
                else:
                    cfreqs = convolve_freqs(freqs_to_convolve)
                # group: minecount of region: expected mines
                mpg = defaultdict(lambda:defaultdict(int))
                for p in region.ps:
                    t = p.total_mines
                    for g in region.group_ids:
                        mpg[g][t] += p.num_cases * p.mines_per_group[g]
                for g in mpg:
                    num_sols = 0
                    for mines_here in mpg[g]:
                        if mines_here == 0:
                            continue
                        num_sols_at_mc = 0
                        for mines_other in cfreqs:
                            mines_to_place = mines_left - mines_other - mines_here
                            if mines_to_place >= 0:
                                num_sols_at_mc += cfreqs[mines_other] * math.comb(num_nf, mines_to_place)
                        num_sols_at_mc *= mpg[g][mines_here]
                        num_sols += num_sols_at_mc
                    a[groups_list[g].tile_locs[0]] = num_sols / sum_global_sols / len(groups_list[g].tile_locs)

        if num_nf > 0:
            prob_dist = {mc: num_sols_for_mc / sum_global_sols for mc, num_sols_for_mc in all_global_sols.items()}
            a[nf_loc] = prob.calc_prob_for_nonfrontier_tiles(prob_dist, mines_left, num_nf)
        return a, sum_global_sols



    
    # @return: safe_locs,mine_locs,safest_prob,total_sols
    @profile
    def calc_probs_for_board(self, regions, groups_list, nonfrontier_locs, update_self=True):
        a, total_sols = self.calc_prob_at_board_test(regions, groups_list, nonfrontier_locs)

        # invalid board: no valid global solutions
        if total_sols == 0:
            return [], [], 1, 0

        safe_locs = []
        mine_locs = []
        safest_prob = 1.0

        for group_info in groups_list:
            rep_loc = group_info.tile_locs[0]
            prob_at_loc = a[rep_loc]
            for loc in group_info.tile_locs:
                if update_self:
                    self.mine_probs[loc] = prob_at_loc
                if math.isclose(prob_at_loc, 0.0, abs_tol=1e-12):
                    safe_locs.append(loc)
                elif math.isclose(prob_at_loc, 1.0, abs_tol=1e-12):
                    mine_locs.append(loc)
            safest_prob = min(safest_prob, prob_at_loc)

        if len(nonfrontier_locs) > 0:
            nf_keys = [loc for loc in a if loc in nonfrontier_locs]
            nf_rep = nf_keys[0] if nf_keys else min(nonfrontier_locs)
            prob_at_loc = a[nf_rep]
            for loc in nonfrontier_locs:
                if update_self:
                    self.mine_probs[loc] = prob_at_loc
                if math.isclose(prob_at_loc, 0.0, abs_tol=1e-12):
                    safe_locs.append(loc)
                elif math.isclose(prob_at_loc, 1.0, abs_tol=1e-12):
                    mine_locs.append(loc)
            safest_prob = min(safest_prob, prob_at_loc)

        if update_self:
            self.total_sols = total_sols

        return safe_locs, mine_locs, safest_prob, total_sols

    @profile
    def solve_exhaustive(self,force=False):
        self.mine_probs[:] = -1
        self.regions_list = self.get_updated_regions_list()
        groups_list= self.find_possibilities(self.regions_list)
        ff_groups = []
        ic_regions = []
        ff_influence_locs = []
        for region in self.regions_list:
            ff_groups_in_region,ff_influence_locs_in_region = ffd.is_two_tile_ff_in_region(self,region)
            for ff_group in ff_groups_in_region:
                ff_groups.append(ff_group)
            for loc in ff_influence_locs_in_region:
                ff_influence_locs.append(loc)
            if ffd.is_region_info_complete(self,region):
                ic_regions.append(region)
        self.ic_regions = ic_regions
        self.ff_groups = ff_groups
        self.ff_influence_locs = ff_influence_locs
        self.groups_list = groups_list
        mines_left = self.minecount-self.flag_count
        frontier_locs = []
        for region in self.regions_list:
            frontier_locs.extend(region.locs)
        frontier_locs = set(frontier_locs)  
        nonfrontier_locs = set(ul for ul in self.unrevealed_tiles if ul not in frontier_locs)
        self.nonfrontier_tiles = nonfrontier_locs
        self.nf_rep_loc = min(nonfrontier_locs) if len(nonfrontier_locs) > 0 else None
        if len(groups_list) == 0 and mines_left==0:
            safe_locs = []
            for loc in nonfrontier_locs:
                
                self.mine_probs[loc] = 0
                safe_locs.append(loc)
            return safe_locs,[]
        safe_locs, mine_locs = self.search_possibilities(self.regions_list,groups_list)
        if len(safe_locs) > 0 and not force:
            for loc in safe_locs:
                self.mine_probs[loc]= 0
            for loc in mine_locs:
                self.mine_probs[loc]= 1

        else:
            safe_locs, mine_locs,_,total_sols = self.calc_probs_for_board(self.regions_list,groups_list,nonfrontier_locs)
            self.total_sols = total_sols
        return safe_locs,mine_locs
            


    def solve_exhaustive_and_open(self):

        safe_locs, mine_locs=self.solve_exhaustive()
        info_found = self.open_info(safe_locs,mine_locs)
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

    def search_possibilities(self,regions,groups_list):
        safe_locs = []
        mine_locs = []
        for region in regions:
            sols = []
            ps=region.ps
            if ps == None:
                continue
            for p in ps:
                sols.append(p.mines_per_group)
            group_indices = []
            for group_index, group_info in enumerate(groups_list):
                if group_info.tile_locs[0] in region.locs:
                    group_indices.append(group_index)
            group_counts = list(map(list, zip(*sols)))


            for group_index in group_indices:

                group_count = group_counts[group_index]
                avg_mines_in_group = sum(group_count)/len(group_count)
                group_info = groups_list[group_index]
                if avg_mines_in_group == 0:
                    for loc in group_info.tile_locs:
                        safe_locs.append(loc)
                elif avg_mines_in_group == len(group_info.tile_locs):
                    for loc in group_info.tile_locs:
                        mine_locs.append(loc)
        return safe_locs,mine_locs                            


        
    def optimize_backtrack_order(self,locs):

        constraint_map = defaultdict(set)  # clue -> set of (x, y)

        # tile_neighbors: maps each tile to other tiles it shares a constraint with
        tile_neighbors = defaultdict(set)

        for loc in locs:
            neighbors = self.lookup_neighbors(loc)
            for neighbor in neighbors:
                if self.tile_state_tracker[neighbor] == REVEALED and self.num_mine_tracker[neighbor] != 9:
                    constraint_map[neighbor].add(loc)

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

    def open_info(self,safe_locs,mine_locs):
        for loc in safe_locs:
            self.reveal_tiles(loc)
        for loc in mine_locs:
            self.toggle_flag_at_loc(loc)
        return len(safe_locs) > 0 or len(mine_locs) > 0

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


# freqs is a list of dicts
def convolve_freqs(freqs):
    if len(freqs) == 0:
        return {}
    total_freqs = Counter()
    for tm,tc in freqs[0].items():
        convolve_freqs_helper(freqs,1,tm,tc,total_freqs)
    return total_freqs

def convolve_freqs_helper(freqs, index, total_mines, total_count, total_freqs):
    if index == len(freqs):
        total_freqs[total_mines] += total_count
    else:
        for tm,tc in freqs[index].items():
            new_tm = total_mines + tm
            new_tc = total_count * tc
            convolve_freqs_helper(freqs,index+1,new_tm,new_tc,total_freqs)
# return a new freqs dict that has freqs_to_remove deconvolved from all_freqs
def deconvolve_freqs(all_freqs, freqs_to_remove):
    new_freqs = Counter()
    for tm,tc in all_freqs.items():
        for tm_r, tc_r in freqs_to_remove.items():
            new_freqs[tm-tm_r] += tc/tc_r
    return new_freqs


def get_groupings_by_clue(groups_list, unfinished_clues_list, clue_index_dict):
    # Initialize an empty list of groups for each clue index
    groupings_by_clue = {
        clue_index_dict[clue_loc]: [] for clue_loc in unfinished_clues_list
    }

    # Fill in the groupings by clue
    for group_id, group_info in enumerate(groups_list):
        for clue_index in group_info.clue_indices:
            groupings_by_clue[clue_index].append(group_id)

    return groupings_by_clue

# boundary: ids of groups which are adjacent to both used and unused clues
def get_boundary(groups, used_clues):
    boundary = []
    for group_id,info in enumerate(groups):
        adj_to_used_clue = False
        adj_to_unused_clue = False
        for clue_index in info.clue_indices:
            if used_clues[clue_index]:
                adj_to_used_clue = True
            else:
                adj_to_unused_clue = True
        if adj_to_used_clue and adj_to_unused_clue:
            boundary.append(group_id)
    return boundary


# boundary_supergroup: a set of groups which are adjacent to the same unused clues
def get_boundary_supergroups(groups,used_clues,boundary):
    clue_sets = defaultdict(list) # sets of clues: list of group ids
    for group_id in boundary:
        info = groups[group_id]
        clue_indices = info.clue_indices
        unused_clue_indices = set()
        for clue_index in clue_indices:
            if not used_clues[clue_index]:
                unused_clue_indices.add(clue_index)
        unused_clue_indices = frozenset(unused_clue_indices)
        clue_sets[unused_clue_indices].append(group_id)
    supergroups = clue_sets.values()
    return supergroups

# sum arrays of the same length elements-wise
def sum_arrays(arr1,arr2):
    return [arr1[i] + arr2[i] for i in range(len(arr1))]


# possibility fields:
# total_mines (default:0)
# num_cases (default:1)
# mines_per_group: list where the ith element represents how many mines are in the group at 
#                  groups_list[i]
def merge_possibilities(ps_to_merge,board=None):

    merged_total_mines = 0
    merged_num_cases = 1
    merged_mines_per_group = [0] * len(ps_to_merge[0].mines_per_group)
    for p in ps_to_merge:
        if board is not None:
            board.check_timeout()
        merged_total_mines += p.total_mines
        merged_num_cases *= p.num_cases
        merged_mines_per_group = sum_arrays(merged_mines_per_group,p.mines_per_group)
    return Possibility(mines_per_group=merged_mines_per_group,total_mines=merged_total_mines,num_cases=merged_num_cases)


def extend_possibility(p, mines_to_add, groups_to_use, new_ps, n, groups_list,board=None):
    if board is not None:
        board.check_timeout()
    if n < 0:
        if mines_to_add == 0:
            new_ps.append(p)
    else:
        group_to_use = groups_to_use[n]
        group_len = len(groups_list[group_to_use].tile_locs)
        if n == 0:
            if mines_to_add >= 0 and mines_to_add <= group_len:
                new_total_mines = p.total_mines + mines_to_add
                num_combs = math.comb(group_len,mines_to_add)

                new_num_cases = p.num_cases * num_combs
                new_mines_per_group = p.mines_per_group[:]
                new_mines_per_group[group_to_use] = mines_to_add
                new_p = Possibility(mines_per_group=new_mines_per_group,total_mines=new_total_mines,
                                    num_cases=new_num_cases)
                new_ps.append(new_p)

        else:
            max_mines = group_len
            for used_mines in range(max_mines+1):
                new_total_mines = p.total_mines + used_mines

                num_combs = math.comb(max_mines,used_mines)
                new_num_cases = p.num_cases * num_combs

                new_mines_per_group = p.mines_per_group[:]
                new_mines_per_group[group_to_use] = used_mines
                new_p = Possibility(mines_per_group=new_mines_per_group,total_mines=new_total_mines,
                                    num_cases=new_num_cases)
                extend_possibility(new_p,mines_to_add-used_mines,groups_to_use,new_ps,n-1,groups_list,board=board)
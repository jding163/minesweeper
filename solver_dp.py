from solver import Solver
import dataclasses
from dataclasses import dataclass
from collections import defaultdict
from math import comb
import probability as prob
from itertools import product
import copy
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

class SolverDP(Solver):

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
            x,y = group[0]
            neighbors = self.tiles[x][y].neighbors
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

        return new_start_index, new_ps



    def find_possibilities(self,regions_to_solve):
        if len(regions_to_solve) == 0:
            return {}

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

        for x, y in region_tiles:
            for neighbor in self.tiles[x][y].neighbors:
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
                clue = self.tiles[clue_loc[0]][clue_loc[1]]
                mines_added_per_clue[clue_index] = clue.num_adj_mines-clue.num_adj_flags
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
            merge_possibilities(list(combo),board=self)
            for combo in all_combinations
        ]
        return merged_possibilities

    def calc_prob_at_loc(self,loc,groups_list,nonfrontier_locs,total_sols,total_sols_dict,num_local_sols_at_count,ps_with_num_mines):
        x,y=loc
        tile = self.tiles[x][y]
        if not tile.is_unknown():
            return 0
        

        #total_sols = sum(total_sols_dict.values())
        if (x,y) in nonfrontier_locs:
            prob_dist = {mc: num_sols_for_mc / total_sols for mc, num_sols_for_mc in total_sols_dict.items()}
            mines_left = len(self.mines) - self.flag_count

            prob_nf = prob.calc_prob_for_nonfrontier_tiles(prob_dist,mines_left,len(nonfrontier_locs))
            

            return prob_nf
        
        group_id = -1
        group_size = -1
        for id,info in enumerate(groups_list):
            if loc in info.tile_locs:
                group_size = len(info.tile_locs)
                group_id = id
                break


        avg_mines_in_group = 0
        for num_mines, num_cases in num_local_sols_at_count.items():
            num_sols_at_num_mines = total_sols_dict[num_mines]
            matching_ps = ps_with_num_mines[num_mines]
            avg_mines_in_group_at_num_mines = 0
            for p in matching_ps:
                frac = p.num_cases/num_cases

                avg_mines_in_group_at_num_mines += frac * p.mines_per_group[group_id]
            avg_mines_in_group += (num_sols_at_num_mines/total_sols) * avg_mines_in_group_at_num_mines
        prob_loc_is_mine = avg_mines_in_group/group_size
        return prob_loc_is_mine

    def calc_probs_for_board(self,regions,groups_list,nonfrontier_locs):
        safe_locs = []
        mine_locs = []
        total_sols_dict = defaultdict(int)
        num_local_sols_at_count = defaultdict(int)
        ps_with_num_mines = defaultdict(list)
        mines_left = self.minecount-self.flag_count

        safest_prob = 1
        if len(regions)>0:
            
            ps = self.merge_all_possibilities(regions)

            for p in ps:
                if p.total_mines <= mines_left:
                    num_local_sols_at_count[p.total_mines] += p.num_cases

                    ps_with_num_mines[p.total_mines].append(p)
            total_sols = 0

            for num_mines in ps_with_num_mines.keys():
                total_sols_at_num_mines = num_local_sols_at_count[num_mines] * comb(len(nonfrontier_locs),mines_left-num_mines)
                total_sols_dict[num_mines] = total_sols_at_num_mines
                total_sols += total_sols_at_num_mines
            if total_sols == 0:
                return [],[],1,0
            for group_info in groups_list:
                group_locs = group_info.tile_locs
                rep_loc = group_locs[0]
                prob_at_loc = self.calc_prob_at_loc(rep_loc,groups_list,nonfrontier_locs,total_sols,total_sols_dict,num_local_sols_at_count,ps_with_num_mines)
                for loc in group_locs:
                    tile = self.tiles[loc[0]][loc[1]]
                    tile.prob_mine_local = prob_at_loc
                    if prob_at_loc == 0:
                        safe_locs.append(loc)
                    elif prob_at_loc == 1:
                        mine_locs.append(loc)
                safest_prob = min(safest_prob,prob_at_loc)
        else:
            total_sols = comb(len(nonfrontier_locs),mines_left)

        if len(nonfrontier_locs) > 0:
            
            nf_loc = None
            for nf_l in nonfrontier_locs:
                nf_loc = nf_l
                break
            prob_at_loc = self.calc_prob_at_loc(nf_loc,groups_list,nonfrontier_locs,total_sols,total_sols_dict,num_local_sols_at_count,ps_with_num_mines)
            for loc in nonfrontier_locs:
                tile = self.tiles[loc[0]][loc[1]]
                tile.prob_mine_local = prob_at_loc


                if prob_at_loc == 0:
                    safe_locs.append(loc)
                elif prob_at_loc == 1:
                    mine_locs.append(loc)
            safest_prob = min(safest_prob,prob_at_loc)

        return safe_locs,mine_locs,safest_prob,total_sols
    
    def solve_exhaustive(self):
        self.regions_list = self.get_updated_regions_list()
        groups_list = self.find_possibilities(self.regions_list)
        self.groups_list = groups_list
        mines_left = self.minecount-self.flag_count
        nonfrontier_locs = set()
        frontier_locs = set()
        for region in self.regions_list:
            for l in region.locs:
                frontier_locs.add(l)
        nonfrontier_locs = set()
        for r in range(self.rows):
            for c in range(self.cols):
                if (r,c) not in frontier_locs and self.tiles[r][c].is_unknown():
                    nonfrontier_locs.add((r,c))
        self.nonfrontier_tiles = sorted(nonfrontier_locs)
        if len(groups_list) == 0 and mines_left==0:

            safe_locs = []
            for x,y in nonfrontier_locs:
                
                tile = self.tiles[x][y]
                tile.prob_mine_local = 0
                safe_locs.append((x,y))
            return safe_locs,[]
        safe_locs, mine_locs = self.search_possibilities(self.regions_list,groups_list)
        if len(safe_locs) > 0:
            for x,y in safe_locs:
                tile = self.tiles[x][y]
                tile.prob_mine_local = 0
            for x,y in mine_locs:
                tile = self.tiles[x][y]
                tile.prob_mine_local = 1
        else:
            safe_locs, mine_locs,_,total_sols= self.calc_probs_for_board(self.regions_list,groups_list,nonfrontier_locs) 
            self.total_sols = total_sols
        return safe_locs,mine_locs

    # return total_count,best_prob, num_safe
    def get_sol_counts_at_loc_for_val(self,loc,val):
        x,y = loc
        tile = self.tiles[x][y]
        orig_val_at_loc = self.assign_tile_value(tile,val)
        regions = self.get_updated_regions_list()
        regions_to_solve = []
        for region in regions:
            if region.ps == None:
                regions_to_solve.append(region)
            else:
                regions_to_solve.append(copy.deepcopy(region))
        total_count = 0
        best_prob = 1
        num_safe = 0
        solvable = True
        groups_list = self.find_possibilities(regions_to_solve)
        for region in regions_to_solve:
            if len(region.ps) == 0:
                solvable = False
                break
        if solvable:
            nonfrontier_locs = set()
            frontier_locs = set()
            for region in regions_to_solve:
                for l in region.locs:
                    frontier_locs.add(l)
            nonfrontier_locs = set()
            for r in range(self.rows):
                for c in range(self.cols):
                    if (r,c) not in frontier_locs and self.tiles[r][c].is_unknown():
                        nonfrontier_locs.add((r,c))

            safe_locs, _,best_prob,total_count= self.calc_probs_for_board(regions_to_solve,groups_list,nonfrontier_locs) 
            num_safe = len(safe_locs)
        self.unassign_tile_value(tile,orig_val_at_loc)
        return total_count,best_prob, num_safe
    
    def search_possibilities(self,regions,groups_list):
        safe_locs = []
        mine_locs = []
        for region in regions:
            sols = []
            ps=region.ps
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
    
    # def get_sol_counts_at_loc_for_val(self,loc,val):
    #     x,y = loc
    #     tile = self.tiles[x][y]
    #     orig_val_at_loc = self.assign_tile_value(tile,val)

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
                num_combs = comb(group_len,mines_to_add)

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

                num_combs = comb(max_mines,used_mines)
                new_num_cases = p.num_cases * num_combs

                new_mines_per_group = p.mines_per_group[:]
                new_mines_per_group[group_to_use] = used_mines
                new_p = Possibility(mines_per_group=new_mines_per_group,total_mines=new_total_mines,
                                    num_cases=new_num_cases)
                extend_possibility(new_p,mines_to_add-used_mines,groups_to_use,new_ps,n-1,groups_list,board=board)


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
        

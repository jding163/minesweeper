from solver import Solver
from dataclasses import dataclass
from collections import defaultdict
from math import comb
import probability as prob
@dataclass
class GroupInfo():
    tile_locs: list[tuple[int, int]]
    clue_indices: list[int]

    def __str__(self):
        return (f"GroupInfo(tile_locs={self.tile_locs}, "
                f"clue_indices={self.clue_indices},")

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
    def find_groupings(self):
        unfinished_clues_list = list(self.unfinished_clues)
        ccs = self.get_ccs()
        all_groups = []
        regions = self.convert_ccs_to_regions(ccs)
        for region in regions:
            groups = self.group_equivalent_tiles(region)
            #groups = self.order_groups_by_information(groups)
            region.groups = groups
            for group in groups:
                all_groups.append(group)
        
        clue_index_dict = {}
        for i in range(len(unfinished_clues_list)):
            clue = unfinished_clues_list[i]
            clue_index_dict[clue] = i

        groups_dict = {}
        for i in range(len(all_groups)):
            group = all_groups[i]
            x,y = group[0]
            neighbors = self.tiles[x][y].neighbors
            clue_neighbors = [n for n in neighbors if n in unfinished_clues_list]

            clue_indices_for_group = [clue_index_dict[n] for n in clue_neighbors]
                
            groups_dict[i] = GroupInfo(tile_locs=group,clue_indices=clue_indices_for_group)
        return groups_dict, unfinished_clues_list,clue_index_dict


    def find_possibilities(self):
        #groups_dict: dict(group id: GroupInfo(tile_locs,clue_indices))
        #unfinished_clues_list: list of locs of clues to be used
        #clue_index_dict: dict(loc of clue: index of clue in unfinished_clues_list)
        groups_dict, unfinished_clues_list, clue_index_dict = self.find_groupings()

        #groups_by_clue: dict(index of clue in unfinished_clues_list: adjacent group ids)
        groups_by_clue = get_groupings_by_clue(groups_dict, unfinished_clues_list, clue_index_dict)


        used_clues = [False] * len(unfinished_clues_list)
        used_groups = [False] * len(groups_dict)
        num_used_clues = 0
        
        # possibility fields:
        # total_mines (default:0)
        # num_cases (default:1)
        # mines_per_group: list where the ith element represents how many mines are in the group at 
        #                  groups_dict[i]
        ps = [Possibility(mines_per_group=[0] * len(groups_dict))]

        # mines_added_per_clue: list where the ith element represents how many mines need to be added to
        # satisfy the clue at unfinished_clues_list[i]
        mines_added_per_clue = [0] * len(clue_index_dict)
        for clue_loc, clue_index in clue_index_dict.items():
            clue = self.tiles[clue_loc[0]][clue_loc[1]]
            mines_added_per_clue[clue_index] = clue.num_adj_mines-clue.num_adj_flags
        while (num_used_clues < len(unfinished_clues_list)):
            best_clue = -1
            best_clue_boundary = len(groups_dict) + 1
            for clue_index in clue_index_dict.values():
                if used_clues[clue_index]:
                    continue
                used_clues[clue_index] = True
                boundary = get_boundary(groups_dict,used_clues)
                supergroups = get_boundary_supergroups(groups_dict,used_clues,boundary)
                used_clues[clue_index] = False
                boundary_change = len(supergroups)
                if boundary_change < best_clue_boundary:
                    best_clue = clue_index
                    best_clue_boundary = boundary_change
        
            used_clues[best_clue] = True
            num_used_clues += 1
            boundary = get_boundary(groups_dict,used_clues)
            supergroups = get_boundary_supergroups(groups_dict,used_clues,boundary)

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

                extend_possibility(p,mines_to_add,groups_to_use,new_ps,len(groups_to_use)-1,groups_dict)
            valid_ps = []
            for p in new_ps:
                if p.total_mines <= self.minecount - self.flag_count:
                    valid_ps.append(p)
            ps = valid_ps
        return groups_dict, ps

    def calc_prob_at_loc(self,loc,groups_dict,ps,nonfrontier_locs):
        x,y=loc
        tile = self.tiles[x][y]
        if not tile.is_unknown():
            return 0
        
        num_local_sols_at_count = defaultdict(int)
        for p in ps:
            num_local_sols_at_count[p.total_mines] += p.num_cases
        
        ps_with_num_mines = defaultdict(list)

        for p in ps:
            ps_with_num_mines[p.total_mines].append(p)

        total_sols_dict = defaultdict(int)
        for num_mines in ps_with_num_mines.keys():
            mines_left = self.minecount-self.flag_count-num_mines
            total_sols_at_num_mines = num_local_sols_at_count[num_mines] * comb(len(nonfrontier_locs),mines_left)
            total_sols_dict[num_mines] = total_sols_at_num_mines
        #print(total_sols_dict)
        total_sols = sum(total_sols_dict.values())
        if (x,y) in nonfrontier_locs:
            prob_dist = {mc: num_sols_for_mc / total_sols for mc, num_sols_for_mc in total_sols_dict.items()}
            mines_left = len(self.mines) - self.flag_count

            prob_nf = prob.calc_prob_for_nonfrontier_tiles(prob_dist,mines_left,len(nonfrontier_locs))
            

            return prob_nf
        
        group_id = -1
        group_size = -1
        for id,info in groups_dict.items():
            if loc in info.tile_locs:
                group_size = len(info.tile_locs)
                group_id = id
                break
        assert group_id >=0


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

    def calc_probs_for_board(self,groups_dict,ps):
        frontier_locs = set()
        for region in self.regions_list:
            for l in region.locs:
                frontier_locs.add(l)
        nonfrontier_locs = set()
        for r in range(self.rows):
            for c in range(self.cols):
                if (r,c) not in frontier_locs and self.tiles[r][c].is_unknown():
                    nonfrontier_locs.add((r,c))
        safe_locs = []
        mine_locs = []
        for group_info in groups_dict.values():
            group_locs = group_info.tile_locs
            rep_loc = group_locs[0]
            prob_at_loc = self.calc_prob_at_loc(rep_loc,groups_dict,ps,nonfrontier_locs)
            for loc in group_locs:
                tile = self.tiles[loc[0]][loc[1]]
                tile.prob_mine_local = prob_at_loc
                if prob_at_loc == 0:
                    safe_locs.append(loc)
                elif prob_at_loc == 1:
                    mine_locs.append(loc)

        if len(nonfrontier_locs) > 0:
            
            nf_loc = None
            for nf_l in nonfrontier_locs:
                nf_loc = nf_l
                break
            prob_at_loc = self.calc_prob_at_loc(nf_loc,groups_dict,ps,nonfrontier_locs)
            for loc in nonfrontier_locs:
                tile = self.tiles[loc[0]][loc[1]]
                tile.prob_mine_local = prob_at_loc
                if prob_at_loc == 0:
                    safe_locs.append(loc)
                elif prob_at_loc == 1:
                    mine_locs.append(loc)
        self.nonfrontier_tiles = sorted(list(nonfrontier_locs))
        return safe_locs,mine_locs
    
    def solve_exhaustive(self):
        ccs = self.get_ccs()
        regions = self.convert_ccs_to_regions(ccs)
        for region in regions:
            groups = self.group_equivalent_tiles(region)
            #groups = self.order_groups_by_information(groups)
            region.groups = groups
            self.regions_list.append(region)
        groups_dict,ps = self.find_possibilities()
        return self.calc_probs_for_board(groups_dict,ps)
    def solve_endgame_and_open(self):
        return False
    

def extend_possibility(p, mines_to_add, groups_to_use, new_ps, n, groups_dict):

    if n < 0:
        if mines_to_add == 0:
            new_ps.append(p)
    else:
        group_to_use = groups_to_use[n]
        group_len = len(groups_dict[group_to_use].tile_locs)
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
                extend_possibility(new_p,mines_to_add-used_mines,groups_to_use,new_ps,n-1,groups_dict)





def extend_possibilities(p, mines_to_add, groups_to_use, new_ps, supergroups, n, groups_dict):
    if n <0:
        if mines_to_add == 0:
            add_possibility(p,new_ps,supergroups,groups_dict)
        return
    
    first_group = groups_to_use[n]
    group_len = len(groups_dict[first_group].tile_locs)

    if n == 0:
        if mines_to_add >= 0 and mines_to_add <= group_len:
            multiplier = comb(group_len,mines_to_add)
            new_group_map = []
            for i in range(len(groups_dict)):
                new_group_map.append(p.mines_per_group[i] * multiplier)
            new_group_map[first_group] = mines_to_add * p.num_cases * multiplier
            new_p = Possibility(total_mines=p.total_mines + mines_to_add,
                                num_cases=p.num_cases*multiplier,mines_per_group=new_group_map)
            add_possibility(new_p, new_ps, supergroups,groups_dict)
        return
    max_mines = group_len
    for used_mines in range(max_mines+1):
        multiplier = comb(max_mines,used_mines)
        new_group_map = []
        for i in range(len(groups_dict)):
            new_group_map.append(p.mines_per_group[i] * multiplier)
        new_group_map[first_group] = used_mines * p.num_cases * multiplier
        new_p = Possibility(total_mines=p.total_mines + used_mines,
                            num_cases=p.num_cases*multiplier,mines_per_group=new_group_map)
        extend_possibilities(new_p,mines_to_add-used_mines,groups_to_use,new_ps,supergroups,n-1,groups_dict)
    return

def normalize(p, supergroups):
    total_mines = p.total_mines
    norm_string = str(total_mines)
    num_cases = p.num_cases
    for supergroup in supergroups:
        minecount = 0
        for group_id in supergroup:
            minecount += p.mines_per_group[group_id]

        mines_in_supergroup = round(minecount/num_cases)
        norm_string += str(mines_in_supergroup)
    return norm_string

def add_possibility(p, pmap, supergroups,groups_dict):
    key = normalize(p,supergroups)
    if key in pmap:
        combined = pmap[key]
        combined.num_cases += p.num_cases
        for i in range(len(groups_dict)):
            combined.mines_per_group[i] += p.mines_per_group[i]
        pmap[key] = combined
    else:
        pmap[key] = p

def get_groupings_by_clue(groups_dict, unfinished_clues_list, clue_index_dict):
    # Initialize an empty list of groups for each clue index
    groupings_by_clue = {
        clue_index_dict[clue_loc]: [] for clue_loc in unfinished_clues_list
    }

    # Fill in the groupings by clue
    for group_id, group_info in groups_dict.items():
        for clue_index in group_info.clue_indices:
            groupings_by_clue[clue_index].append(group_id)

    return groupings_by_clue

# boundary: ids of groups which are adjacent to both used and unused clues
def get_boundary(groups, used_clues):
    boundary = []
    for group_id,info in groups.items():
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
        

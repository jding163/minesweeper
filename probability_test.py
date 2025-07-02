from game_state_manager import GSM
from collections import Counter
import copy
import math
from collections import defaultdict
from settings import *
#board = None

def calc_probs_from_grouped_sols(groups,sols,return_probs=True):
    num_sols_per_group = []
    for i in range(len(sols)):
        sol = sols[i]
        num_sols_in_group = 1
        # compute total combinations for a given solution
        for j in range(len(groups)):
            num_sols_in_group *= math.comb(len(groups[j]), sol[j])
        num_sols_per_group.append(num_sols_in_group)
    num_sols_total = sum(num_sols_per_group)

    sol_instances = []
    for i in range(len(sols)):
        instances = [(num * num_sols_per_group[i]) for num in sols[i]]
        sol_instances.append(instances)
    sum_cols = [sum(x) for x in zip(*sol_instances)]
    probs_per_group = [sum/num_sols_total for sum in sum_cols]
    if return_probs:
        return probs_per_group, num_sols_per_group
    else:
        return sum_cols,num_sols_per_group

def get_sol_counts(board):

    frontier_tiles = set()
    regions = board.get_regions()
    #region_locs = [region.locs for region in regions]
    for region in regions:
        for loc in region.locs:
            frontier_tiles.add(loc)


    nonfrontier_tiles = []
    for row in range(GSM.rows):
        for col in range(GSM.cols):
            if board.get_type_at_loc((row,col)) == UNKNOWN and (row,col) not in frontier_tiles:
                nonfrontier_tiles.append((row,col))
    board.nonfrontier_tiles = nonfrontier_tiles

    local_freqs = [region.freqs for region in board.regions_list]
    global_freqs,subdivs = convolve_freqs(local_freqs)
    sols_per_mines_in_frontier = defaultdict(int)
    for num_mines,freq in global_freqs.items():
        
        mines_nonfrontier = GSM.mine_count - board.flag_count - num_mines
        if mines_nonfrontier >=0:
            num_sols_for_nonfrontier = math.comb(len(nonfrontier_tiles),mines_nonfrontier)
            sols_per_mines_in_frontier[num_mines] = num_sols_for_nonfrontier * freq
    print(sols_per_mines_in_frontier)
    print(sum(sols_per_mines_in_frontier.values()))
    # print(local_freqs)
    # print(subdivs)
    return sols_per_mines_in_frontier, subdivs

def calc_global_prob_for_group(board,group,sols_per_mines_in_frontier,subdivs):
    regions = board.regions_list

    region_index = [i for i, region in enumerate(regions) if group in region.groups][0]

    region = regions[region_index]
    groups = region.groups

    sols = region.group_sols
    counts = region.group_counts
    sols_with_counts = list(zip(sols,counts))
    freqs = region.freqs
    group_index = find_matching_indices(groups,group)[0]

    num_sols = 0
    for freq in freqs.keys():
        matching_sols = [(sol,count) for sol,count in sols_with_counts if sum(sol) == freq]
        group_probs = calc_probs_from_grouped_sols(groups,[sol[0] for sol in matching_sols])
        if len(group_probs[0]) > 0:
            loc_prob_at_given_freq = group_probs[0][group_index]/len(groups[group_index])
            for num_mines, configs in subdivs.items():
                configs_at_given_freq = [config for config in configs if config[region_index] == freq]
                matching_configs = len(configs_at_given_freq)/len(configs)
                num_sols_at_freq = matching_configs * loc_prob_at_given_freq * sols_per_mines_in_frontier[num_mines]
                num_sols += num_sols_at_freq
    total_sols = sum(sols_per_mines_in_frontier.values())

    global_prob = num_sols/total_sols
    return global_prob

# def calc_prob_that_loc_is_value(board,loc,sols_per_mines_in_frontier,subdivs):
#     regions = board.regions_list


#     neighbor_locs = [n.locs for n in board.get_neighbor_tiles(loc) if n.is_unknown()]
#     regions_to_combine = [r for r in regions if any(neighbor_locs) in r.locs]

#     region_index = [i for i, region in enumerate(regions) if group in region.groups][0]

#     region = regions[region_index]
#     groups = region.groups

#     sols = region.group_sols
#     counts = region.group_counts
#     sols_with_counts = list(zip(sols,counts))
#     freqs = region.freqs
#     group_index = find_matching_indices(groups,group)[0]

#     num_sols = 0
#     for freq in freqs.keys():
#         matching_sols = [(sol,count) for sol,count in sols_with_counts if sum(sol) == freq]
#         group_probs = calc_probs_from_grouped_sols(groups,[sol[0] for sol in matching_sols])
#         if len(group_probs[0]) > 0:
#             loc_prob_at_given_freq = group_probs[0][group_index]/len(groups[group_index])
#             for num_mines, configs in subdivs.items():
#                 configs_at_given_freq = [config for config in configs if config[region_index] == freq]
#                 matching_configs = len(configs_at_given_freq)/len(configs)
#                 num_sols_at_freq = matching_configs * loc_prob_at_given_freq * sols_per_mines_in_frontier[num_mines]
#                 num_sols += num_sols_at_freq
#     total_sols = sum(sols_per_mines_in_frontier.values())

#     global_prob = num_sols/total_sols
#     return global_prob

def find_matching_indices(locs, targets):
    target_set = set(map(tuple, targets)) 
    result = []

    for i, sublist in enumerate(locs):
        if any(tuple(coord) in target_set for coord in sublist):
            result.append(i)

    return result

# freqs is a list of dicts
def convolve_freqs(freqs):
    if len(freqs) == 0:
        return {},{}
    total_freqs = Counter()
    subdivs = defaultdict(list)
    for tm,tc in freqs[0].items():
        convolve_freqs_helper(freqs,1,tm,tc,total_freqs,subdivs,[tm])
    return total_freqs,subdivs

def convolve_freqs_helper(freqs, index, total_mines, total_count, total_freqs,subdivs,subdiv):
    if index == len(freqs):
        total_freqs[total_mines] += total_count
        subdivs[total_mines].append(subdiv)
    else:
        for tm,tc in freqs[index].items():
            new_tm = total_mines + tm
            new_tc = total_count * tc
            new_subdiv = [num for num in subdiv]
            new_subdiv.append(tm)
            convolve_freqs_helper(freqs,index+1,new_tm,new_tc,total_freqs,subdivs,new_subdiv)

def calc_prob_for_nonfrontier_tiles(prob_dist, mines_left, num_nonfrontier_tiles):
    total_prob = 0

    for mines_in_border, prob in prob_dist.items():
        mines_out_border = mines_left - mines_in_border
        if 0 <= mines_out_border <= num_nonfrontier_tiles:
            safe_prob = (num_nonfrontier_tiles - mines_out_border) / num_nonfrontier_tiles
            total_prob += prob * safe_prob
    return 1-total_prob


# idea: in order for (x,y) to be an opening, all of its neighbors as well as (x,y) must be safe
# for each revealed tile, check if tile is flagged. if so, (x,y) cannot be an opening
# for each non-revealed tile, check probability that unrevealed neighbors are mines. 
# for all neighbors contained in one frontier, check how many solutions exist where neighbors are safe. if
# (x,y) also belongs to this frontier, (x,y) also needs to be safe. then take found_solutions/total_solutions
# to get the probability those tiles are safe
# not all neighbors of (x,y) are guaranteed to be in the same frontier. if they are not, do this calculation
# for each frontier and multiply the results
# for non-frontier tiles, it's possible that minecount guarantees that a mine exists within the region, 
# in which case it is guranteed that (x,y) is not an opening
# to check for this case, check if (# of remaining flags) - (max # of frontier mines) 
# - (# of non-frontier tiles not bordering (x,y))
# let n be the result of the computation. if n > 0, (x,y) cannot be an opening. if n <=0, it is possible.
# to get the chance for an opening, multiply the safe probs of all non-frontier tiles, including (x,y) if
# it is a non-frontier tile
# then take the product of the frontier and nonfrontier mine probabilities
# note that this calculation is NOT the chance that (x,y) is an opening assuming (x,y) is safe; it assumes 
# that (x,y) may or may not be a mine
def calc_prob_of_opening_at_loc(board,loc):
    if loc == (0,1):
        pass
    
    curr_tile = board.tiles[loc[0]][loc[1]]
    if curr_tile.is_revealed()  or curr_tile.is_flagged():
        return
    

    tiles_to_check = board.get_neighbor_tiles(loc)
    #t = [tile.loc for tile in tiles_to_check]
    # if (loc == (0,0)):
    #     print(t)

    tiles_to_check.append(curr_tile)
    prob_safe_nonfrontier = 1
    prob_safe_frontier = 1
    frontier_tiles = set()
    frontier_tile_locs = set()
    num_nonfrontier_tiles = 0

    for tile in tiles_to_check:
        if tile.is_flagged():
            curr_tile.prob_opening = 0
            return curr_tile.prob_opening
        elif not tile.is_revealed():
            if tile.loc in board.nonfrontier_tiles:
                num_nonfrontier_tiles += 1 
                prob_safe_nonfrontier *= (1-tile.prob_mine_local)
            else:
                frontier_tiles.add(tile)
                frontier_tile_locs.add(tile.loc)
    # print(frontier_tile_locs)
    # print(num_nonfrontier_tiles)
    if len(board.mines) == 0:
        curr_tile.prob_opening = prob_safe_frontier * prob_safe_nonfrontier
        return curr_tile.prob_opening

    mines_left = len(board.mines) - board.flag_count

    # local_freqs = []
    # for region in board.regions_list:
    #     local_freqs.append(region.freqs)
    local_freqs = [region.freqs for region in board.regions_list]

    global_freqs,_ = convolve_freqs(local_freqs)
    if len(global_freqs) == 0:
        max_mines_in_frontier = 0
    else:
        max_mines_in_frontier = max(global_freqs)
    if mines_left - max_mines_in_frontier - len(board.nonfrontier_tiles) + num_nonfrontier_tiles > 0:
        prob_safe_nonfrontier = 0
        prob_safe_frontier = 0
    

    else:
        if loc == (2,10):
            pass
        regions = board.regions_list
        relevant_regions = {}

        for region in regions:
            indices = find_matching_indices(region.groups,frontier_tile_locs)
            if len(indices) > 0:
                relevant_regions[region] = indices
        num_valid_sols = 0

        for region, indices in relevant_regions.items():
            groups = region.groups
            sols = region.group_sols
            total = region.num_sols
            counts = region.group_counts
            sols_with_counts = zip(sols,counts)
            locs = [groups[i] for i in indices]
            for group in locs:
                group_prob = 0

                for l in group:
                    if l in frontier_tile_locs:
                        x,y =l
                        group_prob += board.tiles[x][y].prob_mine_local
                prob_safe_frontier *= 1-group_prob
        #   max_mines_per_group = []

        #     for group in locs:
        #         max_mines = len(group)-len(set(frontier_tile_locs).intersection(set(group)))
        #         max_mines_per_group.append(max_mines)

        #     valid_sols = [
        #         (sol, count) for sol, count in sols_with_counts
        #         if all(sol[i] <= max_mines_per_group[j] for j,i in enumerate(indices))
        #     ]    

        #     sliced_valid_sols = [([sol[i] for i in indices], count) for sol, count in valid_sols]
        #     print(loc)
        #     print(valid_sols)
        #     for sol,count in valid_sols:
        #         num_mines = sum(sol)
        #         mines_nonfrontier = GSM.mine_count - board.flag_count - num_mines
        #         count *= math.comb(len(board.nonfrontier_tiles),mines_nonfrontier)
                
        #         sliced_sol = [sol[i] for i in indices]

        #         for j,num_mines in enumerate(sliced_sol):

        #             group = groups[indices[j]]
        #             len_group = len(group)
        #             if len_group == 1:
        #                 continue
        #             print(group)
        #             combs = math.comb(max_mines_per_group[j],num_mines)/math.comb(len_group,num_mines)
        #             #combs = 1-((len_group - max_mines_per_group[j])/len_group)
        #             print(combs)
        #             count *= combs
        #             #count *= (max_mines_per_group[j] - num_mines)/len_group
        #         num_valid_sols += count 
        # prob_safe_frontier *= num_valid_sols/board.total_sols
            
    curr_tile.prob_opening = prob_safe_frontier * prob_safe_nonfrontier
    return curr_tile.prob_opening

def calc_prob_of_opening_for_board(board):
    for x in range(GSM.rows):
        for y in range(GSM.cols):
            tile = board.tiles[x][y]
            if not tile.is_revealed() and not tile.is_flagged():
                calc_prob_of_opening_at_loc(board,(x,y))
                


def update_nonfrontier_tile_probs(board):
    #determine probs for non-border tiles
    if len(board.nonfrontier_tiles) > 0:

        if len(board.regions_list) == 0:
            for x,y in board.nonfrontier_tiles:
                prob_mine_local = (GSM.mine_count - board.flag_count)/len(board.nonfrontier_tiles)
                board.tiles[x][y].prob_mine_local = prob_mine_local

        else:
            local_freqs = [region.freqs for region in board.regions_list]

            global_freqs,_ = convolve_freqs(local_freqs)        
            num_sols_total = sum(global_freqs.values())
            prob_dist = {mc: num_sols_for_mc / num_sols_total for mc, num_sols_for_mc in global_freqs.items()}
            mines_left = len(board.mines) - board.flag_count
            prob_for_nonfrontier_tiles = calc_prob_for_nonfrontier_tiles(prob_dist,mines_left,len(board.nonfrontier_tiles))
            for x,y in board.nonfrontier_tiles:
                board.tiles[x][y].prob_mine_local = prob_for_nonfrontier_tiles
            return global_freqs
    return None


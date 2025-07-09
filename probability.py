from game_state_manager import GSM
from collections import Counter
import copy
import math
from math import comb
from collections import defaultdict
from settings import *
from itertools import combinations, product
from scipy import stats
from line_profiler import profile

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



def calc_global_prob_for_group(merged_regions,group,sols_per_mines_in_frontier):
    # merged_regions = regions[0]
    # for i in range(1,len(regions)):
    #     merged_regions = merged_regions.merge_regions(regions[i])
    #merged_regions = board.merge_multiple_regions(regions)
    sols = merged_regions.group_sols
    counts = merged_regions.group_counts
    freqs = merged_regions.freqs
    groups = merged_regions.groups
    sols_with_counts = list(zip(sols,counts))
    group_index = find_matching_indices(groups,group)[0]

    average_mines_in_group_at_freq = {}
    for freq in freqs.keys():
        matching_sols = [(sol,count) for sol,count in sols_with_counts if sum(sol) == freq]
        sliced_sols = [(sol[group_index],count) for sol,count in matching_sols]
        total_weighted_mines = sum(x * y for x, y in sliced_sols)
        total_occurrences = sum(y for _, y in sliced_sols)
        average_mines = total_weighted_mines / total_occurrences if total_occurrences > 0 else 0
        average_mines_in_group_at_freq[freq] = average_mines
    # print('group:',group)

    # print('avg_mines:',average_mines_in_group_at_freq)
    numerator = sum(
        average_mines_in_group_at_freq[freq] * sols_per_mines_in_frontier[freq]
        for freq in average_mines_in_group_at_freq
    )

    denominator = sum(sols_per_mines_in_frontier.values())

    overall_average = numerator / denominator if denominator > 0 else 0

    global_prob = overall_average/len(group)
    #print('gp:',global_prob)
    # print(board.sols_per_mines_in_frontier)
    # print(total_sols)
    return global_prob

def distribute_ones(n, length):
    """Generate all binary lists of a given length with n ones."""
    if n > length:
        return []
    result = []
    for ones_positions in combinations(range(length), n):
        arr = [0] * length
        for pos in ones_positions:
            arr[pos] = 1
        result.append(arr)
    return result

def expand_sols_flat(sols, groups):
    lens = [len(group) for group in groups]
    all_group_distributions = []
    for count, length in zip(sols, lens):
        if length == 0:
            all_group_distributions.append([[]])
        elif count == 0:
            all_group_distributions.append([[0] * length])
        else:
            all_group_distributions.append(distribute_ones(count, length))

    # Cartesian product to form all full combinations
    grouped_sols = product(*all_group_distributions)

    # Flatten each solution across all groups
    flattened_sols = [sum(solution, []) for solution in grouped_sols]
    return flattened_sols

def expand_batch(batch_sols, groups):
    all_flattened = []
    for sols in batch_sols:
        expanded = expand_sols_flat(sols, groups)
        all_flattened.extend(expanded)
    return all_flattened

def convolve_mine_distributions(dist_frontier, nf, prob_nonfrontier_tile,prob_mine_local,adj_flags,eps=0.00005):
    # print(dist_frontier)
    # print(nf)
    # print(prob_nonfrontier_tile)
    # print(prob_mine_local)

    dist_total = defaultdict(float)
    if nf ==0:
        for k, p in dist_frontier.items():
            dist_total[k] = p
    elif len(dist_frontier) == 0:
        for total_mines in range(nf + 1):
            dist_total[total_mines] = float(stats.binom.pmf(total_mines, nf, prob_nonfrontier_tile))
    else:
        frontier_dict = dict(dist_frontier)
        max_total = max(frontier_dict) + nf

        for total_mines in range(max_total + 1):
            for frontier_mines in range(0, total_mines + 1):
                nonfrontier_mines = total_mines - frontier_mines
                if (frontier_mines in frontier_dict and 0 <= nonfrontier_mines <= nf):
                    p_frontier = frontier_dict[frontier_mines]
                    p_nonfrontier = stats.binom.pmf(nonfrontier_mines, nf, prob_nonfrontier_tile)
                    dist_total[total_mines] += p_frontier * p_nonfrontier

    for key in dist_total.keys():
        dist_total[key] = float(dist_total[key] * (1-prob_mine_local))
    new_dict = defaultdict(lambda:0)
    for k,v in dist_total.items():
        new_dict[k+adj_flags] = v
    sum_probs = sum(new_dict.values())
    # print('dict:',new_dict)
    # print('sum_probs:',sum_probs)
    # print('prob_mine_local:',prob_mine_local)
    err = abs((1-sum_probs)-prob_mine_local)
    #print('err:',err)

    assert err < eps, f'error: {err}'


    return new_dict

def calc_prob_opening_for_loc(board,loc):
    num_sols = board.total_sols
    count,_ = board.get_sol_counts_at_loc_for_val(loc,0)
    return count/num_sols

# def calc_sec_safety_at_loc(board,loc):
#     min_flags = 0
#     max_flags = 0
#     neighbors = board.get_neighbor_tiles(loc)
#     for n in neighbors:
#         if n.type == MINE:
#             min_flags+=1
#         elif n.type == UNKNOWN:
#             max_flags +=1
#     max_flags += min_flags
#     probs = defaultdict(float)
#     num_sols = board.total_sols
#     for i in range(min_flags,max_flags+1):
#         count,best_prob = board.get_sol_counts_at_loc_for_val(loc,i)
#         if count > 0:
#             probs[i] = (count/num_sols,1-best_prob)
#     print(loc)
#     sec_safety = sum([x * y for x,y in probs.values()])
#     return sec_safety,probs
#     # neighbor_locs = [n.loc for n in board.get_neighbor_tiles(loc) if n.is_unknown()]
#     # nonfrontier_neighbor_locs = [n for n in neighbor_locs if n in board.nonfrontier_tiles]
#     # frontier_neighbor_locs = [n for n in neighbor_locs if n not in nonfrontier_neighbor_locs]
#     # if loc not in board.nonfrontier_tiles:
#     #     frontier_neighbor_locs.append(loc)

#     # regions_to_merge = board.regions_list

#     # vals_dict_frontier = defaultdict(lambda:1)
#     # adj_flags = board.tiles[loc[0]][loc[1]].num_adj_flags

#     # if len(frontier_neighbor_locs) > 0 and len(regions_to_merge) >= 1:
#     #     #region = board.merge_multiple_regions(regions_to_merge)
#     #     region = regions_to_merge[0]

#     #     if len(regions_to_merge) > 1:
#     #         for i in range(1,len(regions_to_merge)):
#     #             region = board.merge_regions(region,regions_to_merge[i])

#     #     groups = region.groups

#     #     sols = region.group_sols
#     #     freqs = region.freqs


#     #     counts = region.group_counts
#     #     sols_with_counts = list(zip(sols,counts))
#     #     neighbor_indices = find_matching_indices(groups,frontier_neighbor_locs)
#     #     neighbor_indices_with_counts = defaultdict(int)
#     #     for i in neighbor_indices:
#     #         group = groups[i]
#     #         for l in group:
#     #             if l in frontier_neighbor_locs:
#     #                 neighbor_indices_with_counts[i] += 1

#     #     num_sols_at_val = defaultdict(int)
#     #     for freq in freqs.keys():

#     #         # if loc in frontier_neighbor_locs:
#     #         #     loc_index = find_matching_indices(groups,[loc])[0]
#     #         #     matching_sols = [
#     #         #         (sol,count) for (sol,count) in sols_with_counts
#     #         #         if sol[loc_index] < len(groups[loc_index]) and sum(sol) == freq
#     #         #     ]
#     #         # else:
#     #         matching_sols = [(sol,count) for sol,count in sols_with_counts if sum(sol) == freq]

#     #         num_matching_sols = sum([count for _,count in matching_sols])
#     #         matching_sols_at_val = defaultdict(int)
#     #         for sol,_ in matching_sols:
#     #             counts_dicts = []

#     #             for idx in range(len(sol)):
#     #                 group = groups[idx]
#     #                 num_mines = sol[idx]
#     #                 if idx in neighbor_indices:

#     #                     num_tiles = neighbor_indices_with_counts[idx]
#     #                     counts = hypergeometric_counts(len(group),num_tiles,num_mines)
#     #                 else:
#     #                     counts = {0:math.comb(len(group), num_mines)}
#     #                 counts_dicts.append(counts)
#     #             merged = convolve_freqs(counts_dicts)

#     #             for num_mines, count in merged.items():
#     #                 matching_sols_at_val[num_mines] += count
            
            
#     #         for num_mines,num_sols in matching_sols_at_val.items():
#     #             frac = num_sols/num_matching_sols
#     #             num_sols_at_freq = board.sols_per_mines_in_frontier[freq]*frac
#     #             num_sols_at_val[num_mines] += num_sols_at_freq



#     #     # flat_sols = expand_batch(sols,groups)
#     #     # flat_groups = sum(groups,[])

#     #     # neighbor_indices = [flat_groups.index(l) for l in frontier_neighbor_locs]
#     #     # print('total sols:', len(flat_sols))

#     #     # num_sols_at_val = defaultdict(int)

#     #     # for freq in freqs.keys():
#     #     #     if loc in frontier_neighbor_locs:
#     #     #         loc_index = flat_groups.index(loc)
#     #     #         matching_sols = [
#     #     #             sol for sol in flat_sols
#     #     #             if sol[loc_index] == 0 and sum(sol) == freq
#     #     #         ]
#     #     #     else:
#     #     #         matching_sols = [sol for sol in flat_sols if sum(sol) == freq]
#     #     #     print(f'{freq}:',len(matching_sols))
#     #     #     matching_sols_at_val = defaultdict(int)
#     #     #     for sol in matching_sols:
#     #     #         neighbor_sum = sum(sol[i] for i in neighbor_indices)
#     #     #         matching_sols_at_val[neighbor_sum] += 1
#     #     #     print(f'{freq}:',sorted(matching_sols_at_val.items()))
#     #     #     for num_mines,num_sols in matching_sols_at_val.items():
#     #     #         frac = num_sols/len(matching_sols)
#     #     #         num_sols_at_freq = board.sols_per_mines_in_frontier[freq]*frac
#     #     #         num_sols_at_val[num_mines] += num_sols_at_freq



#     #     total_sols = sum(board.sols_per_mines_in_frontier.values())
#     #     for num_mines,num_sols in num_sols_at_val.items():
#     #         global_prob_for_frontier_tiles = num_sols/total_sols
#     #         #if loc not in frontier_neighbor_locs:
#     #         x1,y1 = loc
#     #         loc_prob = board.tiles[x1][y1].prob_mine_local
#     #         #global_prob_for_frontier_tiles *= 1-loc_prob
#     #         vals_dict_frontier[num_mines] *= global_prob_for_frontier_tiles
#     # nf = len(nonfrontier_neighbor_locs)
#     # nf_prob = 0
#     # if nf>0:
#     #     x,y = nonfrontier_neighbor_locs[0]
#     #     nf_prob = board.tiles[x][y].prob_mine_local
#     # x1,y1 = loc
#     # loc_prob = board.tiles[x1][y1].prob_mine_local
#     # vals_dict_frontier = {k:v for k,v in vals_dict_frontier.items() if v > 0}
#     # total_distribution = convolve_mine_distributions(vals_dict_frontier, nf,nf_prob, loc_prob,adj_flags)
#     # return total_distribution

def find_matching_indices(locs, targets):
    if not isinstance(targets,list):
        targets = [targets]
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
def calc_local_prob_of_opening_at_loc(board,loc):
    curr_tile = board.tiles[loc[0]][loc[1]]
    if curr_tile.is_revealed()  or curr_tile.is_flagged():
        return
    

    tiles_to_check = board.get_neighbor_tiles(loc)

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
    if len(board.mines) == 0:
        curr_tile.prob_opening = prob_safe_frontier * prob_safe_nonfrontier
        return curr_tile.prob_opening

    mines_left = len(board.mines) - board.flag_count

    local_freqs = [region.freqs for region in board.regions_list]

    global_freqs = convolve_freqs(local_freqs)
    if len(global_freqs) == 0:
        max_mines_in_frontier = 0
    else:
        max_mines_in_frontier = max(global_freqs)
    if mines_left - max_mines_in_frontier - len(board.nonfrontier_tiles) + num_nonfrontier_tiles > 0:
        prob_safe_nonfrontier = 0
        prob_safe_frontier = 0
    

    else:
        regions = board.regions_list
        relevant_regions = {}

        for region in regions:
            indices = find_matching_indices(region.groups,frontier_tile_locs)
            if len(indices) > 0:
                relevant_regions[region] = indices

        for region, indices in relevant_regions.items():
            groups = region.groups
            locs = [groups[i] for i in indices]
            for group in locs:
                group_prob = 0

                for l in group:
                    if l in frontier_tile_locs:
                        x,y =l
                        group_prob += board.tiles[x][y].prob_mine_local
                prob_safe_frontier *= 1-group_prob
    curr_tile.prob_opening = prob_safe_frontier * prob_safe_nonfrontier
    return curr_tile.prob_opening

def calc_prob_of_opening_for_board(board):
    for x in range(GSM.rows):
        for y in range(GSM.cols):
            tile = board.tiles[x][y]
            if not tile.is_revealed() and not tile.is_flagged():
                calc_local_prob_of_opening_at_loc(board,(x,y))
                


def update_nonfrontier_tile_probs(board):
    #determine probs for non-border tiles
    if len(board.nonfrontier_tiles) > 0:

        if len(board.regions_list) == 0:
            for x,y in board.nonfrontier_tiles:
                prob_mine_local = (GSM.mine_count - board.flag_count)/len(board.nonfrontier_tiles)
                board.tiles[x][y].prob_mine_local = prob_mine_local

        else:
            local_freqs = [region.freqs for region in board.regions_list]

            global_freqs = convolve_freqs(local_freqs)        
            num_sols_total = sum(global_freqs.values())
            prob_dist = {mc: num_sols_for_mc / num_sols_total for mc, num_sols_for_mc in global_freqs.items()}
            mines_left = len(board.mines) - board.flag_count
            prob_for_nonfrontier_tiles = calc_prob_for_nonfrontier_tiles(prob_dist,mines_left,len(board.nonfrontier_tiles))
            for x,y in board.nonfrontier_tiles:
                board.tiles[x][y].prob_mine_local = prob_for_nonfrontier_tiles
            return global_freqs
    return None

# x = group size
# y = neighbors in group
# z = number of mines in group
# want to find distribution of counts on how many of the y tiles are mines

def hypergeometric_counts(x, y, z):
    counts = {}
    min_k = max(0, z - (x - y))
    max_k = min(y, z)

    total = 0
    for k in range(min_k, max_k + 1):
        count = comb(y, k) * comb(x - y, z - k)
        counts[k] = count
        total += count

    assert total == comb(x, z), f"Sum {total} does not equal total combinations {comb(x, z)}"
    return counts

def hypergeometric_distribution(x, y, z):
    """
    Returns a dictionary: {k: P(k)}, where k is the number of special items picked.
    """
    distribution = {}
    min_k = max(0, z - (x - y))
    max_k = min(y, z)
    total_ways = comb(x, z)

    for k in range(min_k, max_k + 1):
        special = comb(y, k)
        non_special = comb(x - y, z - k)
        prob = (special * non_special) / total_ways
        distribution[k] = prob

    return distribution
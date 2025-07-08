from game_state_manager import GSM
import probability as prob
import copy
import sprites
from settings import *
from collections import defaultdict
def calc_force_for_board(board):
    for x in range(GSM.rows):
        for y in range(GSM.cols):
            tile = board.tiles[x][y]
            if not tile.is_revealed() and not tile.is_flagged() and not (x,y) in board.nonfrontier_tiles:
                force = calc_force_at_loc(board,(x,y))
                tile.force = force

def calc_force_at_loc(board,loc):
    regions = board.regions_list
    region = [r for r in regions if loc in r.locs]
    if len(region) == 0:
        return -1
    region=region[0]
    groups = region.groups
    sols = region.group_sols
    group_index = prob.find_matching_indices(groups,[loc])[0]
    group_with_loc = groups[group_index]
    valid_sols = [sol for sol in sols if sol[group_index] < len(group_with_loc)]
    if len(group_with_loc) == 1:
        valid_sols = [sol[:group_index] + sol[group_index+1:] for sol in valid_sols]
        updated_groups = groups[:group_index] + groups[group_index+1:]
    else:
        loc_index = group_with_loc.index(loc)
        updated_group = group_with_loc[:loc_index] + group_with_loc[loc_index+1:]
        valid_sols = [sol for sol in valid_sols if sol[group_index] <= len(updated_group)]
        updated_groups = groups[:group_index] + [updated_group] + groups[group_index+1:]
    probs_per_group, _ = prob.calc_probs_from_grouped_sols(updated_groups,valid_sols)
    probs_per_group = [prob/len(groups[i]) for i, prob in enumerate(probs_per_group)]
    num_guaranteed_safe = 0
    num_guaranteed_mine = 0
    for i in range(len(probs_per_group)):
        prob_per_group = probs_per_group[i]
        if prob_per_group == 0:
            num_guaranteed_safe += len(updated_groups[i])
        elif prob_per_group == 1:
            num_guaranteed_mine += len(updated_groups[i])
    #force = (1-min(probs_per_group)) * board.tiles[loc[0]][loc[1]].prob_mine_local
    #force = (1-min(probs_per_group))
    force = num_guaranteed_safe

    return force


        

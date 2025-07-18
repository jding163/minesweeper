from game_state_manager import GSM
import probability as prob
import copy
import sprites
from settings import *
from collections import defaultdict
from dataclasses import dataclass


@dataclass(kw_only=True)
class ProgressInfo:
    loc: tuple
    sec_safety: float
    probs_loc_is_val: dict
    best_ss_at_val: dict
    finished: bool
    expected_clears: dict
# def find_loc_with_best_progress_over_locs(board,locs):
#     if len(locs) == 0:
#         return None
#     threshold = -1
#     best_loc = None
#     for loc in locs:
#         # print(f'loc: {loc}')
#         sec_safety_so_far, _, finished = calc_progress_info_at_loc(board,loc,threshold)
#         if finished and sec_safety_so_far > threshold:
#             threshold = sec_safety_so_far
#             best_loc = loc
#         # if finished:
#         #     print(f'ss: {sec_safety_so_far}')
#         # print(f'finished: {finished}')


#     # print(f'best: {best_loc}')
#     return best_loc
def find_loc_with_best_progress_over_locs(board,locs,expected_clears_weight=0.005):
    if len(locs) == 0:
        return None
    threshold = -1
    best_loc = None
    best_score = 0
    for loc in locs:
        info = calc_progress_info_at_loc(board,loc,threshold)

        if info.finished and info.sec_safety > threshold:
            # threshold = info.sec_safety
            # best_loc = loc
            expected_clear_score = 0
            for i in range(0,9):
                expected_clear_score += info.probs_loc_is_val[i] * info.expected_clears[i]
            
            final_score = info.sec_safety + expected_clear_score * expected_clears_weight
            if final_score > best_score:
                best_score = final_score
                threshold = info.sec_safety
                best_loc = loc
    return best_loc

def calc_progress_info_at_loc(board,loc,threshold,threshold_on=True):
    x,y=loc
    tile = board.tiles[x][y]
    prob_mine = tile.prob_mine_local
    min_flags = 0
    max_flags = 0
    neighbors = board.get_neighbor_tiles(loc)
    for n in neighbors:
        if n.type == MINE:
            min_flags+=1
        elif n.type == UNKNOWN:
            max_flags +=1
    max_flags += min_flags
    probs_loc_is_val = defaultdict(float) # value: prob that loc is value 
    best_ss_at_val = defaultdict(float) # value: best sec safety at val
    sec_safety_so_far = 0.0
    weight_so_far = 0.0
    num_sols = board.total_sols
    expected_clears = defaultdict(int)
    for i in range(min_flags, max_flags + 1):
        count, best_prob,min_num_safe = board.get_sol_counts_at_loc_for_val(loc, i)
        #print(f'{i}: {num_safe} clears')
        prob = count / num_sols
        val = 1 - best_prob
        probs_loc_is_val[i] = prob
        best_ss_at_val[i] = val
        expected_clears[i] = min_num_safe

        sec_safety_so_far += prob * val
        weight_so_far += prob

        # Check whether it's still possible to reach the threshold
        remaining_weight = 1.0-prob_mine - weight_so_far
        max_possible = sec_safety_so_far + remaining_weight
        # print(f'max possible at val {i}:',max_possible)
        if threshold_on and max_possible < threshold:
            return ProgressInfo(loc=loc,sec_safety=sec_safety_so_far,probs_loc_is_val=probs_loc_is_val,
                                expected_clears=expected_clears,best_ss_at_val=best_ss_at_val,
                                finished=False)

    # expected_clear_score = 0
    # for i in range(0,9):
    #     expected_clear_score += probs_loc_is_val[i] * expected_clears[i]
    # print('loc:', loc)
    # print('ecs:', expected_clear_score)
    return ProgressInfo(loc=loc,sec_safety=sec_safety_so_far,probs_loc_is_val=probs_loc_is_val,
                        expected_clears=expected_clears,best_ss_at_val=best_ss_at_val,finished=True)



        

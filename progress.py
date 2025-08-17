from game_state_manager import GSM
import probability as prob
import copy
import sprites
from settings import *
from collections import defaultdict
from dataclasses import dataclass
from line_profiler import profile



@dataclass(kw_only=True)
class ProgressInfo:
    loc: tuple
    sec_safety: float
    probs_loc_is_val: dict
    best_ss_at_val: dict
    finished: bool
    expected_clears: dict

def find_loc_with_best_progress_over_locs(board,locs,expected_clears_weight=0.005,ff_influence_weight=1.2):
    if len(locs) == 0:
        return None
    threshold = -1
    best_loc = None
    best_score = -1
    ff_influence_loc_info = dict()
    for loc in locs:
        if loc in board.ff_influence_locs:
            info = calc_progress_info_at_loc(board,loc,threshold/ff_influence_weight)
        else:
            info = calc_progress_info_at_loc(board,loc,threshold)

        score = info.sec_safety
        if loc in board.ff_influence_locs:
            ff_influence_loc_info[loc] = info
        # if loc in board.ff_influence_locs:
        #     init_score_worse = (score <= threshold)
        #     score *= ff_influence_weight
        #     post_score_better = (score > threshold)
        #     if not board.collected and (init_score_worse and post_score_better):
        #         board.collected=True
        if info.finished and score > threshold:
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
    if best_loc not in board.ff_influence_locs:
        old_best = best_score
        old_best_loc = best_loc
        for loc,info in ff_influence_loc_info.items():
            expected_clear_score = 0
            for i in range(0,9):
                expected_clear_score += info.probs_loc_is_val[i] * info.expected_clears[i]
            init_score = info.sec_safety + expected_clear_score * expected_clears_weight
            final_score = init_score * ff_influence_weight
            if final_score > best_score:
                best_score = final_score
                threshold = info.sec_safety
                best_loc = loc
        if not board.collected and best_loc in board.ff_influence_locs and old_best > best_score/ff_influence_weight and old_best < best_score:
            # print(old_best_loc)
            # print(old_best)
            # print(best_loc)
            # print(best_score)
            board.collected=True
    return best_loc
def calc_progress_info_at_loc(board,loc,threshold,threshold_on=True):
    prob_mine = board.mine_probs[loc]

    min_flags = 0
    max_flags = 0
    neighbors = board.lookup_neighbors(loc)
    for neighbor in neighbors:
        if board.tile_state_tracker[neighbor] == FLAGGED:
            min_flags+=1
        elif board.tile_state_tracker[neighbor] == UNKNOWN:
            max_flags +=1
    max_flags += min_flags
    probs_loc_is_val = defaultdict(float) # value: prob that loc is value 
    best_ss_at_val = defaultdict(float) # value: best sec safety at val
    sec_safety_so_far = 0.0
    weight_so_far = 0.0
    num_sols = board.total_sols
    expected_clears = defaultdict(int)
    # @dataclass 
    # class SolverHeuristics():
    #     total_count: int
    #     best_prob: float 
    #     num_safe: int
    #     has_ff: bool
    for i in range(min_flags, max_flags + 1):
        info = board.get_sol_counts_at_loc_for_val(loc, i)
        count= info.total_count
        best_prob = info.best_prob
        min_num_safe = info.num_safe
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
        #print('remaining_weight:',remaining_weight)
        max_possible = sec_safety_so_far + remaining_weight
        #print(f'max possible at val {i}:',max_possible)
        if threshold_on and max_possible < threshold:
            return ProgressInfo(loc=loc,sec_safety=sec_safety_so_far,probs_loc_is_val=probs_loc_is_val,
                                expected_clears=expected_clears,best_ss_at_val=best_ss_at_val,
                                finished=False)

    return ProgressInfo(loc=loc,sec_safety=sec_safety_so_far,probs_loc_is_val=probs_loc_is_val,
                        expected_clears=expected_clears,best_ss_at_val=best_ss_at_val,finished=True)



        

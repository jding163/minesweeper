from game_state_manager import GSM
import probability as prob
import copy
import sprites
from settings import *
from collections import defaultdict

class ProgressInfo:
    def __init__(self, loc,sec_safety, probs, expected_clears,early_exit):
        self.loc = loc
        self.sec_safety = sec_safety            # float ∈ [0,1], the weighted safety score
        self.probs = probs                      # dict[int, tuple[float, float]], {val at loc: (prob, best ss)}
        self.early_exit = early_exit            # bool, True if pruning happened early
        self.expected_clears = expected_clears  # dict[int, float], {val at loc: min safe clears}

def find_loc_with_best_progress_over_locs(board,locs):
    if len(locs) == 0:
        return None
    threshold = -1
    best_loc = None
    for loc in locs:
        info = calc_progress_info_at_loc(board,loc,threshold)
        if info.early_exit and info.sec_safety > threshold:
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
    probs = defaultdict(float)
    sec_safety_so_far = 0.0
    weight_so_far = 0.0
    num_sols = board.total_sols
    expected_clears = defaultdict(int)
    for i in range(min_flags, max_flags + 1):
        count, best_prob,min_num_safe = board.get_sol_counts_at_loc_for_val(loc, i)
        #print(f'{i}: {num_safe} clears')
        prob = count / num_sols
        val = 1 - best_prob
        probs[i] = (prob, val)
        expected_clears[i] = min_num_safe

        sec_safety_so_far += prob * val
        weight_so_far += prob

        # Check whether it's still possible to reach the threshold
        remaining_weight = 1.0-prob_mine - weight_so_far
        max_possible = sec_safety_so_far + remaining_weight
        # print(f'max possible at val {i}:',max_possible)
        if threshold_on and max_possible < threshold:
            # Cannot reach the threshold no matter what remains
            return ProgressInfo(loc,sec_safety_so_far,probs,expected_clears,False)

    return ProgressInfo(loc,sec_safety_so_far,probs,expected_clears,True)



        

from game_state_manager import GSM
import probability as prob
import copy
import sprites
from settings import *
from collections import defaultdict

def find_loc_with_best_sec_safety_over_locs(board,locs):
    if len(locs) == 0:
        return None
    threshold = -1
    best_loc = None
    for loc in locs:
        # print(f'loc: {loc}')
        sec_safety_so_far, _, finished = calc_sec_safety_at_loc(board,loc,threshold)
        if finished and sec_safety_so_far > threshold:
            threshold = sec_safety_so_far
            best_loc = loc
        # if finished:
        #     print(f'ss: {sec_safety_so_far}')
        # print(f'finished: {finished}')


    # print(f'best: {best_loc}')
    return best_loc

def calc_sec_safety_at_loc(board,loc,threshold):
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
    for i in range(min_flags, max_flags + 1):
        count, best_prob = board.get_sol_counts_at_loc_for_val(loc, i)
        prob = count / num_sols
        val = 1 - best_prob
        probs[i] = (prob, val)

        sec_safety_so_far += prob * val
        weight_so_far += prob

        # Check whether it's still possible to reach the threshold
        remaining_weight = 1.0-prob_mine - weight_so_far
        max_possible = sec_safety_so_far + remaining_weight  # assume val=1 for remaining
        # print(f'max possible at val {i}:',max_possible)
        if max_possible < threshold:
            # Cannot reach the threshold no matter what remains
            return sec_safety_so_far, probs, False

    return sec_safety_so_far, probs, True


        

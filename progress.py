from game_state_manager import GSM
import probability_test as prob

def calc_secondary_safety_at_loc(board,loc):
    regions = board.regions_set
    region = next(r for r in regions if loc in r.locs)
    groups = region.groups
    sols = region.group_sols
    counts = region.group_counts
    sols_with_counts = zip(sols,counts)
from game_state_manager import GSM
import probability_test as prob

def calc_force_at_loc(board,loc):
    regions = board.regions_list
    region = [r for r in regions if loc in r.locs]
    if len(region) == 0:
        return -1
    region=region[0]
    groups = region.groups[:]
    sols = region.group_sols
    group_index = prob.find_matching_indices(groups,[loc])[0]
    group_with_loc = groups[group_index]
    valid_sols = [sol for sol in sols if sol[group_index] < len(group_with_loc)]
    if len(group_with_loc) == 1:
        del groups[group_index]
        valid_sols = [sol[:group_index] + sol[group_index+1:] for sol in valid_sols]
    else:
        groups[group_index]


    print(groups)
    print(region.groups)
    probs_per_group, _ = prob.calc_probs_from_grouped_sols(groups,valid_sols)

    probs_per_group = [prob/len(groups[i]) for i, prob in enumerate(probs_per_group)]

    #force = (1-min(probs_per_group)) * board.tiles[loc[0]][loc[1]].prob_mine_local
    force = (1-min(probs_per_group))
    return force
# find regions which have the same number of mines across all possibilities, 
# and which are next to no unrevealed tiles
def is_region_info_complete(board,region):
    if len(region.ps) == 0:
        return False
    # check if all sols have same # of mines
    all_totals_match = True
    ps = region.ps
    expected_total = ps[0].total_mines
    for p in ps: 
        if p.total_mines != expected_total:
            all_totals_match = False
            break
    if not all_totals_match:
        return False

    # check if region is contained (none of its tiles are adjecent to unrevealed info outside of the region)
    contained = True
    for loc in region.locs:
        for neighbor in board.get_neighbor_tiles(loc):
            if neighbor.is_unknown() and neighbor.loc not in region.locs:
                contained = False
                break
        if not contained:
            break
    if contained:
        return True
    return False

def are_neighbors(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1

def is_two_tile_ff_in_region(board,region):
    ff_groups = []
    # a loc has ff influence if that loc being a mine would create a two-tile 50/50
    # give slight preference to these tiles, because if you die to them, you would necessarily have had
    # to also win a 50/50 had you survived by doing another move
    ff_influence_locs = []
    for i in range(len(region.groups)):
        group = region.groups[i]
        if len(group) == 2:

            group_index = region.first_group_index + i
            is_ff = all(p.mines_per_group[group_index] == 1 for p in region.ps)
            if not is_ff:
                continue
            loc0 = group[0]
            loc1 = group[1]
            loc0_neighbors = board.get_neighbor_tiles(loc0)
            unknown_loc0_neighbor_locs = set(n.loc for n in loc0_neighbors if n.is_unknown())
            loc1_neighbors = board.get_neighbor_tiles(loc1)
            unknown_loc1_neighbor_locs = set(n.loc for n in loc1_neighbors if n.is_unknown())

            if loc0 in unknown_loc1_neighbor_locs:
                unknown_loc0_neighbor_locs.add(loc0)
                unknown_loc1_neighbor_locs.add(loc1)
            diff_elems = unknown_loc0_neighbor_locs ^ unknown_loc1_neighbor_locs
            is_ff = (len(diff_elems) == 0)
            if is_ff:
                ff_groups.append(group)
            else:
                is_at_risk_of_ff = (len(diff_elems) == 1)
                if is_at_risk_of_ff:
                    ff_influence_locs.append(next(iter(diff_elems)))


            
    return ff_groups,ff_influence_locs



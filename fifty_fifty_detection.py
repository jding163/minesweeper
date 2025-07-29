
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

    # check if region is isolated
    iso = True
    for loc in region.locs:
        for neighbor in board.get_neighbor_tiles(loc):
            if neighbor.is_unknown() and neighbor.loc not in region.locs:
                iso = False
                break
        if not iso:
            break
    if iso:
        return True
    return False

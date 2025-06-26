from game_state_manager import GSM
from collections import Counter
import copy


#board = None

# freqs is a list of dicts
def convolve_freqs(freqs):
    if len(freqs) == 0:
        return {}
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
def calc_prob_of_opening_at_loc(board,loc):    
    cc_keys = board.ccs_dict.keys()
    relevant_ccs = {}
    
    curr_tile = board.tiles[loc[0]][loc[1]]
    if curr_tile.is_revealed()  or curr_tile.is_flagged():
        return
    

    tiles_to_check = board.get_neighbor_tiles(loc)
    #t = [tile.loc for tile in tiles_to_check]
    # if (loc == (0,0)):
    #     print(t)

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
    # print(frontier_tile_locs)
    # print(num_nonfrontier_tiles)
    if len(board.mines) == 0 or len(board.ccs_freqs) == 0:
        curr_tile.prob_opening = prob_safe_frontier * prob_safe_nonfrontier
        return curr_tile.prob_opening

    mines_left = len(board.mines) - board.flag_count



    sol_freqs = convolve_freqs(board.ccs_freqs)
    max_mines_in_frontier = max(sol_freqs)
    if mines_left - max_mines_in_frontier - len(board.nonfrontier_tiles) + num_nonfrontier_tiles > 0:
        prob_safe_nonfrontier = 0
        prob_safe_frontier = 0
    

    else:
        for key in cc_keys:
            # print('key')
            # print(key)
            # print('value')
            # print(board.ccs_dict[key])
            matching_locs = [loc for loc in key if loc in frontier_tile_locs]
            if matching_locs:
                relevant_ccs[key] = matching_locs

        for cc, locs in relevant_ccs.items():
            sols = board.ccs_dict[cc]
            total = len(sols)

            if total == 0:
                print('ERROR in calc_prob_of_opening()')
                return

            indices = [cc.index(l) for l in locs]
            # print('______')
            # print(loc)
            # print(locs)
            # print(cc)
            # print(len(cc))
            # print(indices)
            # print(sols)
            # print(len(sols[0]))

            valid_count = sum(all(sol[i] == 0 for i in indices) for sol in sols)

            prob_safe_frontier *= valid_count / total
    curr_tile.prob_opening = prob_safe_frontier * prob_safe_nonfrontier
    return curr_tile.prob_opening

def calc_prob_of_opening_for_board(board):
    for x in range(GSM.rows):
        for y in range(GSM.cols):
            tile = board.tiles[x][y]
            if not tile.is_revealed() and not tile.is_flagged():
                calc_prob_of_opening_at_loc(board,(x,y))
                


def update_nonfrontier_tile_probs(board):
    #determine probs for non-border tiles
    if len(board.nonfrontier_tiles) > 0:
        sol_freqs = convolve_freqs(board.ccs_freqs)
        if len(sol_freqs) == 0:
            for x,y in board.nonfrontier_tiles:
                prob_mine_local = (GSM.mine_count - board.flag_count)/len(board.nonfrontier_tiles)
                board.tiles[x][y].prob_mine_local = prob_mine_local
                #board.tiles[x][y].prob_mine_local = GSM.mine_count/(GSM.rows*GSM.cols)
        else:
            num_sols_total = sum(sol_freqs.values())
            prob_dist = {mc: num_sols_for_mc / num_sols_total for mc, num_sols_for_mc in sol_freqs.items()}
            mines_left = len(board.mines) - board.flag_count
            prob_for_nonfrontier_tiles = calc_prob_for_nonfrontier_tiles(prob_dist,mines_left,len(board.nonfrontier_tiles))
            for x,y in board.nonfrontier_tiles:
                board.tiles[x][y].prob_mine_local = prob_for_nonfrontier_tiles
        return sol_freqs
    return None

class Strategy:

    def __str__(self):
        raise NotImplementedError

    def find_move(self,board):
        raise NotImplementedError

# looks for tile with lowest prob of being a mine; as a tiebreaker, prefers corners, then edges, then everything else
class SafestTile(Strategy):

    def __str__(self):
        return 'SafestTile'
    def find_move(self,board):
        #update_nonfrontier_tile_probs(board)

        min_prob = 1
        min_x=0
        min_y=0
        priority = 0

        for x in range(GSM.rows):
            for y in range(GSM.cols):
                tile = board.tiles[x][y]
                if not tile.is_revealed() and not tile.is_flagged():
                    # print('{},{}'.format(x,y))
                    if tile.prob_mine_local < min_prob:
                        min_prob = tile.prob_mine_local
                        min_x = x
                        min_y = y
                        priority = tile.pos_type
                    elif tile.prob_mine_local == min_prob:
                        if tile.pos_type > priority:
                            min_x = x
                            min_y = y
                            priority = tile.pos_type
        return min_x,min_y


# looks for tile with lowest prob of being a mine; as tiebreaker, looks for tile that is most likely to be an opening
class SafestTileAndLikeliestOpening(Strategy):
    def __str__(self):
        return 'SafestTileAndLikeliestOpening'
    def find_move(self,board):
        min_prob = 1
        min_x=0
        min_y=0
        prob_opening = 0
        priority = 0
        calc_prob_of_opening_for_board(board)
        for x in range(GSM.rows):
            for y in range(GSM.cols):
                tile = board.tiles[x][y]
                if not tile.is_revealed() and not tile.is_flagged():
                    # print('{},{}'.format(x,y))
                    if tile.prob_mine_local < min_prob:
                        min_prob = tile.prob_mine_local
                        min_x = x
                        min_y = y
                        priority = tile.pos_type
                        prob_opening = tile.prob_opening

                    elif tile.prob_mine_local == min_prob:
                        if tile.pos_type > priority:
                            min_x = x
                            min_y = y
                            priority = tile.pos_type
                            prob_opening = tile.prob_opening

                        elif tile.pos_type == priority:
                            comp_prob_opening = tile.prob_opening
                            if comp_prob_opening > prob_opening:
                                min_x = x
                                min_y = y
                                prob_opening = comp_prob_opening

                    # if tile.prob_mine_local < min_prob:
                    #     min_prob = tile.prob_mine_local
                    #     min_x = x
                    #     min_y = y
                    #     prob_opening = tile.prob_opening
                    #     #print(prob_opening)
                    # elif tile.prob_mine_local == min_prob:
                    #     comp_prob_opening = tile.prob_opening
                    #     #print(comp_prob_opening)
                    #     if comp_prob_opening > prob_opening:
                    #         min_x = x
                    #         min_y = y
                    #         prob_opening = comp_prob_opening
        return min_x,min_y

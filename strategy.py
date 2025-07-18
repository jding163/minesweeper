import probability as prob
from game_state_manager import GSM
import progress as prog
import time
from line_profiler import profile

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
        min_x=-1
        min_y=-1
        unrevealed_tile_locs = []
        for region in board.regions_list:
            for loc in region.locs:
                unrevealed_tile_locs.append(loc)
        for loc in unrevealed_tile_locs:
            x,y = loc
            tile = board.tiles[x][y]
            if tile.prob_mine_local < min_prob:
                min_prob = tile.prob_mine_local
                min_x = x
                min_y = y
        if len(board.nonfrontier_tiles) == 0:
            return min_x,min_y

        candidates = []
        # threshold = 1-((1-min_prob)*0.9)
        # print(threshold)
        for loc in unrevealed_tile_locs:
            x,y = loc
            tile = board.tiles[x][y]
            if tile.prob_mine_local <= min_prob:
                candidates.append(tile)

        x_nf,y_nf = board.nonfrontier_tiles[0]
        nonfrontier_tile = board.tiles[x_nf][y_nf]
        nonfrontier_tile_prob = nonfrontier_tile.prob_mine_local
        if nonfrontier_tile_prob <= min_prob:
            for x,y in board.nonfrontier_tiles:
                tile = board.tiles[x][y]
                candidates.append(tile)
        if len(candidates) == 1:
            return candidates[0].loc
        progress_dists = {}
        filtered = []
        for c in candidates:
            if c.num_adj_flags == 0:
                filtered.append(c)

        if len(filtered) == 1:
            return filtered[0].loc
        if len(filtered) == 0:
            return candidates[0].loc
        for c in filtered:
            if board.is_loc_candidate_for_analysis(c.loc):

                #print('candidate:',c.loc)
            # progress_dists[c.loc] = prob.calc_prob_dist_for_loc(board,c.loc)
            # print(progress_dists)
                progress_dists[c.loc] = prob.calc_prob_opening_for_loc(board,c.loc)
        best = None
        prob_opening_best = -1
        for k,v in progress_dists.items():
            #prob_opening = v[0]
            prob_opening=v
            if prob_opening > prob_opening_best:
                prob_opening_best = prob_opening
                best = k
        return best
    

class SecSafety(Strategy):
    def __str__(self):
        return 'SecSafety'
    def find_move(self, board):
        min_prob = 1
        min_x = -1
        min_y = -1

        unrevealed_tile_locs = []
        for region in board.regions_list:
            for loc in region.locs:
                unrevealed_tile_locs.append(loc)
        for loc in unrevealed_tile_locs:
            x,y = loc
            tile = board.tiles[x][y]
            if tile.prob_mine_local < min_prob:
                min_prob = tile.prob_mine_local
                min_x = x
                min_y = y
        if len(board.nonfrontier_tiles) == 0:
            return min_x,min_y
        
        candidates = []
        eps = (1-min_prob)/12
        #eps=0
        for loc in unrevealed_tile_locs:
            x,y = loc
            tile = board.tiles[x][y]
            if tile.prob_mine_local <= min_prob + eps:
                candidates.append(tile)

        x_nf,y_nf = board.nonfrontier_tiles[0]
        nonfrontier_tile = board.tiles[x_nf][y_nf]
        nonfrontier_tile_prob = nonfrontier_tile.prob_mine_local
        if nonfrontier_tile_prob <= min_prob + eps:
            for x,y in board.nonfrontier_tiles:
                if board.is_loc_candidate_for_analysis((x,y)):
                    tile = board.tiles[x][y]
                    candidates.append(tile)
        if len(candidates) == 1:
            return candidates[0].loc

        candidate_locs = [c.loc for c in candidates]
        best_loc = prog.find_loc_with_best_progress_over_locs(board,candidate_locs)
        return best_loc
 
            

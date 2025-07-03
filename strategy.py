import probability_test as prob
from game_state_manager import GSM
import progress as prog

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
        for x in range(GSM.rows):
            for y in range(GSM.cols):
                tile = board.tiles[x][y]
                if not tile.is_revealed() and not tile.is_flagged():
                    # print('{},{}'.format(x,y))
                    if tile.prob_mine_local < min_prob:
                        min_prob = tile.prob_mine_local

        candidates = []
        eps = 0.00
        for x in range(GSM.rows):
            for y in range(GSM.cols):
                tile = board.tiles[x][y]
                if not tile.is_revealed() and not tile.is_flagged():
                    if tile.prob_mine_local <= min_prob + eps:
                        candidates.append(tile)
        if len(candidates) == 1:
            return candidates[0].loc
        progress_dists = {}
        filtered = []
        for c in candidates:
            if c.num_adj_flags == 0:
                filtered.append(c)
        if len(progress_dists) == 0:
            return candidates[0].loc
        if len(filtered) == 1:
            return filtered[0].loc
        for c in filtered:
            progress_dists[c.loc] = prob.calc_prob_dist_for_val(board,c.loc,max_val=1)

        
        best = None
        prob_opening_best = -1
        for k,v in progress_dists.items():
            prob_opening = v[0]
            if prob_opening > prob_opening_best:
                prob_opening_best = prob_opening
                best = k
        return best
    

class SafestTileAndForce(Strategy):
    count = 0
    def __str__(self):
        return 'SafestTileAndForce'
    def find_move(self, board):
        min_prob = 1
        min_x=0
        min_y=0
        prob_opening = 0
        priority = 0
        force = 0
        prob.calc_prob_of_opening_for_board(board)
        prog.calc_force_for_board(board)
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
                        force = tile.force

                    elif tile.prob_mine_local == min_prob:
                        if tile.pos_type > priority:
                            min_x = x
                            min_y = y
                            priority = tile.pos_type
                            prob_opening = tile.prob_opening
                            force = tile.force

                        elif tile.pos_type == priority:
                            comp_prob_opening = tile.prob_opening
                            if comp_prob_opening > prob_opening:
                                min_x = x
                                min_y = y
                                prob_opening = comp_prob_opening
                                force = tile.force
                            elif comp_prob_opening == tile.prob_opening:  

                                comp_force = tile.force

                                if comp_force > force:
                                    min_x = x
                                    min_y = y
                                    force = tile.force
        return min_x, min_y
        # min_prob = 1
        # for x in range(GSM.rows):
        #     for y in range(GSM.cols):
        #         tile = board.tiles[x][y]
        #         if not tile.is_revealed() and not tile.is_flagged():
        #             if tile.prob_mine_local < min_prob:
        #                 min_prob = tile.prob_mine_local
        # candidates = []
        # for x in range(GSM.rows):
        #     for y in range(GSM.cols):
        #             tile = board.tiles[x][y] 
        #             if not tile.is_revealed() and not tile.is_flagged():
        #                 if tile.prob_mine_local == min_prob:
        #                     candidates.append(tile)
        # best_score = -999999
        # best_candidate = None
        # for candidate in candidates:
        #     loc = candidate.loc
        #     neighbors = board.get_neighbor_tiles(loc)
        #     num_revealed_neighbors=0
        #     num_unrevealed_neighbors_in_frontier=0
        #     num_unrevealed_neighbors_not_in_frontier=0
        #     for neighbor in neighbors:
        #         if not neighbor.is_unknown():
        #             num_revealed_neighbors += 1
        #         else:
        #             if neighbor.loc in board.nonfrontier_tiles:
        #                 num_unrevealed_neighbors_not_in_frontier += 1
        #             else:
        #                 num_unrevealed_neighbors_in_frontier+=1
        #     score = 0.5*num_revealed_neighbors + 0.5 * num_unrevealed_neighbors_in_frontier + num_unrevealed_neighbors_not_in_frontier
        #     score /= math.pow(len(neighbors),0.2)
        #     if score > best_score:
        #         best_candidate = candidate
        # return best_candidate.loc
            

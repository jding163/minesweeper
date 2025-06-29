import probability_test as prob
from game_state_manager import GSM

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
        prob.calc_prob_of_opening_for_board(board)
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
        return min_x,min_y

class CombinedSafetyAndOpeningScore(Strategy):
    def __str__(self):
        return 'CombinedSafetyAndOpeningScore'
    def find_move(self, board):
        prob.calc_prob_of_opening_for_board(board)
        max_threshold = 0.1
        candidates = []
        while len(candidates) == 0:
            for x in range(GSM.rows):
                for y in range(GSM.cols):
                    tile = board.tiles[x][y]

                    if tile.is_unknown():
                        if tile.prob_mine_local < max_threshold:
                            candidates.append(tile)
            max_threshold += 0.05
        best_candidate = candidates[0]
        for candidate in candidates:
            if candidate.prob_opening > best_candidate.prob_opening:
                best_candidate = candidate
        return best_candidate.loc
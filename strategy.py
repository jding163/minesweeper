import probability as prob
from game_state_manager import GSM
import progress as prog
import time
from line_profiler import profile
import solver
import fifty_fifty_detection as ffd
import logging

def get_priority(board,loc):
    x,y=loc
    on_h_edge = 1 if x == 0 or x == board.rows - 1 else 0
    on_v_edge = 1 if y == 0 or x == board.cols - 1 else 0
    return on_h_edge + on_v_edge

class Strategy:

    def __str__(self):
        raise NotImplementedError

    def find_move(self,board):
        raise NotImplementedError
    def find_move_from_locs(self,board,locs):
        raise NotImplementedError

# looks for tile with lowest prob of being a mine; as a tiebreaker, prefers corners, then edges, then everything else
class SafestTile(Strategy):

    def __str__(self):
        return 'SafestTile'
    def find_move(self,board):
        #update_nonfrontier_tile_probs(board)

        min_prob = 1
        min_x=-1
        min_y=-1
        best_priority = -1

        unrevealed_tile_locs = []
        for region in board.regions_list:
            for loc in region.locs:
                unrevealed_tile_locs.append(loc)
        for x,y in unrevealed_tile_locs:
            prob_mine = board.mine_probs[x][y]
            if prob_mine < min_prob:
                min_prob = prob_mine
                min_x = x
                min_y = y
                best_priority = get_priority(board,(x,y))
            elif prob_mine == min_prob:
                priority = get_priority(board,(x,y))
                if priority > best_priority:
                    min_x = x
                    min_y = y
                    best_priority = priority
        if len(board.nonfrontier_tiles) > 0:
            x_nf,y_nf = board.nonfrontier_tiles[0]
            nonfrontier_tile_prob = board.mine_probs[x_nf][y_nf]
            if nonfrontier_tile_prob <= min_prob:

                for x,y in board.nonfrontier_tiles:
                    priority = get_priority(board,(x,y))

                    if priority > best_priority:
                        min_x = x
                        min_y = y
                        best_priority = priority
        return min_x,min_y
    
    def find_move_from_locs(self,board,locs):
        min_prob = 1
        min_x=-1
        min_y=-1
        best_priority = -1

        for x,y in locs:
            prob_mine = board.mine_probs[x][y]
            if prob_mine < min_prob:
                min_prob = prob_mine
                min_x = x
                min_y = y
                best_priority = get_priority(board,(x,y))
            elif prob_mine == min_prob:
                priority = get_priority(board,(x,y))
                if priority > best_priority:
                    min_x = x
                    min_y = y
                    best_priority = priority
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
            prob_mine = board.mine_probs[x][y]

            if prob_mine < min_prob:
                min_prob = prob_mine
                min_x = x
                min_y = y

        if len(board.nonfrontier_tiles) == 0:
            return min_x,min_y

        candidates = []
        # threshold = 1-((1-min_prob)*0.9)
        # print(threshold)
        for loc in unrevealed_tile_locs:
            x,y = loc
            prob_mine = board.mine_probs[x][y]
            if prob_mine <= min_prob:
                candidates.append(loc)
  

        x_nf,y_nf = board.nonfrontier_tiles[0]
        nonfrontier_tile_prob = board.mine_probs[x_nf][y_nf]
        eps = 0.000001

        if nonfrontier_tile_prob <= min_prob + eps:
            for loc in board.nonfrontier_tiles:

                candidates.append(loc)

        if len(candidates) == 1:
            return candidates[0]
        candidates = sorted(candidates, key=lambda c: (c[0], c[1]))        
        filtered = []
        for c in candidates:
            if board.adj_flag_tracker[c[0]][c[1]] == 0:
                filtered.append(c)

        if len(filtered) == 1:
            return filtered[0]
        if len(filtered) == 0:
            return candidates[0]
        progress_dists = {}

        for c in filtered:
            if board.is_loc_candidate_for_analysis(c):
                progress_dists[c] = prob.calc_prob_opening_for_loc(board,c)
        best = None
        prob_opening_best = -1
        for k,v in progress_dists.items():
            prob_opening=v
            if prob_opening > prob_opening_best:
                prob_opening_best = prob_opening
                best = k
        return best
    def find_move_from_locs(self,board,locs):
        min_prob = 1
        min_x=-1
        min_y=-1

        for loc in locs:
            x,y = loc
            prob_mine = board.mine_probs[x][y]
            if prob_mine < min_prob:
                min_prob = prob_mine
                min_x = x
                min_y = y

        if len(board.nonfrontier_tiles) == 0:
            return min_x,min_y

        candidates = []
        # threshold = 1-((1-min_prob)*0.9)
        # print(threshold)
        for loc in locs:
            x,y = loc
            prob_mine = board.mine_probs[x][y]
            if prob_mine <= min_prob:
                candidates.append(loc)
  
        if len(candidates) == 1:
            return candidates[0]
        candidates = sorted(candidates, key=lambda c: (c[0], c[1]))        
        filtered = []
        for c in candidates:
            if board.adj_flag_tracker[c[0]][c[1]] == 0:
                filtered.append(c)

        if len(filtered) == 1:
            return filtered[0]
        if len(filtered) == 0:
            return candidates[0]
        progress_dists = {}

        for c in filtered:
            if board.is_loc_candidate_for_analysis(c):
                progress_dists[c] = prob.calc_prob_opening_for_loc(board,c)
        best = None
        prob_opening_best = -1
        for k,v in progress_dists.items():
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

        for x,y in unrevealed_tile_locs:
            prob_mine = board.mine_probs[x][y]
            if prob_mine < min_prob:
                min_prob = prob_mine
                min_x = x
                min_y = y
        if len(board.nonfrontier_tiles) == 0:
            return min_x,min_y
        
        candidates = set()
        eps = (1-min_prob)/12
        eps_ffi = 2*eps
        eps_threshold = min_prob+eps
        for x,y in unrevealed_tile_locs:
            prob_mine = board.mine_probs[x][y]


            if prob_mine <= eps_threshold:
                candidates.add((x,y))
        x_nf,y_nf = board.nonfrontier_tiles[0]
        nonfrontier_tile_prob = board.mine_probs[x_nf][y_nf]
        if nonfrontier_tile_prob <= eps_threshold:
            for loc in board.nonfrontier_tiles:
                if board.is_loc_candidate_for_analysis(loc):
                    candidates.add(loc)
        ffi_threshold = min_prob+eps_ffi
        for x,y in board.ff_influence_locs:
            prob_mine = board.mine_probs[x][y]
            if prob_mine <= ffi_threshold:
                candidates.add((x,y))



        candidates=list(candidates)
        if len(candidates) == 1:
            return candidates[0]
        # for c in candidates:
        #     print(c.loc)
        #     print(c.prob_mine_local)
        candidates = sorted(candidates,key=lambda k: [k[0], k[1]])
        # if not board.collected and len(board.ff_influence_locs) > 0:
        #     for l in board.ff_influence_locs:
        #         print(l)
        #     board.collected=True
        best_loc = prog.find_loc_with_best_progress_over_locs(board,candidates)
        # if not board.collected:
        #     best_loc1 = prog.find_loc_with_best_progress_over_locs(board,candidate_locs,ff_influence_weight=1)
        #     if best_loc != best_loc1:
        #         board.collected=True
        #         print(best_loc)
        #         print(best_loc1)
        logging.info(best_loc)
        return best_loc

    def find_move_from_locs(self, board,locs):
        min_prob = 1
        min_x = -1
        min_y = -1


        for x,y in locs:
            prob_mine = board.mine_probs[x][y]
            if prob_mine < min_prob:
                min_prob = prob_mine
                min_x = x
                min_y = y
        if len(board.nonfrontier_tiles) == 0:
            return min_x,min_y
        
        candidates = []
        eps = (1-min_prob)/12
        #eps=0
        for loc in locs:
            x,y = loc
            prob_mine = board.mine_probs[x][y]
            # if loc in board.ff_influence_locs:
            #     score /= 1.02
            if prob_mine <= min_prob + eps:
                candidates.append(loc)

        if len(candidates) == 1:
            return candidates[0]

        candidates = sorted(candidates,key=lambda k: [k[0], k[1]])
        best_loc = prog.find_loc_with_best_progress_over_locs(board,candidates)
        # best_loc = prog.find_loc_with_best_progress_over_locs(board,candidate_locs)


        return best_loc
 
 
            

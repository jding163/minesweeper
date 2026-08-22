
import pygame
import os
from settings import *
import random
from game_state_manager import GSM
import sys
from line_profiler import profile
import numpy as np

# UNKNOWN = 0
# NUMBER = 1
# OPENING = 2
# MINE = 3
GREEN_TRANSP = (0, 255, 0, 90)
ORANGE_TRANSP = (255, 165, 0, 90)
RED_TRANSP = (255, 0, 0, 80)

tile_number_paths = []
for i in range(1, 9):
    tile_number_paths.append(os.path.join("assets", f"Tile{i}.png"))
tile_unknown_path = os.path.join("assets", f"TileUnknown.png")
tile_mine_path = os.path.join("assets", f"TileMine.png")
tile_opening_path = os.path.join("assets", f"TileEmpty.png")
tile_exploded_path = os.path.join("assets", f"TileExploded.png")
tile_flag_path = os.path.join("assets", f"TileFlag.png")
tile_not_mine_path = os.path.join("assets", f"TileNotMine.png")

tile_numbers = []
for i in range(1, 9):
    tile_numbers.append(pygame.transform.scale(pygame.image.load(tile_number_paths[i-1]), (TILESIZE, TILESIZE)))
tile_unknown = pygame.transform.scale(pygame.image.load(tile_unknown_path), (TILESIZE, TILESIZE))
tile_mine  = pygame.transform.scale(pygame.image.load(tile_mine_path), (TILESIZE, TILESIZE))
tile_opening = pygame.transform.scale(pygame.image.load(tile_opening_path), (TILESIZE, TILESIZE))
tile_exploded = pygame.transform.scale(pygame.image.load(tile_exploded_path), (TILESIZE, TILESIZE))
tile_flag = pygame.transform.scale(pygame.image.load(tile_flag_path), (TILESIZE, TILESIZE))
tile_not_mine = pygame.transform.scale(pygame.image.load(tile_not_mine_path), (TILESIZE, TILESIZE))
image_dict = {}
for i in range(len(tile_number_paths)):
    image_dict[tile_number_paths[i]] = tile_numbers[i]
image_dict[tile_unknown_path] = tile_unknown
image_dict[tile_mine_path] = tile_mine
image_dict[tile_opening_path] = tile_opening
image_dict[tile_exploded_path] = tile_exploded
image_dict[tile_flag_path] = tile_flag
image_dict[tile_not_mine_path] = tile_not_mine



def get_neighbors(loc):
    neighbors = [(loc[0]-1,loc[1]-1),(loc[0]-1,loc[1]),(loc[0]-1,loc[1]+1),
                (loc[0],loc[1]-1),(loc[0],loc[1]+1),
                (loc[0]+1,loc[1]-1),(loc[0]+1,loc[1]),(loc[0]+1,loc[1]+1)]
    valid_neighbors = []
    for neighbor in neighbors:
        if 0<=neighbor[0] < GSM.rows and 0<=neighbor[1]< GSM.cols:
            valid_neighbors.append(neighbor)
    return valid_neighbors

class TileUI:
    font = None
    death_click=None

    def __init__(self, x, y,num):
        self.x = x * TILESIZE
        self.y = y * TILESIZE
        self.row = x
        self.col = y
        self.loc = (x,y)
        self.num = num
        self.state = 0
        self.num_adj_flags = 0
        self.mine_prob=0
        self.opening_prob=0
    def draw(self,display,display_probs):
        is_mine = (self.num ==9)
        is_opening = (self.num == 0)
        state = self.state
        loc = (self.x,self.y)
        
        if state == UNKNOWN:
            display.blit(image_dict[tile_unknown_path],loc)

            if display_probs == 1:
                if self.mine_prob >= 0:
                    prob_text = TileUI.font.render(f"{self.mine_prob * 100:.1f}", True, (0, 0, 0))  # Black text
                    text_rect = prob_text.get_rect(center=(self.x + TILESIZE // 2, self.y + TILESIZE // 2))
                    display.blit(prob_text, text_rect)

            # for now, inset does nothing, but I may make SUGGESTIONSIZE smaller later
            inset = (TILESIZE - SUGGESTIONSIZE) // 2
            suggest_pos = (self.x + inset, self.y + inset)
            suggest_rect = pygame.Rect(suggest_pos, (SUGGESTIONSIZE, SUGGESTIONSIZE))
            if TileUI.death_click == None:
                if self.loc in Board.suggestion_safe:
                    self.draw_suggestion(display, suggest_rect, suggest_pos, GREEN_TRANSP)
                elif self.loc == Board.suggestion_guess:
                    self.draw_suggestion(display, suggest_rect, suggest_pos, ORANGE_TRANSP)
                elif self.loc in Board.suggestion_mine:
                    self.draw_suggestion(display, suggest_rect, suggest_pos, RED_TRANSP)

        elif state == REVEALED:
            if is_mine:
                if self.loc == TileUI.death_click:
                    display.blit(image_dict[tile_exploded_path],loc)
                else:
                    display.blit(image_dict[tile_mine_path],loc)
            elif is_opening:
                display.blit(image_dict[tile_opening_path],loc)
            else:
               display.blit(image_dict[tile_number_paths[self.num - 1]],loc)   
        else: #flagged
            if not GSM.game_over() or is_mine:
                display.blit(image_dict[tile_flag_path],loc)
            else:
                display.blit(image_dict[tile_not_mine_path],loc)

        # # always display coords for every cell
        # if display_probs == 3:
        #     loc_text = TileUI.font.render(f"{self.loc}", True, (0, 0, 0))  # Black text
        #     text_rect = loc_text.get_rect(center=(self.x + TILESIZE // 2, self.y + TILESIZE // 2))
        #     display.blit(loc_text, text_rect)

    def draw_suggestion(self, display, rect, pos, color):
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, color, surf.get_rect())
        display.blit(surf, pos)


class BoardUI():
    display_probs = 0 #0,1,2

    def __init__(self, board):
        self.tiles = [[TileUI(r,c,board.num_mine_tracker[r,c]) 
                       for c in range(board.cols)] for r in range(board.rows)]
        self.board=board
        self.display = pygame.Surface((GSM.rows * TILESIZE, GSM.cols * TILESIZE))

    def sync(self):
        for r in range(self.board.rows):
            for c in range(self.board.cols):
                tile = self.tiles[r][c]
                tile.state = self.board.tile_state_tracker[r,c]
                tile.num_adj_flags = self.board.adj_flag_tracker[r,c]
                tile.num = self.board.num_mine_tracker[r,c]
                tile.mine_prob=self.board.mine_probs[r,c]
                tile.opening_prob=self.board.opening_probs[r,c]
        TileUI.death_click = self.board.death_click
    def draw(self, screen, offset=(0, 0)):
        self.sync()
        for row in self.tiles:
            for tile in row:
                tile.draw(self.display, BoardUI.display_probs)

        # Viewport is the fixed on-screen area for the board.
        viewport = pygame.Surface((BOARD_VIEWPORT_WIDTH, BOARD_VIEWPORT_HEIGHT))
        viewport.fill((255, 255, 255))
        viewport.blit(self.display, (-offset[0], -offset[1]))
        screen.blit(viewport, (LEFT_PANEL_WIDTH, HEADER_HEIGHT))

        # Optional scroll indicators for oversized boards.
        board_w = self.board.rows * TILESIZE
        board_h = self.board.cols * TILESIZE
        if board_w > BOARD_VIEWPORT_WIDTH or board_h > BOARD_VIEWPORT_HEIGHT:
            self._draw_scroll_indicators(screen, offset, board_w, board_h)

    def _draw_scroll_indicators(self, screen, offset, board_w, board_h):
        origin_x = LEFT_PANEL_WIDTH
        origin_y = HEADER_HEIGHT

        if board_w > BOARD_VIEWPORT_WIDTH:
            bar_w = BOARD_VIEWPORT_WIDTH
            thumb_w = max(20, int(BOARD_VIEWPORT_WIDTH * BOARD_VIEWPORT_WIDTH / board_w))
            max_x = board_w - BOARD_VIEWPORT_WIDTH
            thumb_x = 0 if max_x == 0 else int(offset[0] * (bar_w - thumb_w) / max_x)
            pygame.draw.rect(screen, (180, 180, 180),
                             (origin_x, origin_y + BOARD_VIEWPORT_HEIGHT - 6, bar_w, 6))
            pygame.draw.rect(screen, (100, 100, 100),
                             (origin_x + thumb_x, origin_y + BOARD_VIEWPORT_HEIGHT - 6, thumb_w, 6))

        if board_h > BOARD_VIEWPORT_HEIGHT:
            bar_h = BOARD_VIEWPORT_HEIGHT
            thumb_h = max(20, int(BOARD_VIEWPORT_HEIGHT * BOARD_VIEWPORT_HEIGHT / board_h))
            max_y = board_h - BOARD_VIEWPORT_HEIGHT
            thumb_y = 0 if max_y == 0 else int(offset[1] * (bar_h - thumb_h) / max_y)
            pygame.draw.rect(screen, (180, 180, 180),
                             (origin_x + BOARD_VIEWPORT_WIDTH - 6, origin_y, 6, bar_h))
            pygame.draw.rect(screen, (100, 100, 100),
                             (origin_x + BOARD_VIEWPORT_WIDTH - 6, origin_y + thumb_y, 6, thumb_h))

class Board:
    seed = None
    suggestion_safe = set()
    suggestion_guess = None
    suggestion_mine = set()
    def __init__(self,empty=False,dims=None,minecount=None):
        if dims is not None:
            self.dims = dims
            self.rows = dims[0]
            self.cols = dims[1]
            GSM.update_dims(dims)
        else:
            self.rows = GSM.rows
            self.cols = GSM.cols
            self.dims = (self.rows,self.cols)
        if minecount is not None:
            self.minecount = minecount
            GSM.update_minecount(minecount)
        else:
            self.minecount = 0
        if not empty:


            self.num_revealed = 0
            self.flag_count = 0
            self.mines = []
            self.first_click= (0,0)
            self.seed = None
            self.death_click = None
            self.revealed_tiles = set()
            self.unrevealed_tiles = set()

            self.unfinished_clues = set()
            self.flagged_tiles = set()
            self.cloned = False


            self.tile_neighbors = []
            for row in range(self.rows):
                self.tile_neighbors.append([])
                for col in range(self.cols):
                    neighbors = get_neighbors((row,col))
                    self.tile_neighbors[row].append(neighbors)
            self.num_mine_tracker = np.zeros((self.dims),dtype=int)
            self.tile_state_tracker = np.zeros((self.dims),dtype=int)
            self.adj_flag_tracker = np.zeros((self.dims),dtype=int)
            total_tiles = self.rows * self.cols
            mine_count_for_density = self.minecount if self.minecount > 0 else GSM.mine_count
            uniform_density = mine_count_for_density / total_tiles if total_tiles > 0 else 0.0
            self.mine_probs = np.full((self.dims), uniform_density, dtype=float)
            self.opening_probs = np.full((self.dims),-1,dtype=float)
            
            # self.mine_probs = np.zeros((self.dims))
            # self.opening_probs = np.zeros((self.dims))

    def save_board(self,filename):
        np.savez_compressed(filename,
                            num_mine_tracker=self.num_mine_tracker,
                            tile_state_tracker=self.tile_state_tracker,
                            adj_flag_tracker=self.adj_flag_tracker)

    def load_board(filename):
        data = np.load(filename)
        nmt = data['num_mine_tracker']
        board = Board(dims=nmt.shape)
        board.num_mine_tracker = nmt
        board.tile_state_tracker = data["tile_state_tracker"]
        board.adj_flag_tracker = data["adj_flag_tracker"]

        board.dims = board.num_mine_tracker.shape
        board.rows = board.dims[0]
        board.cols = board.dims[1]
        board.mine_probs = np.full((board.dims),-1,dtype=float)
        board.opening_probs = np.full((board.dims),-1,dtype=float)
        # board.mine_probs = np.zeros((board.dims))
        # board.opening_probs = np.zeros((board.dims))


        # to calculate
        # unrevealed_rows,unrevealed_cols = zip(np.where(board.tile_state_tracker == UNKNOWN))
        # board.unrevealed_tiles = set((int(r),int(c)) for r,c in zip(unrevealed_rows,unrevealed_cols))

        ur, uc = np.where(board.tile_state_tracker == UNKNOWN)
        board.unrevealed_tiles = {(int(r), int(c)) for r, c in zip(ur, uc)}

        rr, rc = np.where(board.tile_state_tracker == REVEALED)
        board.revealed_tiles = {(int(r), int(c)) for r, c in zip(rr, rc)}

        fr, fc = np.where(board.tile_state_tracker == FLAGGED)
        board.flagged_tiles = {(int(r), int(c)) for r, c in zip(fr, fc)}


        board.num_revealed = len(board.revealed_tiles)
        board.flag_count = len(board.flagged_tiles)

        mine_rows,mine_cols = np.where(board.num_mine_tracker == 9)
        board.mines = list(zip(mine_rows.tolist(), mine_cols.tolist()))
        board.minecount = len(board.mines)
        GSM.update_minecount(board.minecount)

        tile_neighbors = []
        for row in range(board.rows):
            tile_neighbors.append([])
            for col in range(board.cols):
                neighbors = get_neighbors((row,col))
                tile_neighbors[row].append(neighbors)
        board.tile_neighbors = tile_neighbors

        mask = ((board.adj_flag_tracker != board.num_mine_tracker) & (board.tile_state_tracker == REVEALED))
        board.unfinished_clues = {(int(r), int(c)) 
               for r, c in zip(*np.where(mask))}
        #default
        board.cloned=False
        board.first_click=None
        board.seed = None
        board.death_click=None
        return board
    

    # load info into freshly init board
    def clone_board(self,board,copy_num_mine_tracker=False):

        self.rows = board.rows
        self.cols = board.cols
        self.dims = (self.rows,self.cols)
        self.num_revealed = board.num_revealed
        self.flag_count = board.flag_count
        self.mines = list(board.mines)
        self.minecount = board.minecount
        self.first_click=board.first_click
        self.seed = board.seed
        self.death_click=board.death_click
        self.revealed_tiles=set(board.revealed_tiles)
        self.unrevealed_tiles=set(board.unrevealed_tiles)
        self.unfinished_clues=set(board.unfinished_clues)
        self.flagged_tiles=set(board.flagged_tiles)
        self.cloned=True

        self.tile_neighbors = board.tile_neighbors.copy()
        if copy_num_mine_tracker:
            self.num_mine_tracker = board.num_mine_tracker.copy()
        else:
            self.num_mine_tracker = np.zeros((self.dims),dtype=int)
        self.tile_state_tracker = board.tile_state_tracker.copy()
        self.adj_flag_tracker = board.adj_flag_tracker.copy()
        self.mine_probs = board.mine_probs.copy()
        self.opening_probs = board.opening_probs.copy()                
     
    def reset_suggestions():
        Board.suggestion_safe = set()
        Board.suggestion_guess = None
        Board.suggestion_mine = set()

    def default_first_click(self):
        return (0,0)

    def lookup_neighbors(self,loc): 
        return self.tile_neighbors[loc[0]][loc[1]]
    
    def toggle_flag_at_loc(self,loc):
        tile_state = self.tile_state_tracker[loc]
        if tile_state != REVEALED:
            if tile_state == UNKNOWN:
                self.tile_state_tracker[loc] = FLAGGED
                self.flag_count += 1
                neighbors = np.array(self.lookup_neighbors(loc))
                rows, cols = neighbors.T
                self.adj_flag_tracker[rows, cols] += 1
                self.flagged_tiles.add(loc)
                self.unrevealed_tiles.remove(loc)
            else: # tile is flagged
                self.tile_state_tracker[loc] = UNKNOWN
                self.flag_count -= 1
                neighbors = np.array(self.lookup_neighbors(loc))
                rows, cols = neighbors.T
                self.adj_flag_tracker[rows, cols] -= 1
                self.flagged_tiles.discard(loc)
                self.unrevealed_tiles.add(loc)

    def populate(self,first_click,custom_mines=False,seed=None,guarantee_opening=False):
        self.first_click = first_click
        self.unrevealed_tiles = [(row, col) for row in range(self.rows) for col in range(self.cols)]
        if not custom_mines:
            if seed is not None:
                random.seed(seed)
                self.seed = seed
                #print('seed: {}'.format(seed))
            else:
                genned_seed=random.randint(0,sys.maxsize)
                self.seed = genned_seed
                random.seed(genned_seed)
            if guarantee_opening:
                protected = set([first_click])
                protected.update(self.lookup_neighbors(first_click))
                available = [loc for loc in self.unrevealed_tiles if loc not in protected]                                       
                if len(available) < GSM.mine_count:                                                                              
                    raise ValueError(                                                                                            
                        f"Cannot guarantee opening: need {GSM.mine_count} mines "                                                
                        f"but only {len(available)} tiles available outside the "                                                
                        f"protected 3x3 area around {first_click}."                                                              
                    )                                                                                                            
                locs = random.sample(available, GSM.mine_count)
            else:
                locs = random.sample(self.unrevealed_tiles, GSM.mine_count+1)
                if first_click in locs:
                    locs.remove(first_click)
                else:
                    del locs[-1]
            #del locs[-1]
            self.unrevealed_tiles=set(self.unrevealed_tiles)
            self.mines = locs
        else:
            self.mines = list(custom_mines)
            GSM.mine_count = len(custom_mines)
            self.seed = None
            self.unrevealed_tiles = set(self.unrevealed_tiles)
        for loc in self.mines:
            self.update_neighbors_with_minecount(loc)
            self.num_mine_tracker[loc] = 9
        self.minecount = len(self.mines)

    def incr_num_revealed(self):
        self.num_revealed += 1

    # precondition: clicked a number tile
    def chord(self,loc):
        if self.num_mine_tracker[loc] == self.adj_flag_tracker[loc]:
            self.reveal_neighbors(loc)
            self.unfinished_clues.discard(loc)
    
    def update_neighbors_with_minecount(self,loc):
        neighbors = np.array(self.lookup_neighbors(loc))
        rows,cols = neighbors.T
        not_mines_mask = self.num_mine_tracker[rows, cols] != 9
        self.num_mine_tracker[rows[not_mines_mask], cols[not_mines_mask]] += 1

    def reveal_tile(self,loc):
        if self.tile_state_tracker[loc] != UNKNOWN:
            return
        
        self.tile_state_tracker[loc] = REVEALED
        self.unrevealed_tiles.remove(loc)

        if self.num_mine_tracker[loc] == 9:
            self.death_click = loc
            self.reveal_mines()
            GSM.set_game_state(GSM.over)
        else:
            self.num_revealed += 1
            self.revealed_tiles.add(loc)
            if self.num_mine_tracker[loc] > 0:
                self.unfinished_clues.add(loc)
        
    def reveal_tiles(self, loc):
        # Nothing to do unless the tile is currently hidden.
        if self.tile_state_tracker[loc] != UNKNOWN:
            return

        # Snapshot the unknown mask so we can bulk-update bookkeeping once
        # the flood fill is finished, instead of touching sets per tile.
        was_unknown = (self.tile_state_tracker == UNKNOWN).copy()

        # Reveal the clicked tile (handles mines / game over).
        self.reveal_tile(loc)

        # Only zero tiles trigger a flood fill.
        if self.num_mine_tracker[loc] != 0:
            return

        # Fast Python flood fill. A list stack avoids per-tile method-call
        # overhead; marking state immediately prevents duplicate visits.
        # Every neighbor of a zero is guaranteed to be a non-mine.
        tile_state = self.tile_state_tracker
        num_mine = self.num_mine_tracker
        tile_neighbors = self.tile_neighbors
        UNKNOWN_CONST = UNKNOWN

        stack = [loc]
        while stack:
            current = stack.pop()
            for nloc in tile_neighbors[current[0]][current[1]]:
                if tile_state[nloc] == UNKNOWN_CONST:
                    tile_state[nloc] = REVEALED
                    if num_mine[nloc] == 0:
                        stack.append(nloc)

        # Extract every tile that became revealed during this call.
        newly_revealed = (tile_state == REVEALED) & was_unknown
        newly_revealed[loc] = False  # loc was already counted by reveal_tile
        if not np.any(newly_revealed):
            return

        new_r, new_c = np.where(newly_revealed)
        locs = list(zip(new_r.tolist(), new_c.tolist()))
        self.unrevealed_tiles.difference_update(locs)
        self.revealed_tiles.update(locs)
        self.num_revealed += len(locs)

        # Number tiles on the border become new clues for the solver.
        number_mask = num_mine[new_r, new_c] > 0
        num_r = new_r[number_mask]
        num_c = new_c[number_mask]
        self.unfinished_clues.update(zip(num_r.tolist(), num_c.tolist()))
    def reveal_tiles_old(self,loc):
        tile_state_tracker = self.tile_state_tracker
        num_mine_tracker = self.num_mine_tracker

        if tile_state_tracker[loc] != UNKNOWN:
            return
        self.reveal_tile(loc)

        if num_mine_tracker[loc] == 0:

            tile_neighbors = self.tile_neighbors

            loc_neighbors = tile_neighbors[loc[0]][loc[1]]

            q = [nei for nei in loc_neighbors if tile_state_tracker[nei] == UNKNOWN]
            while q:
                loc_to_open = q.pop()
                self.reveal_tile(loc_to_open)
                if num_mine_tracker[loc_to_open] == 0:
                    loc_neighbors = tile_neighbors[loc_to_open[0]][loc_to_open[1]]

                    for nloc in loc_neighbors:
                        if tile_state_tracker[nloc] == UNKNOWN:
                            tile_state_tracker[nloc] = REVEALED
                            q.append(nloc)
    # precondition: an opening was clicked, current tile is already revealed
    def reveal_neighbors(self,loc):
        neighbors = self.lookup_neighbors(loc)
        for nloc in neighbors:
            self.reveal_tiles(nloc)


    def is_complete(self):
        return self.num_revealed == self.rows*self.cols - self.minecount
    
    def verify_win(self):
        mine_check = self.num_mine_tracker < 9
        not_revealed = self.tile_state_tracker != REVEALED 
        mask = mine_check & not_revealed

        return not np.any(mask)
    


    def reveal_mines(self):
        self.tile_state_tracker[(self.num_mine_tracker == 9) & (self.tile_state_tracker != FLAGGED)] = REVEALED

    def reveal_board(self):
        if not self.mines:
            self.populate((0,0))
        self.tile_state_tracker[:] = REVEALED
        self.num_revealed = self.rows*self.cols - self.minecount

            

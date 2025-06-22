
import pygame
import os
from settings import *
import random
import math
from game_state_manager import GSM
import sys
import pprint
import copy
# UNKNOWN = 0
# NUMBER = 1
# OPENING = 2
# MINE = 3

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

class Tile:
    font = None
    def __init__(self, x,y,image,type):
        self.x = x * TILESIZE
        self.y = y * TILESIZE
        self.row = x
        self.col = y
        self.loc = (self.row,self.col)
        self.image = image
        self.type = type
        self.revealed = False
        self.flagged = False
        self.num_adj_mines = 0
        self.num_adj_flags = 0
        self.prob_mine = -1
        self.prob_opening = -1

        # 0: non-edge non-corner 1: edge 2: corner
        if (self.row == 0 or self.row == GSM.rows-1) and (self.col == 0 or self.col == GSM.cols-1):
            self.pos_type = 2
        elif (self.row == 0 or self.row == GSM.rows-1) or (self.col == 0 or self.col == GSM.cols-1):
            self.pos_type = 1
        else:
            self.pos_type = 0

    def set_font(font):
        Tile.font = font 


    def get_type(self):
        return self.type

    def set_type(self,type):
        self.type = type
        if type == MINE:
            self.image = tile_mine_path
        elif type == NUMBER:
            self.image = tile_number_paths[self.num_adj_mines-1]
        elif type == OPENING:
            self.image = tile_opening_path
    
    def set_image(self,image):
        self.image = image
        
    def is_flagged(self):
        return self.flagged
    def toggle_flag(self):
        if not self.revealed:
            self.flagged = not self.flagged
            if self.flagged:
                self.set_type(MINE)
            else:
                self.set_type(UNKNOWN)

    def incr_adj_mines(self):
        self.num_adj_mines += 1
    
    def get_adj_mines(self):
        return self.num_adj_mines
    def get_adj_flags(self):
        return self.num_adj_flags

    def is_revealed(self):
        return self.revealed

    def is_unknown(self):
        return not self.is_flagged() and not self.is_revealed()

    def set_revealed(self,revealed):
        self.revealed = revealed

    def draw(self,display,display_probs):

        if not self.revealed and not self.flagged:
            display.blit(image_dict[tile_unknown_path],(self.x,self.y))
        elif self.revealed and self.flagged:
            display.blit(image_dict[tile_flag_path],(self.x,self.y))

        elif self.revealed:
            display.blit(image_dict[self.image],(self.x,self.y))
        elif self.flagged:
            if self.type is MINE:
                display.blit(image_dict[tile_flag_path],(self.x,self.y))
            else:
                display.blit(image_dict[tile_not_mine_path],(self.x,self.y))
        if display_probs == 1:
            if self.prob_mine != -1 and not self.revealed and not self.flagged:
                prob_text = Tile.font.render(f"{self.prob_mine * 100:.1f}", True, (0, 0, 0))  # Black text
                text_rect = prob_text.get_rect(center=(self.x + TILESIZE // 2, self.y + TILESIZE // 2))
                display.blit(prob_text, text_rect)
        elif display_probs == 2:
            if self.prob_mine != -1 and not self.revealed and not self.flagged:
                prob_text = Tile.font.render(f"{self.prob_opening * 100:.1f}", True, (0, 0, 0))  # Black text
                text_rect = prob_text.get_rect(center=(self.x + TILESIZE // 2, self.y + TILESIZE // 2))
                display.blit(prob_text, text_rect)
        elif display_probs == 3:
            loc_text = Tile.font.render(f"{self.loc}", True, (0, 0, 0))  # Black text
            text_rect = loc_text.get_rect(center=(self.x + TILESIZE // 2, self.y + TILESIZE // 2))
            display.blit(loc_text, text_rect)




class Board:
    seed = None
    display_probs = 0 #0,1,2
    def __init__(self):
        self.display = pygame.Surface((GSM.rows * TILESIZE, GSM.cols * TILESIZE))
        self.tiles = []
        for row in range(GSM.rows):
            self.tiles.append([])
            for col in range(GSM.cols):
                self.tiles[row].append(Tile(row,col,tile_unknown_path,UNKNOWN))
        self.num_revealed = 0
        self.flag_count = 0
        self.complete = False
        self.mines = []
        self.first_click= (0,0)
        self.seed = None
        self.death_click = None

    def reset_probs(self):
        for row in self.tiles:
            for tile in row: 
                tile.prob_mine = -1

    def get_type_at_loc(self,loc):
        return self.tiles[loc[0]][loc[1]].get_type()
    def get_neighbor_tiles(self,loc):
        neighbor_coords = get_neighbors(loc)
        neighbors = []
        for coord in neighbor_coords:
            neighbors.append(self.tiles[coord[0]][coord[1]])
        return neighbors
    
    def get_number_neighbor_tiles(self,loc):
        neighbors = self.get_neighbor_tiles(loc)
        return [neighbor for neighbor in neighbors if neighbor.is_revealed()]
    
    
    def get_unrevealed_neighbor_tiles(self,loc):
        neighbor_coords = get_neighbors(loc)
        neighbors = []
        for coord in neighbor_coords:
            tile = self.tiles[loc[0]][loc[1]]
            if not tile.is_flagged() and not tile.is_revealed():
                neighbors.append(self.tiles[coord[0]][coord[1]])
        return neighbors
    
    def toggle_flag_at_loc(self,loc):
        if not self.tiles[loc[0]][loc[1]].is_revealed():
            self.tiles[loc[0]][loc[1]].toggle_flag()
            if self.tiles[loc[0]][loc[1]].is_flagged():
                self.flag_count +=1
                neighbors = self.get_neighbor_tiles(loc)
                for n in neighbors:
                   n.num_adj_flags += 1
            else:
                self.flag_count -=1
                neighbors = self.get_neighbor_tiles(loc)
                for n in neighbors:
                    n.num_adj_flags -= 1
    def get_flag_count(self):
        return self.flag_count
    def toggle_flag_at_loc(self,x,y):
        if not self.tiles[x][y].is_revealed():
            self.tiles[x][y].toggle_flag()
            if self.tiles[x][y].is_flagged():
                self.flag_count +=1
                neighbors = self.get_neighbor_tiles((x,y))
                for n in neighbors:
                    n.num_adj_flags += 1
                    
            else:
                self.flag_count -=1
                neighbors = self.get_neighbor_tiles((x,y))
                for n in neighbors:
                    n.num_adj_flags -= 1

    def draw(self,screen):
        for row in self.tiles:
            for tile in row: 
                tile.draw(self.display,Board.display_probs)
        screen.blit(self.display, (0, HEADER_HEIGHT))
    


    def display_board(self):
        for row in self.tiles:
            print(row)


    def populate(self,first_click,custom_mines=False,seed=None):
        self.first_click = first_click
        if not custom_mines:
            possible_locs = [(row, col) for row in range(GSM.rows) for col in range(GSM.cols)]
            if seed is not None:
                #print('aaaaaa')
                random.seed(seed)
                self.seed = seed
                print('seed: {}'.format(seed))
            else:
                genned_seed=random.randint(-sys.maxsize - 1,sys.maxsize)
                self.seed = genned_seed

                random.seed(genned_seed)
                print('seed: {}'.format(genned_seed))
            locs = random.sample(possible_locs, GSM.mine_count+1)

            if first_click in locs:
                locs.remove(first_click)
            else:
                del locs[-1]
            #del locs[-1]
            self.mines = locs
        else:
            self.mines = custom_mines
            GSM.mine_count = len(custom_mines)
        for loc in self.mines:
            #self.tiles[loc[0]][loc[1]].set_type(MINE)
            self.update_neighbors_with_minecount(loc)
        GSM.set_game_state(True)

    def incr_num_revealed(self):
        self.num_revealed += 1

    # precondition: clicked a number tile
    def chord(self,loc):

        if self.tiles[loc[0]][loc[1]].get_adj_mines() == self.tiles[loc[0]][loc[1]].get_adj_flags():
            self.reveal_neighbors([loc[0],loc[1]])
    
    def update_neighbors_with_minecount(self,loc):
        neighbors = self.get_neighbor_tiles(loc)
        for neighbor in neighbors:
            neighbor.incr_adj_mines()
            

        
    def reveal_tiles(self,mx,my):
        if self.tiles[mx][my].is_revealed() or self.tiles[mx][my].is_flagged():
            return
        self.tiles[mx][my].set_revealed(True)

        if (mx,my) in self.mines:
            self.tiles[mx][my].set_type(MINE)
            self.tiles[mx][my].set_image(tile_exploded_path)
            self.death_click = (mx,my)
            self.reveal_mines()
            GSM.set_game_state(False)
        else:
            self.incr_num_revealed()
            if self.tiles[mx][my].get_adj_mines() > 0:
                self.tiles[mx][my].set_type(NUMBER)
            else:
                self.tiles[mx][my].set_type(OPENING)
                self.reveal_neighbors((mx,my))


    # precondition: an opening was clicked, current tile is already revealed
    def reveal_neighbors(self,loc):

        neighbors = self.get_neighbor_tiles(loc)
        for neighbor in neighbors:
            if neighbor.is_revealed() is False and neighbor.is_flagged() is False:
                neighbor.set_revealed(True)
                if neighbor in self.mines:
                    neighbor.set_type(MINE)
                    neighbor.set_image(tile_exploded_path)
                    self.reveal_mines()
                    #self.reveal_board()
                else:
                    self.incr_num_revealed()
                    if neighbor.get_adj_mines() == 0:
                        neighbor.set_type(OPENING)
                        self.reveal_neighbors((neighbor.row,neighbor.col))
                    else:
                        neighbor.set_type(NUMBER)



    def is_complete(self):
        return self.num_revealed == GSM.rows*GSM.cols - GSM.mine_count
    
    def verify_win(self):
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                if self.tiles[row][col].get_type() is NUMBER and not self.tiles[row][col].is_revealed():
                    return False
        return True
    


    def reveal_mines(self):
        for mine in self.mines:
            if self.tiles[mine[0]][mine[1]].get_type() is not MINE:
                self.tiles[mine[0]][mine[1]].set_type(MINE)
                self.tiles[mine[0]][mine[1]].set_revealed(True)
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                if self.tiles[row][col].is_flagged() and (row,col) not in self.mines:
                    self.tiles[row][col].set_type(UNKNOWN)

    def reveal_board(self):
        if not self.mines:
            self.populate((0,0))
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                if (row,col) in self.mines:
                    self.tiles[row][col].set_type(MINE)
                else:
                    if self.tiles[row][col].get_adj_mines() == 0:
                        self.tiles[row][col].set_type(OPENING)
                    else:
                        self.tiles[row][col].set_type(NUMBER)
                    
                self.tiles[row][col].set_revealed(True)
        self.num_revealed = GSM.rows*GSM.cols - GSM.mine_count
        GSM.set_game_state(False)

            

    def debug_revealed(self,mx,my):
        print(self.tiles[mx][my].get_type())

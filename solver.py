from sprites import *
import  copy
from collections import defaultdict
import numpy as np
from collections import Counter
import math

import time
import probability as prob


paths_explored = 0

#MINECOUNT SEED = -75

class Solver(Board):

    def __init__(self,first_click=(0,0)):
        super().__init__()
        self.first_click = first_click
        self.ccs_dict = {}
        self.ccs_freqs = []
        self.nonfrontier_tiles = []
        #self.populate(first_click)
        #self.reveal_tiles(first_click[0],first_click[1])
    
    # flags neighbors if they are known to be mines
    def flag_neighbors(self,loc):
        neighbor_mines = self.tiles[loc[0]][loc[1]].get_adj_mines()
        neighbor_unknowns = 0
        neighbors = self.get_neighbor_tiles(loc)
        for neighbor in neighbors:
            neighbor_flagged = neighbor.is_flagged()
            neighbor_revealed = neighbor.is_revealed()
            if neighbor_flagged:
                neighbor_mines -=1
            elif not neighbor_revealed:
                neighbor_unknowns += 1
        if neighbor_unknowns == neighbor_mines:
            for neighbor in neighbors:
                neighbor_revealed = neighbor.is_revealed()
                neighbor_flagged = neighbor.is_flagged()
                if not neighbor_revealed and not neighbor_flagged:
                    self.toggle_flag_at_loc(neighbor.row,neighbor.col)
    
    def flag_board(self):
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                if self.tiles[row][col].is_revealed():
                    self.flag_neighbors((row,col))
    
    def chord_board(self):
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                if self.tiles[row][col].is_revealed():
                    self.chord((row,col))

    def solve_trivial_and_open(self):
        init_mines = self.flag_count
        init_revealed = self.num_revealed
        prev_mines = init_mines
        prev_revealed = init_revealed
        self.flag_board()
        self.chord_board()
        while self.flag_count != prev_mines or self.num_revealed != prev_revealed:
            self.flag_board()
            self.chord_board()
            prev_revealed = self.num_revealed
            prev_mines = self.flag_count
        return not ((init_mines == prev_mines) and (prev_revealed == init_revealed)) # solution found or not
        
    def get_ccs(self):
        adj_sets = []
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                if self.tiles[row][col].is_revealed():
                    neighbors = self.get_neighbor_tiles((row,col))
                    adj_set = set()
                    for neighbor in neighbors:
                        if neighbor.is_unknown():
                            adj_set.add((neighbor.row,neighbor.col))
                    if len(adj_set) > 0: 
                        adj_sets.append(adj_set) 
        merged = merge_sets(adj_sets)
        return merged
                            
    def open_remaining(self):
        if self.flag_count == GSM.mine_count:
            for row in range(GSM.rows):
                for col in range(GSM.cols):
                    self.reveal_tiles(row,col)


    def inject_mine(self,loc):
        self.tiles[loc[0]][loc[1]].set_type(MINE)

    def inject_num(self,loc):
        self.tiles[loc[0]][loc[1]].set_type(NUMBER)

    def undo_inject(self,loc):
        self.tiles[loc[0]][loc[1]].set_type(UNKNOWN)

    def verify_board(self):
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                curr = self.tiles[row][col]
                if curr.is_revealed():
                    neighbors = self.get_neighbor_tiles((row,col))
                    neighbor_types = {UNKNOWN: 0, MINE: 0, NUMBER: 0, OPENING: 0}
                    for neighbor in neighbors:
                        neighbor_types[neighbor.get_type()] += 1
                    if neighbor_types[MINE] > curr.get_adj_mines() or (neighbor_types[UNKNOWN] == 0 and neighbor_types[MINE] != curr.get_adj_mines()):
                        return False
                        
        return True

    def verify_neighbors(self,locs_to_check):
        for loc in locs_to_check:
            tile = self.tiles[loc[0]][loc[1]]
            tiles_to_check = self.get_neighbor_tiles((tile.row,tile.col))
            tiles_to_check.append(tile)
            for t in tiles_to_check:
                if t.get_type() is NUMBER:
                    tile_types = {UNKNOWN: 0, MINE: 0, NUMBER: 0, OPENING: 0}
                    for t in tiles_to_check:
                        tile_types[t.get_type()] += 1
                    if tile_types[MINE] > tile.get_adj_mines() or (tile_types[UNKNOWN] == 0 and tile_types[MINE] != tile.get_adj_mines()):
                        return False
        return True
        
    def optimize_backtrack_order(self,locs):

        constraint_map = defaultdict(set)  # clue -> set of (x, y)

        # tile_neighbors: maps each tile to other tiles it shares a constraint with
        tile_neighbors = defaultdict(set)

        for loc in locs:
            neighbors = self.get_neighbor_tiles(loc)
            for neighbor in neighbors:
                if neighbor.is_revealed():
                    constraint_map[(neighbor.row,neighbor.col)].add(loc)

        # Build tile_neighbors from constraints
        for tiles in constraint_map.values():
            sorted_tiles = sorted(tiles)  # ensure deterministic pairings
            for i, a in enumerate(sorted_tiles):
                for b in sorted_tiles[i + 1:]:
                    tile_neighbors[a].add(b)
                    tile_neighbors[b].add(a)
        order = []
        if len(locs) == 1:
            order = list(locs)
        else:
            order = order_tiles_by_connectivity(tile_neighbors)
        locs_to_check = list(constraint_map.keys())
        return order, locs_to_check
    
    def check_for_existing_solution(self,locs):
        locs_t = tuple(locs)
        if locs_t in self.ccs_dict:
            return True
        return False

    def find_solutions(self,locs,locs_to_check):
        #print(locs)
        if len(locs) == 0:
            return
        if self.check_for_existing_solution(locs):
            return self.ccs_dict[tuple(locs)]
        sols = []
        loc = locs[0]

        # count flagged mines from previous play
        mine_count = 0 # includes flagged mines and unflagged mines deduced from prior calls to find_solution
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                if self.get_type_at_loc((row,col)) is MINE: 
                    mine_count += 1 

        if self.get_type_at_loc(loc) is not UNKNOWN:
            # don't increment mine count even if loc contains a flag; it was already counted 
            self.find_solutions_helper(locs,locs_to_check,sols,1,mine_count) 
        else:
            self.inject_mine(loc)
            if self.verify_neighbors(locs_to_check):
                self.find_solutions_helper(locs,locs_to_check,sols,1,mine_count+1)
            self.inject_num(loc)
            if self.verify_neighbors(locs_to_check):
                self.find_solutions_helper(locs,locs_to_check,sols,1,mine_count)
            self.undo_inject(loc)

        return sols


    def find_solutions_helper(self,locs,locs_to_check,sols,index,mine_count):
        global paths_explored
        paths_explored += 1
        if mine_count > len(self.mines):
            return
            
        if index == len(locs): # valid solution found
            sol = []
            for x,y in locs:
                curr = self.tiles[x][y]
                if curr.get_type() is MINE:
                    sol.append(1)
                else:
                    sol.append(0)
            sols.append(sol)
        else:
            loc = locs[index]
            if self.get_type_at_loc(loc) is MINE:
                self.find_solutions_helper(locs,locs_to_check,sols,index+1,mine_count+1)
            elif self.get_type_at_loc(loc) is NUMBER:
                self.find_solutions_helper(locs,locs_to_check,sols,index+1,mine_count)
                
            #b = copy.deepcopy(self)
            #b = timer.timed_deepcopy(self)
            else:
                self.inject_mine(loc)
                if self.verify_neighbors(locs_to_check):
                    self.find_solutions_helper(locs,locs_to_check,sols,index+1,mine_count+1)
                self.inject_num(loc)
                if self.verify_neighbors(locs_to_check):
                    self.find_solutions_helper(locs,locs_to_check,sols,index+1,mine_count)
                self.undo_inject(loc)


    def solve_exhaustive(self,instant_break=False):
        ccs = self.get_ccs()
        #paths_explored = 0
        self.start_time = time.time()
        for cc in ccs:
            cc,locs_to_check = self.optimize_backtrack_order(cc)
            cc = sorted(cc,key=lambda coord: (coord[0], coord[1]))
            #print(cc)
            if len(cc) <= 10:
                sols = self.find_solutions(cc,locs_to_check)
                # if len(cc) != len(sols[0]):
                #     print('error')
                self.ccs_dict[tuple(cc)] = sols
                self.mark_tile_probs(cc,sols)
                # if update_graphic:
                #     self.open_known_tiles(cc,sols)
                # else:
                #     self.mark_tile_probs(cc,sols)


            else:
                # splits should have 4 locs minimum
                initial_split = len(cc)//5
                for split in range(initial_split,0,-1):
                    #print(split)
                    subdivs = subdivide_locs(cc,split)
                    # shifted_subdiv = shift_and_subdivide_locs(cc,split)
                    # all_subdivs = subdiv+shifted_subdiv
                    for i in range(len(subdivs)):
                        sols = self.find_solutions(subdivs[i],locs_to_check)
                        #print(subdivs[i])
                        #self.mark_known_tiles_given_sols(subdiv[i],sols)
                        self.mark_tile_probs(subdivs[i],sols)
                        info_found = self.mark_known_tiles()
                        if instant_break and info_found:
                            #print(time.time()-start_time)
                            return
                        # else:
                        #     self.mark_known_tiles(subdiv[i],sols)
                        if split == 1:
                            # if len(cc) != len(sols[0]):
                            #     print('error')
                            self.ccs_dict[tuple(cc)] = sols
                            self.mark_tile_probs(cc,sols)
                            
                # if update_graphic:
                #     self.open_marked_tiles(cc)
                # else:
                #     self.mark_tile_probs(cc,sols)
            
        #print(paths_explored)
        #print(time.time()-start_time)
    def solve_exhaustive_and_open(self,instant_break=False):
        self.solve_exhaustive(instant_break=instant_break)
        info_found = self.open_known_tiles()
        return info_found
    # assume all known mines are flagged
    # assume that solve_board() was called previously and failed
    def solve_endgame(self):
        min_flags = 0
        max_flags = 0

        border_tiles = []
        ccs = self.get_ccs()
        

        for cc in ccs:
            for loc in cc:
                border_tiles.append(loc)


        nonfrontier_tiles = []
        for row in range(GSM.rows):
            for col in range(GSM.cols):
                if self.get_type_at_loc((row,col)) == UNKNOWN and (row,col) not in border_tiles:
                    nonfrontier_tiles.append((row,col))

        self.nonfrontier_tiles = nonfrontier_tiles
        if len(nonfrontier_tiles) == 0:
            self.ccs_freqs = []
            for cc, sols in list(self.ccs_dict.items()):
                cc_set = set(cc)
                if cc_set not in ccs:
                    del self.ccs_dict[cc]
                else:
                    freqs = get_minecount_freqs(sols)
                    self.ccs_freqs.append(freqs)
            return 
        remaining_mines = GSM.mine_count-self.flag_count
        if remaining_mines == 0:
            for x,y in nonfrontier_tiles:
                self.reveal_tiles(x,y)
            return
        #print(ccs)
        # if len(ccs) == 0:
        #     prob_mine_local_nonfrontier = remaining_mines/len(nonfrontier_tiles)
        #     tiles_to_update = [self.tiles[t[0]][t[1]] for t in nonfrontier_tiles]
        #     for t in tiles_to_update:
        #         #t.prob_mine_local=0.1
        #         t.prob_mine_local = prob_mine_local_nonfrontier
        #     #self.mark_tile_probs(nonfrontier_tiles,[[prob_mine_local_nonfrontier] * len(nonfrontier_tiles)])
        #     return
        ccs_min = {}
        ccs_max = {}
        self.ccs_freqs = []
        for cc, sols in list(self.ccs_dict.items()):
            cc_set = set(cc)
            if cc_set not in ccs:
                del self.ccs_dict[cc]
            else:
                freqs = get_minecount_freqs(sols)
                self.ccs_freqs.append(freqs)
                # minmax = get_minmax_minecount(sols)
                # local_min = minmax[0]
                # local_max = minmax[1]
                local_min = min(freqs)
                local_max = max(freqs)
                ccs_min[cc] = local_min
                ccs_max[cc] = local_max
                min_flags += local_min
                max_flags += local_max
        # print('min_flags: {}'.format(min_flags))
        # print('max_flags: {}'.format(max_flags))
        # all non-border tiles are mines, solution uses max amount of mines
        if max_flags + len(nonfrontier_tiles) == remaining_mines:
            for cc, sols in self.ccs_dict.items():
                cc_set = set(cc)
                if cc_set not in ccs:
                    continue
                local_max = ccs_max[cc]
                valid_sols = [sol for sol in sols if sum(sol) == local_max]
                self.mark_tile_probs(tuple(cc),valid_sols)
            self.mark_tile_probs(nonfrontier_tiles,[[1] * len(nonfrontier_tiles)])
        # all non-border tiles are safe, solution uses min amount of mines
        elif min_flags == remaining_mines:


            for cc, sols in self.ccs_dict.items():
                cc_set = set(cc)
                if cc_set not in ccs:
                    continue
                local_min = ccs_min[cc]
                valid_sols = [sol for sol in sols if sum(sol) == local_min]
                # valid_sols=sols
                self.mark_tile_probs(tuple(cc),valid_sols)
            self.mark_tile_probs(nonfrontier_tiles,[[0] * len(nonfrontier_tiles)])
        prob.update_nonfrontier_tile_probs(self)
    
    def solve_endgame_and_open(self):

        self.solve_endgame()
        info_found = self.open_known_tiles()
        return info_found

    def open_known_tiles(self):
        opened = False
        for x in range(GSM.rows):
            for y in range(GSM.cols):
                tile = self.tiles[x][y]
                if not tile.is_revealed() and not tile.is_flagged():
                    if tile.prob_mine_local == 1:
                        opened = True
                        self.toggle_flag_at_loc(x,y)
                    elif tile.prob_mine_local == 0:
                        opened = True
                        self.reveal_tiles(x,y)
        return opened

    def mark_known_tiles(self):
        info_found = False
        for x in range(GSM.rows):
            for y in range(GSM.cols):
                tile = self.tiles[x][y]
                if not tile.is_revealed() and not tile.is_flagged():
                    if tile.prob_mine_local == 1:
                        info_found = True
                        self.inject_mine((x,y))
                    elif tile.prob_mine_local == 0:
                        info_found = True
                        self.inject_num((x,y))
        return info_found
    
    def mark_known_tiles_given_sols(self,locs,sols):
        probs = get_probs(sols)
        info_found = False
        for i, prob in enumerate(probs):
            x, y = locs[i]
            if prob == 1:
                info_found = True
                self.inject_mine((x,y)) 
            elif prob == 0:
                info_found = True
                self.inject_num((x,y))
        return info_found
    
    def mark_tile_probs(self,locs,sols):
        probs = get_probs(sols)
        for i in range(len(probs)):
            x,y = locs[i]
            self.tiles[x][y].prob_mine_local = probs[i]

    def open_marked_tiles(self,locs):
        for loc in locs:
            if self.get_type_at_loc(loc) is MINE:
                self.toggle_flag_at_loc(loc[0],loc[1]) 
            elif self.get_type_at_loc(loc) is NUMBER:
                self.reveal_tiles(loc[0],loc[1])


                

def merge_sets(sets):
    merged = []
    while sets:
        base = sets.pop()
        changed = True
        while changed:
            changed = False
            for s in sets[:]:
                if base & s:  # intersection found
                    base |= s
                    sets.remove(s)
                    changed = True
        merged.append(base)
    return sorted(merged,key=len)


def order_tiles_by_connectivity(tile_neighbors):
    visited = set()
    order = []

    # Deterministically pick the start_tile with highest degree and smallest position as tiebreaker
    start_tile = min(
        tile_neighbors,
        key=lambda k: (-len(tile_neighbors[k]), k)
    )

    stack = [start_tile]

    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        order.append(current)

        # Sort neighbors by descending degree and then by position
        neighbors = sorted(
            tile_neighbors[current],
            key=lambda t: (-len(tile_neighbors[t]), t)
        )
        # Reverse to maintain stack behavior (DFS with highest priority first)
        stack.extend(reversed(neighbors))

    return order


def subdivide_locs(locs, split):
    np_locs= np.array(locs)
    parts = np.array_split(np_locs,split)
    list_parts = []
    for part in parts:
        sublist = []
        for coord in part:
            coords = (int(coord[0]),int(coord[1]))
            sublist.append(coords)
        list_parts.append(sublist)

    return list_parts

def shift_and_subdivide_locs(locs, split):
    shift = len(locs)//2
    shifted_locs = locs[shift:] + locs[:shift]
    return subdivide_locs(shifted_locs,split)

def get_probs(sols):
    return [sum(bits) / len(sols) for bits in zip(*sols)]

def get_minecount_freqs(sols):
    mine_counts = [sum(sol) for sol in sols]
    freqs = dict(Counter(mine_counts))
    return freqs

def get_minmax_minecount(sols):
    mine_counts = [sum(sol) for sol in sols]
    min_mines = min(mine_counts)
    max_mines = max(mine_counts)
    return (min_mines,max_mines)

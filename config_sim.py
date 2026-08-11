import random
from collections import Counter, defaultdict
import time
from solver import Solver
from line_profiler import profile
from player import Player
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import numpy as np

player = Player()
def tiny_sample(seq, k):
    if len(seq) == 0:
        return []
    n = len(seq)
    if k == 0:
        return []
    if k == n:
        return list(seq)
    chosen_indices = set()
    while len(chosen_indices) < k:
        chosen_indices.add(random.randrange(n))
    return [seq[i] for i in chosen_indices]

def play_genned_board(board,first_click):
    player.board = board
    board.reveal_tiles(first_click)
    result = player.autoplay()
    return result

def sim_moves_on_genned_boards(board,num_samples,moves,workers=1,batch_size=15,seed=None):
    if workers == 1:
        wins = sim_moves(board,num_samples,moves,seed=seed)
    else:
        wins = {move:0 for move in moves}

        with ProcessPoolExecutor(max_workers=workers) as pool:
            # futures = [pool.submit(sim_moves, board,chunk, moves) for chunk in chunks]
            # for i,future in enumerate(as_completed(futures)):
            #     print(f"Completed chunk {i+1}/{len(futures)}")
            futures = []
            remaining = num_samples
            task_id = 0
            while remaining > 0:
                n = min(batch_size, remaining)
                if seed is None:
                    futures.append(pool.submit(sim_moves, board, n, moves))
                else:
                    futures.append(pool.submit(sim_moves, board, n, moves,seed+task_id))
                    task_id += 1
                remaining -= n
            for i,future in enumerate(as_completed(futures)):
                print(f"Completed chunk {i+1}/{len(futures)}")
                result = future.result()
                for move in moves:
                    wins[move] += result[move]
    print('done')
    print(wins)
    return wins

def sim_moves(board,num_samples,moves,seed=None):
    if seed is not None:
        random.seed(seed)
    nonfrontier_tiles_list = sorted(board.nonfrontier_tiles)
    sim_board = Solver()
    wins = {move:0 for move in moves}
    global_ps = board.global_ps
    total_sols_dict = board.total_sols_dict
    ps_by_mine_count = defaultdict(list)
    for p in global_ps:
        mine_count = sum(p.mines_per_group)
        ps_by_mine_count[mine_count].append(p)
    mc_keys = list(total_sols_dict.keys())
    mc_weights = list(total_sols_dict.values())
    while num_samples > 0:
        sample = sample_mines_per_group(ps_by_mine_count,mc_keys,mc_weights)
        b = gen_board_from_sample(board,sample,nonfrontier_tiles_list)
        for move in moves:
            sim_board.clone_board(b,copy_num_mine_tracker=True)
            sim_board.copy_solver_info(b)
            result = play_genned_board(sim_board,move)
            if result:
                wins[move] += 1
        num_samples -= 1
    return wins

def gen_board_from_sample(board,sample,nonfrontier_tiles_list):
    groups_list = board.groups_list
    new_mines = list(board.flagged_tiles)
    mpg = sample.mines_per_group
    for i, group in enumerate(groups_list):
        num_mines = mpg[i]
        if num_mines > 0:
            mine_locs = tiny_sample(group.tile_locs, num_mines)
            new_mines.extend(mine_locs)

    mines_left = len(board.mines) - len(new_mines)
    nonfrontier_mines = random.sample(nonfrontier_tiles_list,mines_left)
    new_mines.extend(nonfrontier_mines)
    new_board = Solver(empty=True)
    new_board.clone_board(board)
    new_board.mines = new_mines
    new_board.copy_solver_info(board)


    for loc in new_board.mines:
        new_board.update_neighbors_with_minecount(loc)
        new_board.num_mine_tracker[loc] = 9

    return new_board
        
def sample_mines_per_group(ps_by_mine_count,mc_keys,mc_weights):
    mc = random.choices(mc_keys,weights=mc_weights,k=1)[0]
    ps = ps_by_mine_count[mc]
    p_weights = [p.num_cases for p in ps]
    chosen_p = random.choices(ps,weights=p_weights,k=1)[0]
    return chosen_p



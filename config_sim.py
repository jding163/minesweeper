import random
import math
from collections import Counter, defaultdict
import time
from solver import Solver, convolve_freqs
from line_profiler import profile
from player import Player
from concurrent.futures import ProcessPoolExecutor, as_completed
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
    for win in wins:
        wins[win] /= num_samples
    print(wins)
    return wins
# sample a set of mine locations consistent with the current board state
# @return: locations of new mines from generated config
def sample_configuration(board):
    regions = board.regions_list
    groups_list = board.groups_list
    nonfrontier_tiles_list = sorted(board.nonfrontier_tiles)
    num_nf = len(nonfrontier_tiles_list)
    mines_left = board.minecount - board.flag_count

    # per-region weighted counts of total mines
    for region in regions:
        region.freq_dict = defaultdict(int)
        for p in region.ps:
            region.freq_dict[p.total_mines] += p.num_cases

    # convolve regions to get the frontier mine-count distribution, then weight
    # by the number of ways to place the remaining mines on non-frontier tiles
    frontier_freqs = convolve_freqs([region.freq_dict for region in regions]) if regions else {0: 1}
    total_by_count = {}
    for mc, count in frontier_freqs.items():
        nf_mines = mines_left - mc
        if 0 <= nf_mines <= num_nf:
            total_by_count[mc] = count * math.comb(num_nf, nf_mines)

    if not total_by_count:
        return None

    keys = list(total_by_count.keys())
    weights = list(total_by_count.values())
    total_mc = random.choices(keys, weights=weights, k=1)[0]

    # suffix[i] is the convolution of regions[i:].
    suffix = [Counter({0: 1})]
    for region in reversed(regions):
        suffix.append(convolve_freqs([region.freq_dict, suffix[-1]]))
    suffix = list(reversed(suffix))

    rem = total_mc
    sampled = []
    for i, region in enumerate(regions):
        choices = []
        w = []
        next_suffix = suffix[i + 1]
        for p in region.ps:
            t = p.total_mines
            if t > rem:
                continue
            completions = next_suffix.get(rem - t, 0)
            if completions == 0:
                continue
            choices.append(p)
            w.append(p.num_cases * completions)
        if not choices:
            return None
        p = random.choices(choices, weights=w, k=1)[0]
        sampled.append((region, p))
        rem -= p.total_mines

    new_mines = set(board.flagged_tiles)
    for region, p in sampled:
        for gid in region.group_ids:
            n = p.mines_per_group[gid]
            if n:
                new_mines.update(random.sample(groups_list[gid].tile_locs, n))

    nf_mines = mines_left - total_mc
    if nf_mines:
        new_mines.update(random.sample(nonfrontier_tiles_list, nf_mines))

    return new_mines

# @return Solver board with sample config
def gen_board(board):
    mine_locs = sample_configuration(board)
    if mine_locs is None:
        return None
    new_board = Solver(empty=True)
    new_board.clone_board(board)
    new_board.mines = list(mine_locs)
    new_board.copy_solver_info(board)
    for loc in new_board.mines:
        new_board.update_neighbors_with_minecount(loc)
        new_board.num_mine_tracker[loc] = 9
    return new_board

# generate samples and compare empirical mine probabilities to the solver's
# mine_probs for every frontier tile and one non-frontier tile
# @return: dict with loc: (solver_prob, empirical_prob, abs_error)
def validate_sampler(board, num_samples=10000, seed=None, verbose=True):
    if seed is not None:
        random.seed(seed)

    frontier_locs = set()
    for region in board.regions_list:
        frontier_locs.update(region.locs)
    frontier_locs = sorted(frontier_locs)

    nf_loc = min(board.nonfrontier_tiles) if board.nonfrontier_tiles else None
    test_locs = list(frontier_locs)
    if nf_loc is not None:
        test_locs.append(nf_loc)

    counts = {loc: 0 for loc in test_locs}
    valid_samples = 0
    for _ in range(num_samples):
        mines = sample_configuration(board)
        if mines is None:
            continue
        valid_samples += 1
        for loc in test_locs:
            if loc in mines:
                counts[loc] += 1

    results = {}
    max_error = 0.0
    for loc in test_locs:
        empirical = counts[loc] / valid_samples if valid_samples else 0.0
        solver_prob = board.mine_probs[loc]
        error = abs(empirical - solver_prob)
        results[loc] = (solver_prob, empirical, error)
        max_error = max(max_error, error)

    if verbose:
        print(f"Validated {len(test_locs)} locations using {valid_samples} valid samples")
        print(f"{'loc':>10} {'solver':>12} {'empirical':>12} {'error':>12}")
        for loc in test_locs:
            solver_prob, empirical, error = results[loc]
            marker = " ***" if error > 0.05 else ""
            print(f"{str(loc):>10} {solver_prob:12.6f} {empirical:12.6f} {error:12.6f}{marker}")
        print(f"max error: {max_error:.6f}")

    return results


def sim_moves(board, num_samples, moves, seed=None):
    if seed is not None:
        random.seed(seed)
    sim_board = Solver()
    wins = {move: 0 for move in moves}
    while num_samples > 0:
        b = gen_board(board)
        if b is None:
            continue
        for move in moves:
            sim_board.clone_board(b, copy_num_mine_tracker=True)
            sim_board.copy_solver_info(b)
            result = play_genned_board(sim_board, move)
            if result:
                wins[move] += 1
        num_samples -= 1
    return wins



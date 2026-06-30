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

def split_evenly(n, x):
    q, r = divmod(n, x)
    return [q + 1] * r + [q] * (x - r)

def sim_moves_on_genned_boards(board,num_samples,moves,workers=1):
    if workers == 1:
        wins = sim_moves(board,num_samples,moves)
    else:

        wins = {move:0 for move in moves}
        chunks = split_evenly(num_samples,workers)
        print(chunks)
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(sim_moves, board,chunk, moves) for chunk in chunks]
            for i,future in enumerate(as_completed(futures)):
                print(f"Completed chunk {i+1}/{len(futures)}")
                result = future.result()
                for move in moves:
                    wins[move] += result[move]
    print('done')
    print(wins)
    return wins


def sim_moves(board,num_samples,moves):
    nonfrontier_tiles_list = sorted(board.nonfrontier_tiles)
    samples = sample_mines_per_group_x_times(board,num_samples)
    genned_boards = []
    for sample in samples:
        genned_board = gen_board_from_sample(board,sample,nonfrontier_tiles_list)
        genned_boards.append(genned_board)
    print(len(samples),len(genned_boards))

    sim_board = Solver()
    wins = {}
    for move in moves:
        won_at_loc = 0
        for b in genned_boards:
            sim_board.clone_board(b,copy_num_mine_tracker=True)
            sim_board.copy_solver_info(b)
            result = play_genned_board(sim_board,move)
            if result:
                won_at_loc+=1
        wins[move] = won_at_loc
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

def sample_mines_per_group_x_times(board,x):
    start = time.time()
    global_ps = board.global_ps
    total_sols_dict = board.total_sols_dict
    ps_by_mine_count = defaultdict(list)
    for p in global_ps:
        mine_count = sum(p.mines_per_group)
        ps_by_mine_count[mine_count].append(p)
    mc_keys = list(total_sols_dict.keys())
    mc_weights = list(total_sols_dict.values())
    results = []
    for _ in range(x):
        results.append(sample_mines_per_group(ps_by_mine_count,mc_keys,mc_weights))
    # print('total sols:',board.total_sols)
    num_loc_sols = sum([p.num_cases for p in global_ps])
    # print('local sols:', num_loc_sols)
    # print('sample_mines_per_group_x_times():',time.time()-start)
    return results




def verify_sampling_distribution_from_samples(board, samples):
    total_sols_dict = board.total_sols_dict
    global_ps = board.global_ps
    ps_by_mine_count = defaultdict(list)
    for p in global_ps:
        mine_count = sum(p.mines_per_group)
        ps_by_mine_count[mine_count].append(p)
    global_ps = ps_by_mine_count
    total_sols = sum(total_sols_dict.values())
    expected_probs_per_mine_count = {m: count / total_sols for m, count in total_sols_dict.items()}

    # Track counts
    mine_count_samples = []
    possibility_counts = defaultdict(lambda: Counter())
    
    # Precompute expected probabilities per possibility inside each mine count bucket
    expected_probs_per_possibility = {}
    for m, ps in global_ps.items():
        total_cases = sum(p.num_cases for p in ps)

        expected_probs_per_possibility[m] = {tuple(p.mines_per_group): p.num_cases / total_cases for p in ps}
    # Count samples
    for p in samples:
        m = sum(p.mines_per_group)
        mpg = tuple(p.mines_per_group)

        mine_count_samples.append(m)
        possibility_counts[m][mpg] += 1

    num_samples = len(samples)
    empirical_counts_mine = Counter(mine_count_samples)
    empirical_probs_per_mine_count = {m: empirical_counts_mine.get(m, 0) / num_samples for m in total_sols_dict.keys()}
    error_per_mine_count = {m: abs(empirical_probs_per_mine_count[m] - expected_probs_per_mine_count[m]) for m in total_sols_dict.keys()}

    # Calculate empirical and expected probabilities per possibility
    possibility_stats = {}
    for m in global_ps.keys():
        empirical_total = sum(possibility_counts[m].values())
        stats = {}
        for p in global_ps[m]:
            mpg = tuple(p.mines_per_group)
            empirical_p = possibility_counts[m][mpg] / empirical_total if empirical_total > 0 else 0
            expected_p = expected_probs_per_possibility[m][mpg]
            stats[mpg] = {
                'empirical': empirical_p,
                'expected': expected_p,
                'abs_error': abs(empirical_p - expected_p)
            }
        possibility_stats[m] = stats

    # Print summary for mine counts
    print("Mine count | Empirical P | Expected P | Abs. Error")
    for m in sorted(total_sols_dict.keys()):
        print(f"{m:10} | {empirical_probs_per_mine_count[m]:.5f} | {expected_probs_per_mine_count[m]:.5f} | {error_per_mine_count[m]:.5f}")

    for m in sorted(possibility_stats.keys()):
        print(f"\nTop possibility errors for mine count {m}:")
        sorted_poss = sorted(possibility_stats[m].items(), key=lambda x: x[1]['abs_error'], reverse=True)[:5]
        for p, stats in sorted_poss:
            print(f"Possibility {p} | Emp: {stats['empirical']:.5f} | Exp: {stats['expected']:.5f} | AbsErr: {stats['abs_error']:.5f}")

    return {
        'mine_count_stats': {
            'empirical': empirical_probs_per_mine_count,
            'expected': expected_probs_per_mine_count,
            'error': error_per_mine_count,
        },
        'possibility_stats': possibility_stats
    }





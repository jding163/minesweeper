import random
from collections import Counter, defaultdict
import time
import copy
from solver import Solver
from line_profiler import profile

x = 0


def tiny_sample(seq, k):
    n = len(seq)
    if k == 0:
        return []
    if k == n:
        return list(seq)
    chosen_indices = set()
    while len(chosen_indices) < k:
        chosen_indices.add(random.randrange(n))
    return [seq[i] for i in chosen_indices]

@profile
def gen_board_from_sample(board,sample,nonfrontier_tiles_list):
    groups_list = board.groups_list
    new_mines = list(board.flagged_tiles)
    mpg = sample.mines_per_group
    start = time.time()

    for i, group in enumerate(groups_list):
        num_mines = mpg[i]
        if num_mines > 0:
            mine_locs = tiny_sample(group.tile_locs, num_mines)
            new_mines.extend(mine_locs)



    mines_left = len(board.mines) - len(new_mines)
    nonfrontier_mines = random.sample(nonfrontier_tiles_list,mines_left)
    new_mines.extend(nonfrontier_mines)
    elapsed = time.time()-start




    new_board = Solver(empty=True)
    new_board.clone_board(board)
    new_board.mines = new_mines
    new_board.copy_solver_info(board)


    new_board.mines = new_mines

    return elapsed
        

    

    


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
    print('total sols:',board.total_sols)
    num_loc_sols = sum([p.num_cases for p in global_ps])
    print('local sols:', num_loc_sols)
    print('sample_mines_per_group_x_times():',time.time()-start)
    return results



from collections import Counter, defaultdict

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

    # Optional: print top few possibility errors per mine count
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





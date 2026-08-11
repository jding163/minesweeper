import sys, os, types, traceback, math

# Stub missing deps so we can import the game modules headlessly.
sys.modules['line_profiler'] = types.SimpleNamespace(profile=lambda f: f)
scipy = types.ModuleType('scipy')
scipy.stats = types.ModuleType('scipy.stats')
sys.modules['scipy'] = scipy
sys.modules['scipy.stats'] = scipy.stats

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import controller as C  # load first to resolve circular imports
from player import Player
from solver import Solver
import strategy as strat

def inspect_diff(board):
    backup_mine_probs = board.mine_probs.copy()
    backup_total_sols = board.total_sols
    backup_total_sols_dict = dict(board.total_sols_dict)
    backup_global_ps = list(board.global_ps)

    board.mine_probs[:] = -1
    regions = board.get_updated_regions_list()
    groups_list = board.find_possibilities(regions)
    frontier_locs = set(loc for region in regions for loc in region.locs)
    nonfrontier_locs = set(ul for ul in board.unrevealed_tiles if ul not in frontier_locs)

    a_test, total_sols_test = board.calc_prob_at_board_test(regions, groups_list, nonfrontier_locs)
    safe_test, mine_test, safest_test, total_sols_test2 = board.calc_probs_for_board_test(
        regions, groups_list, nonfrontier_locs, update_self=False)
    safe_old, mine_old, safest_old, total_sols_old = board.calc_probs_for_board(
        regions, groups_list, nonfrontier_locs, update_self=True)
    old_probs = board.mine_probs.copy()

    board.mine_probs[:] = backup_mine_probs
    board.total_sols = backup_total_sols
    board.total_sols_dict = backup_total_sols_dict
    board.global_ps = backup_global_ps

    print('safe_test', sorted(safe_test))
    print('safe_old ', sorted(safe_old))
    print('mine_test', sorted(mine_test))
    print('mine_old ', sorted(mine_old))
    print('total_test', total_sols_test2, 'total_old', total_sols_old)
    print('total_sols  test=', total_sols_test, 'old=', total_sols_old)
    print('safest_prob test=', safest_test, 'old=', safest_old)

    # compare probabilities at every group rep and at every tile where status differs
    compare_locs = set(a_test.keys())
    compare_locs.update(mine_test)
    compare_locs.update(mine_old)
    compare_locs.update(safe_test)
    compare_locs.update(safe_old)
    print('per-loc comparison:')
    for loc in sorted(compare_locs):
        tp = a_test.get(loc, None)
        op = old_probs[loc]
        marker = ''
        if tp is not None and not math.isclose(tp, op, rel_tol=1e-9, abs_tol=1e-12):
            marker = ' <-- DIFF'
        print(f'  {loc}: test={tp!r} old={op:.12f}{marker}')

    # print group containing first differing mine
    for loc in set(mine_test) ^ set(mine_old):
        print('group info for', loc)
        for gi, group_info in enumerate(groups_list):
            if loc in group_info.tile_locs:
                print('  group id', gi, 'tile_locs', group_info.tile_locs, 'clue_indices', group_info.clue_indices)
                rep = group_info.tile_locs[0]
                print('  test prob at rep', rep, a_test.get(rep))
                # print old per-tile probs for this group
                for tloc in group_info.tile_locs:
                    print('    old', tloc, old_probs[tloc])


def try_seed(seed, strategy_cls=strat.SecSafety):
    board = Solver()
    board.populate((0,0), seed=seed)
    board.reveal_tiles((0,0))
    player = Player()
    player.set_board(board)
    player.set_strategy(strategy_cls())
    try:
        player.autoplay(risk=True)
    except AssertionError as e:
        return True, e, board
    return False, None, board

if __name__ == '__main__':
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    for seed in range(start, start + count):
        failed, exc, board = try_seed(seed)
        if failed:
            print(f"ASSERT FAILED at seed {seed}")
            print("Exception:", exc)
            traceback.print_exc()
            inspect_diff(board)
            board.save_board(f'failed_board_{seed}')
            break
    else:
        print(f"No assert failures in seeds {start}-{start+count-1}")

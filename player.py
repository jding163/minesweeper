from solver import Solver
import time
from game_state_manager import GSM
import sys
import random
import strategy as strat
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import time
from line_profiler import profile
import logging
import statistics
import math
from solver import TimeoutException
import fifty_fifty_detection as ffd
import controller as C
import os
import argparse
from settings import ROWS, COLS, NUM_MINES                                                                                   
max_size = sys.maxsize
min_size = 0


def run_game(seed, strat, timeout, dims=None, minecount=None):
    player = Player(timeout=timeout, dims=dims, minecount=minecount)
    player.set_strategy(strat)

    try:
        result = player.play_game(seed=seed)
    except TimeoutException as e:
        result= {
            'seed': seed,
            'won': False,
            'time': timeout,
            'timeout': True
        }
    except Exception as e:
        result= {
            'seed': seed,
            'won': False,
            'time': -1,
            'error': str(e)
        }
    result['collect'] = player.board.collected
    return result

class Player():
    executor = None
    def __init__(self, timeout=None, dims=None, minecount=None):
        self.strategy = strat.SafestTile()
        self.timeout = timeout
        self.dims = dims
        self.minecount = minecount

    def set_executor(executor):
        Player.executor = executor

    def set_board(self,board):
        self.board = board
    def set_strategy(self,strat):
        self.strategy = strat
    
    def find_safest_among_locs(self,locs):
        min_prob = 1
        min_loc = (-1,-1)
        for loc in locs:
            prob_mine = self.board.mine_probs[loc]
            if prob_mine < min_prob:
                min_prob = prob_mine
                min_loc = loc
        return min_loc
    def get_suggestion(self):
        # on a fresh board, suggest corner
        if len(self.board.revealed_tiles) == 0:
            return [], [], [self.board.default_first_click()]

        safe_locs, mine_locs=self.board.solve_exhaustive()
        if len(safe_locs) > 0:
            return safe_locs,mine_locs,[]
        else:
            best_move = self.find_best_move()
            return [],mine_locs, [best_move]

    def find_best_move(self):
        if len(self.board.ff_groups) > 0:
            ff_groups = sorted(self.board.ff_groups, key=lambda sublist: (sublist[0][0], sublist[0][1]))
            best_move = ff_groups[0][0]
        elif len(self.board.ic_regions) > 0:
            isolated_locs = []
            for region in self.board.ic_regions:
                for loc in region.locs:
                    isolated_locs.append(loc)
            isolated_locs = sorted(isolated_locs,key=lambda k: [k[0], k[1]])
            best_move = self.strategy.find_move_from_locs(self.board,isolated_locs)

        else:
            best_move = self.strategy.find_move(self.board)
        return best_move
    
    # @return: True if a move is made, else false
    def play_one_step(self,risk=True):
        game_lost = self.board.death_click is not None
        game_won = self.board.is_complete()
        if game_lost or game_won:
            return False
        if self.board.solve_trivial_and_open():
            return True
        elif self.board.solve_exhaustive_and_open():
            return True

        game_lost = self.board.death_click is not None
        game_won = self.board.is_complete()
        game_over = game_lost or game_won
        if risk is True and not game_over:
            best_move = self.find_best_move()

            self.board.reveal_tiles(best_move)
            return True
        return False

    def autoplay(self,risk=True):
        
        while True:
            game_lost = self.board.death_click is not None
            if game_lost:
                return False
            game_won = self.board.is_complete()
            if game_won:
                return True
            move_made = self.play_one_step(risk=risk)
            if not move_made:
                break
        return False

    def play_game(self, seed=None):
        if self.dims is not None:
            rows, cols = self.dims
            minecount = self.minecount if self.minecount is not None else GSM.mine_count
            GSM.set_board((rows, cols, minecount))
        self.board = Solver()
        if self.timeout is not None:
            self.board.deadline = time.time() + self.timeout
        self.board.populate((0,0), seed=seed)
        start_time = time.time()

        self.board.reveal_tiles((0,0))
        self.autoplay()


        end_time = time.time()
        duration = end_time - start_time

        return {
            'seed': seed,
            'won': self.board.is_complete() and self.board.verify_win(),
            'time': duration
        }
    
    def find_matching_board_state(self,reqs,first_click=(0,0)):
        if first_click in reqs.keys() and reqs[first_click] == -1:
            print('impossible requirements')
            return
        while True:
            seed = random.randint(min_size,max_size)
            C.handle_keypress_n()
            C.update_mouse_pos(first_click[0], first_click[1])
            C.handle_board_click(seed=seed)
            
            reqs_satisfied = True
            for req,tiletype in reqs.items():
                if tiletype == -1: #mine
                    reqs_satisfied = req in self.board.mines
                else:
                    reqs_satisfied = ((not req in self.board.mines) and (self.board.num_mine_tracker[req] == tiletype))
                if not reqs_satisfied:
                    break
            if not reqs_satisfied:
                continue
            return seed


    def play_games(self,num_games,seed=None,seeds_list=None,parallel=True,timeout=60):
        won_seeds = []
        if seeds_list is not None:
            seeds = seeds_list
        else:
            if seed is not None:
                random.seed(seed)
            else:
                seed = random.randint(min_size,max_size)
                random.seed(seed)
            seeds = [random.randint(min_size,max_size) for _ in range(num_games)]
        start_time = time.time()
        results = []
        won_seeds = []
        lost_seeds = []
        error_seeds = []
        collected_seeds = []
        timeouts = 0
        if parallel:

            futures = {Player.executor.submit(run_game, s, self.strategy, timeout, self.dims, self.minecount): s for s in seeds}
            
            for i, future in enumerate(as_completed(futures)):
                if i % 100 == 0:
                    print(i)
                    logging.info(i)
                result = future.result()
                results.append(result)
                #print(f"{i}: Seed {result['seed']}: {'Won' if result['won'] else 'Lost'} in {result['time']:.2f} seconds")
                result_seed = result['seed']
                if 'error' in result:
                    err_msg = result['error']
                    logging.error(f'Error at seed {result_seed}')
                    logging.info(err_msg)
                    error_seeds.append(result_seed)
                if 'timeout' in result:
                    logging.info(f'Timeout at seed {result_seed}')
                    timeouts+=1
                if result['won']:
                    won_seeds.append(result_seed)
                else:
                    lost_seeds.append(result_seed)
                if result['collect']:
                    collected_seeds.append(result_seed)
        else:
            self.timeout = timeout
            for i in range(num_games):
                #print(i)
                
                if i % 100 == 0:
                    print(i)
                    logging.info(i)
                seed=seeds[i]
                logging.info(f'starting game {i}: {seed}')
                try:
                    result = self.play_game(seed=seed)
                except TimeoutException as e:
                    result = {
                        'seed': seed,
                        'won': False,
                        'time': timeout,
                        'timeout': True
                    }
                except Exception as e:
                    result = {
                        'seed': seed,
                        'won': False,
                        'time': -1,
                        'error': str(e)
                    }
                #logging.info(f'finished game {i}: {seed}')

                # print(i)
                # print(seeds[i])
                result['collect'] = self.board.collected

                results.append(result)

                if result['won'] == True:
                    won_seeds.append(seeds[i])
                else:
                    lost_seeds.append(seeds[i])
                result_seed = result['seed']
                if 'error' in result:
                    err_msg = result['error']
                    logging.error(f'Error at seed {result_seed}')
                    logging.info(err_msg)
                    error_seeds.append(result_seed)

                if 'timeout' in result:
                    logging.info(f'Timeout at seed {result_seed}')
                    timeouts+=1
                if result['collect']:
                    collected_seeds.append(result_seed)


        total_wins = sum(1 for r in results if r['won'])
        total_errors = sum(1 for r in results if 'error' in r)
        total_games = len(results)

        total_losses = total_games - total_wins - total_errors
        total_time = sum(r['time'] for r in results if 'error' not in r)
        avg_time = total_time / total_games if total_games > 0 else 0
        avg_time_win = (sum(r['time'] for r in results if r['won']) / total_wins) if total_wins > 0 else 0
        #median_win = statistics.median(r['time'] for r in results if r['won']) if total_wins > 0 else 0

        print("\n--- Statistics Summary ---")
        print(f'Strategy used: {self.strategy}')
        print(f'Seed: {seed}')
        print(f"Total games: {total_games}")
        print(f"Total time: {time.time()-start_time}")
        print(f"Wins: {total_wins}")
        print(f"Losses: {total_losses}")
        print(f"Errors: {total_errors}")
        print(f"Winrate: {total_wins / total_games:.2%}")
        print(f"Average time per game: {avg_time:.2f} seconds")
        print(f"Average time per win: {avg_time_win:.2f} seconds")
        #print(f"Median win: {median_win:.2f}")
        print('timeouts:',timeouts)
        # print(error_seeds)
        return results
    
# given a list of indices and length n, what is the largest # indices within any given interval of n
# n < len(wins)
def calc_mastery(nums, n):
    if not nums:
        return 0

    max_count = 0
    start = 0

    for end in range(len(nums)):
        while nums[end] > nums[start] + n:
            start += 1
        count = end - start + 1
        max_count = max(max_count, count)

    return max_count
def parse_args():
    parser = argparse.ArgumentParser(description="Performance benchmarking")
    parser.add_argument('--rows','-r',type=int,default=30,help="board rows")
    parser.add_argument('--cols','-c',type=int,default=16,help="board columns")
    parser.add_argument('--mines','-m',type=int,default=99,help="board minecount")
    parser.add_argument('--games','-g',type=int,default=1000,help="number of games to play")
    parser.add_argument('--seed','-s',type=int,default=None,help="random seed")
    parser.add_argument('--workers','-w',type=int,default=os.cpu_count(),help="number of games to play")
    parser.add_argument('--strategy',choices=['SecSafety','SafestTile'],default="SecSafety",help="strategy to use")
    parser.add_argument('--timeout','-t',type=int,default=30,help="per-game timeout in seconds")
    parser.add_argument('--parallel',action=argparse.BooleanOptionalAction,default=True,help="run games in parallel")
    return parser.parse_args()



# seed used for testing: -7778276623403
def main():
    args = parse_args()
    logging.basicConfig(
        filename='debug.log',            # File to write to
        filemode='w',                    # 'w' to overwrite, 'a' to append
        level=logging.DEBUG,             # Minimum logging level
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    rows,cols,mines = args.rows,args.cols,args.mines
    dims = (rows,cols)

    workers = max(args.workers,1)
    timeout = args.timeout
    executor = ProcessPoolExecutor(max_workers=workers)
    strategy_class = getattr(strat,args.strategy)
    Player.set_executor(executor)
    p = Player(timeout=timeout,dims=dims,minecount=mines)
    p.set_strategy(strategy_class())

    # print(res)
    # seed=-7778276623403
    games = args.games
    parallel = args.parallel
    seed = args.seed
    w1 = p.play_games(games,seed=seed,parallel=parallel,timeout=timeout)





if __name__ == '__main__':
    main()


    # max_workers = multiprocessing.cpu_count()
    # print(max_workers)
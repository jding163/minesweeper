from solver import Solver
import controller as C
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
from solver import TimeoutException
import fifty_fifty_detection as ffd



max_size = sys.maxsize
#min_size = -sys.maxsize - 1
min_size = 0


def run_game(seed,strat,timeout):
    player = Player(timeout=timeout)  
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
    def __init__(self,timeout=None):
        self.strategy = strat.SafestTile()
        self.timeout=timeout
    def set_board(self,board):
        self.board = board
    def set_strategy(self,strat):
        self.strategy = strat
    def set_game(self,game):
        self.game = game
    
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
        safe_locs, mine_locs=self.board.solve_exhaustive()
        if len(safe_locs) > 0:
            return safe_locs,mine_locs
        else:
            best_move = self.find_best_move()
            return [best_move],mine_locs

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

    @profile
    def play_game(self,seed=None):
        #C.handle_keypress_n()  # full reset
        self.board = Solver()
        if self.timeout is not None:
            self.board.deadline = time.time() + self.timeout

        self.board.populate((0,0),seed=seed)
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
            seeds = [random.randint(min_size,max_size) for _ in range(num_games)]
        start_time = time.time()
        #seeds = seeds[2350:2400]

        results = []
        won_seeds = []
        error_seeds = []
        collected_seeds = []
        timeouts = 0
        if parallel:
            #max_workers = multiprocessing.cpu_count()
            max_workers = 6
            with ProcessPoolExecutor(max_workers=max_workers) as executor:

                futures = {executor.submit(run_game, s,self.strategy,timeout): s for s in seeds}
                
                for i, future in enumerate(as_completed(futures)):
                    if i % 250 == 0:
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
                    if 'timeout' in result:
                        logging.info(f'Timeout at seed {result_seed}')
                        timeouts+=1
                    if result['won']:
                        won_seeds.append(result_seed)
                    if result['collect']:
                        collected_seeds.append(result_seed)
        else:
            self.timeout = timeout
            for i in range(num_games):
                #print(i)
                
                if i % 250 == 0:
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
                result_seed = result['seed']
                if 'error' in result:
                    err_msg = result['error']
                    logging.error(f'Error at seed {result_seed}')
                    logging.info(err_msg)
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
        median_win = statistics.median(r['time'] for r in results if r['won'])

        print("\n--- Statistics Summary ---")
        print(f'Strategy used: {self.strategy}')
        print(f"Total games: {total_games}")
        print(f"Total time: {time.time()-start_time}")
        print(f"Wins: {total_wins}")
        print(f"Losses: {total_losses}")
        print(f"Errors: {total_errors}")
        print(f"Winrate: {total_wins / total_games:.2%}")
        print(f"Average time per game: {avg_time:.2f} seconds")
        print(f"Average time per win: {avg_time_win:.2f} seconds")
        print(f"Median win: {median_win:.2f}")
        print('timeouts:',timeouts)


        # with open("seeds.txt", "w") as file:
        #     for seed in won_seeds:
        #         file.write(f'{seed}\n')
        with open("seeds.txt", "w") as file:
            for seed in collected_seeds:
                file.write(f'{seed}\n')

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


def main():

    logging.basicConfig(
        filename='debug.log',            # File to write to
        filemode='w',                    # 'w' to overwrite, 'a' to append
        level=logging.DEBUG,             # Minimum logging level
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    # b = Solver()
    # b.display = None
    #b=Solver()

    p = Player(timeout=60)
    #p.set_strategy(strat.SafestTile())
    #p.set_strategy(strat.SafestTileAndLikeliestOpening())
    p.set_strategy(strat.SecSafety())

    # with open('seeds1.txt', 'r') as f:
    #     seeds_list = [int(line.strip()) for line in f]
    # p.play_games(len(seeds_list),seeds_list=seeds_list,parallel=False)
    # C.set_player(p)
    # C.set_board(b)
    seed=-7778276623403
    #seed=-222204841234
    #seed=29849475784
    #seed=5
    # res = p.play_game(seed=seed)
    # print(res)
    w1 = p.play_games(100,seed=seed,parallel=False,timeout=30)
    # for w in w1:
    #     print(w)


    # set1 = set(w1)
    # set2 = set(w2)

    # in_both = list(set1 & set2)       # Intersection
    # only_in_w1 = list(set1 - set2)    # Elements only in w1
    # only_in_w2 = list(set2 - set1)    # Elements only in w2
    # print('w1 wins:', len(w1))
    # print('w2 wins:', len(w2))
    # print("In both:", len(in_both))
    # print("Only in w1:", len(only_in_w1))
    # print("Only in w2:", len(only_in_w2))
    # print('w1:')
    # for item in only_in_w1:
    #     print(item)
    # print('w2:')
    # for item in only_in_w2:
    #     print(item)
    # print('Best mastery:',calc_mastery(w1,100))




if __name__ == '__main__':
    main()


    # max_workers = multiprocessing.cpu_count()
    # print(max_workers)
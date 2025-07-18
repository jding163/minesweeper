from solver import Solver
import controller as C
import time
from game_state_manager import GSM
import sys
import random
import probability as prob
import pygame
import strategy as strat
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import time
from line_profiler import profile


max_size = sys.maxsize
#min_size = -sys.maxsize - 1
min_size = 0


def run_game(seed,strat):
    player = Player()  
    player.set_strategy(strat)
    return player.play_game(seed=seed)

class Player():
    def __init__(self):
        self.strategy = strat.SafestTile()
    def set_board(self,board):
        self.board = board
    def set_strategy(self,strat):
        self.strategy = strat
    def set_game(self,game):
        self.game = game
    @profile
    def play_one_step(self,risk=True):


        #game_over = not GSM.get_game_state() or (self.board.is_complete() and self.board.verify_win())
        game_over = not GSM.get_game_state() or self.board.is_complete()

        if game_over:
            return
        if self.board.solve_trivial_and_open():
            return

        elif self.board.solve_exhaustive_and_open():
            return
        elif self.board.solve_endgame_and_open():
            return 
        #probs should be marked already
        #game_over = not GSM.get_game_state() or (self.board.is_complete() and self.board.verify_win())
        game_over = not GSM.get_game_state() or self.board.is_complete()


        if risk is True and not game_over:
            x,y = self.strategy.find_move(self.board)
            #x,y = prob.find_safest_tile(self.board)
            self.board.reveal_tiles(x,y)

    def autoplay(self,risk=True):
        while True:
            #game_over = not GSM.get_game_state() or (self.board.is_complete() and self.board.verify_win())
            game_over = not GSM.get_game_state() or self.board.is_complete()
            if game_over:
                break
            self.play_one_step(risk=risk)
    
    def play_game(self,seed=None):
        #C.handle_keypress_n()  # full reset
        #GSM.set_game_state(True)
        self.board = Solver(run_pygame=False)

        self.board.populate((0,0),seed=seed)
        start_time = time.time()

        self.board.reveal_tiles(0,0)
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
                x,y = req
                if tiletype == -1: #mine
                    reqs_satisfied = (x,y) in self.board.mines
                else:
                    reqs_satisfied = ((not (x,y) in self.board.mines) and (self.board.tiles[x][y].get_adj_mines() == tiletype))
                if not reqs_satisfied:
                    break
            if not reqs_satisfied:
                continue
            return seed


    def play_games_on_seed(self,num_games,seed,parallel=True):
        seeds = [seed] * num_games

        start_time = time.time()
        results = []
        if parallel:
            max_workers = multiprocessing.cpu_count()
            #max_workers = 4
            with ProcessPoolExecutor(max_workers=max_workers) as executor:

                futures = {executor.submit(run_game, s,self.strategy): s for s in seeds}
                
                for i, future in enumerate(as_completed(futures)):
                    result = future.result()
                    results.append(result)
                    print(f"{i}: Seed {result['seed']}: {'Won' if result['won'] else 'Lost'} in {result['time']:.2f} seconds")

        else:

            for i in range(num_games):
                print(i)

                result = self.play_game(seed=seeds[i])
                results.append(result)
                print(f"Seed {result['seed']}: {'Won' if result['won'] else 'Lost'} in {result['time']:.2f} seconds")

        total_games = len(results)
        total_wins = sum(1 for r in results if r['won'])
        total_losses = total_games - total_wins
        total_time = sum(r['time'] for r in results)
        avg_time = total_time / total_games if total_games > 0 else 0
        avg_time_win = (sum(r['time'] for r in results if r['won']) / total_wins) if total_wins > 0 else 0

        print("\n--- Statistics Summary ---")
        print(f'Strategy used: {self.strategy}')
        print(f"Total games: {total_games}")
        print(f"Total time: {time.time()-start_time}")
        print(f"Wins: {total_wins}")
        print(f"Losses: {total_losses}")
        print(f"Winrate: {total_wins / total_games:.2%}")
        print(f"Average time per game: {avg_time:.2f} seconds")
        print(f"Average time per win: {avg_time_win:.2f} seconds")

    def play_games(self,num_games,seed=None,seeds_list=None,parallel=True):
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
        if parallel:
            max_workers = multiprocessing.cpu_count()
            max_workers = 4
            with ProcessPoolExecutor(max_workers=max_workers) as executor:

                futures = {executor.submit(run_game, s,self.strategy): s for s in seeds}
                
                for i, future in enumerate(as_completed(futures)):
                    try:
                        result = future.result()
                        results.append(result)
                        print(f"{i}: Seed {result['seed']}: {'Won' if result['won'] else 'Lost'} in {result['time']:.2f} seconds")
                        if result['won']:
                            won_seeds.append(i)
                        if i % 250 == 0:
                            print(i)
                    except:
                        with open('t1.txt', 'w') as f:
                            f.write(f'error at {seeds[i]}')
            

        else:
            won_seeds = []
            for i in range(num_games):
                print(i)
                if i % 250 == 0:
                    print(i)
                result = self.play_game(seed=seeds[i])
                results.append(result)
                if result['won'] == True:
                    won_seeds.append(seeds[i])
                #print(result)
            #seeds_to_print = won_seeds
            #seeds_to_print = Solver.collected_seeds
            # for j in seeds_to_print:
            #     print(j)
                #print(f"Seed {result['seed']}: {'Won' if result['won'] else 'Lost'} in {result['time']:.2f} seconds")
            #print(Solver.collected_seeds)
            # with open('seeds3.txt', 'w') as f:
            #     for item in Solver.collected_seeds:
            #         f.write(f"{item}\n")

        total_games = len(results)
        total_wins = sum(1 for r in results if r['won'])
        total_losses = total_games - total_wins
        total_time = sum(r['time'] for r in results)
        avg_time = total_time / total_games if total_games > 0 else 0
        avg_time_win = (sum(r['time'] for r in results if r['won']) / total_wins) if total_wins > 0 else 0

        print("\n--- Statistics Summary ---")
        print(f'Strategy used: {self.strategy}')
        print(f"Total games: {total_games}")
        print(f"Total time: {time.time()-start_time}")
        print(f"Wins: {total_wins}")
        print(f"Losses: {total_losses}")
        print(f"Winrate: {total_wins / total_games:.2%}")
        print(f"Average time per game: {avg_time:.2f} seconds")
        print(f"Average time per win: {avg_time_win:.2f} seconds")
        return won_seeds
    
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

    # b = Solver()
    # b.display = None
    #b=Solver()

    p = Player()
    #p.set_strategy(strat.SafestTileAndLikeliestOpening())
    p.set_strategy(strat.SecSafety())

    # with open('seeds1.txt', 'r') as f:
    #     seeds_list = [int(line.strip()) for line in f]
    # p.play_games(len(seeds_list),seeds_list=seeds_list,parallel=False)
    # C.set_player(p)
    # C.set_board(b)
    #seed=-1569694061328666230
    seed=29849475784
    #seed=5
    # res = p.play_game(seed=seed)
    # print(res)
    w1 = p.play_games(10,seed=seed,parallel=False)
    # p.play_games_on_seed(10,-1443323327528190823)
    # p.set_strategy(strat.SafestTileAndForce())
    # w2 = p.play_games(100,seed=seed)

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
    print('Best mastery:',calc_mastery(w1,100))




if __name__ == '__main__':
    main()


    # max_workers = multiprocessing.cpu_count()
    # print(max_workers)
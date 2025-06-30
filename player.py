from solver_test import Solver
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


max_size = sys.maxsize
min_size = -sys.maxsize - 1


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
        
    def play_one_step(self,risk=True):
        game_over = not GSM.get_game_state() or (self.board.is_complete() and self.board.verify_win())
        if game_over:
            return
        if self.board.solve_trivial_and_open():
            return

        elif self.board.solve_exhaustive_and_open():
            return
        elif self.board.solve_endgame_and_open():
            return 
        #probs should be marked already
        game_over = not GSM.get_game_state() or (self.board.is_complete() and self.board.verify_win())

        if risk is True and not game_over:
            x,y = self.strategy.find_move(self.board)
            #x,y = prob.find_safest_tile(self.board)
            self.board.reveal_tiles(x,y)
            #self.board.open_safest_tile(convolve)

    def autoplay(self,risk=True):
        while True:
            game_over = not GSM.get_game_state() or (self.board.is_complete() and self.board.verify_win())

            if game_over:
                break
            self.play_one_step(risk=risk)
    
    def play_game(self,starts=[(0,0)],seed=None):
        #C.handle_keypress_n()  # full reset
        #GSM.set_game_state(True)
        self.board = Solver(run_pygame=False)
        start_time = time.time()

        self.board.populate((0,0),seed=seed)
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



    def play_games(self,num_games,seed=None):
        if seed is not None:
            random.seed(seed)
        seeds = [random.randint(min_size,max_size) for _ in range(num_games)]
        start_time = time.time()
        results = []
        
        with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:

            futures = {executor.submit(run_game, s,self.strategy): s for s in seeds}
            
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                results.append(result)
                print(f"{i}: Seed {result['seed']}: {'Won' if result['won'] else 'Lost'} in {result['time']:.2f} seconds")

        # for i in range(num_games):
        #     print(i)

        #     result = self.play_game(seed=seeds[i])
        #     results.append(result)
        #     print(f"Seed {result['seed']}: {'Won' if result['won'] else 'Lost'} in {result['time']:.2f} seconds")

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

def main():

    # b = Solver()
    # b.display = None
    #b=Solver()
    p = Player()
    # C.set_player(p)
    # C.set_board(b)
    p.set_strategy(strat.SafestTileAndLikeliestOpening())
    p.play_games(1000,seed=5)

if __name__ == '__main__':
    main()

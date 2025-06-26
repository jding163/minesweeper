from solver import Solver
import controller as C
import time
from game_state_manager import GSM
import sys
import random
import probability as prob
import pygame
import concurrent.futures


max_size = sys.maxsize
min_size = -sys.maxsize - 1


class Player():
    def __init__(self):
        self.strategy = prob.SafestTile()
    def set_board(self,board):
        self.board = board
    def set_strategy(self,strat):
        self.strategy = strat
    def set_game(self,game):
        self.game = game
        
    def play_one_step(self,risk=True):
        if C.game_over():
            return
        if self.board.solve_trivial_and_open():
            return

        elif self.board.solve_exhaustive_and_open():
            return
        elif self.board.solve_endgame_and_open():
            return 
        #probs should be marked already
        elif risk is True and not C.game_over():
            x,y = self.strategy.find_move(self.board)
            #x,y = prob.find_safest_tile(self.board)
            self.board.reveal_tiles(x,y)
            #self.board.open_safest_tile(convolve)

    def autoplay(self,risk=True):
        while True:
            if C.game_over():
                break
            self.play_one_step(risk=risk)
        #     if C.game_over():
        #         break
        #     progress = False
        #     if self.board.solve_trivial_and_open():
        #         progress = True
        #         continue 
        #     if C.game_over():
        #         break
        #     if self.board.solve_exhaustive_and_open():
        #         progress = True
        #         continue  
        #     if C.game_over():
        #         break
        #     if self.board.solve_endgame_and_open():
        #         progress = True
        #         continue 
        #     #probs should be marked already
        #     if not progress:
        #         if risk is True and not C.game_over():
        #             x,y = self.strategy.find_move(self.board)
        #             #x,y = prob.find_safest_tile(self.board)
        #             self.board.reveal_tiles(x,y)
        #             #self.board.open_safest_tile(convolve)
        #             continue
        #         else:
        #             break
        # return True
    
    def play_game(self,starts=[(0,0)],seed=None):
        C.handle_keypress_n()  # full reset

        start_time = time.time()
        won = False

        for x, y in starts:
            C.update_mouse_pos(x, y)
            C.handle_board_click(seed=seed)
            self.autoplay()

            if C.game_won():
                won = True
                #break

        end_time = time.time()
        duration = end_time - start_time

        return {
            'seed': seed,
            'won': won,
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
        #seeds = [1952622651856132950 for _ in range(num_games)]
        start_time = time.time()
        results = []
        #starts = [(0,0),(GSM.rows-1,0),(GSM.rows-1,GSM.cols-1),(0,GSM.cols-1)]
        for i in range(num_games):
            print(i)

            result = self.play_game(seed=seeds[i])
            results.append(result)
            print(f"Seed {result['seed']}: {'Won' if result['won'] else 'Lost'} in {result['time']:.2f} seconds")

        # for result in results:
        #     print(f"Seed {result['seed']}: {'Won' if result['won'] else 'Lost'} in {result['time']:.2f} seconds")
        # Stats summary
        total_games = len(results)
        total_wins = sum(1 for r in results if r['won'])
        total_losses = total_games - total_wins
        total_time = sum(r['time'] for r in results)
        avg_time = total_time / total_games if total_games > 0 else 0
        avg_time_win = (sum(r['time'] for r in results if r['won']) / total_wins) if total_wins > 0 else 0

        print("\n--- Statistics Summary ---")
        print(f"Total games: {total_games}")
        print(f"Total time: {time.time()-start_time}")
        print(f"Wins: {total_wins}")
        print(f"Losses: {total_losses}")
        print(f"Winrate: {total_wins / total_games:.2%}")
        print(f"Average time per game: {avg_time:.2f} seconds")
        print(f"Average time per win: {avg_time_win:.2f} seconds")
        # for i in range(num_games):
        #     print(i)
        #     no_err = True
        #     for x,y in range(len(starts)):
        #         C.handle_keypress_n() # reset
        #         start_time = time.time()
        #         won = False
        #         C.update_mouse_pos(x,y)
        #         C.handle_board_click(seed=seeds[i])
        #         #print(self.board.mines)
        #         no_err = self.autoplay()
        #         if C.game_won():
        #             won_games +=1
        #         if no_err is False:
        #             break
        #     if no_err is False:
        #         err_count += 1
        #         break
        # print('won_games: {}/{}'.format(won_games,num_games*len(starts)))
        # print(time.time()-start_time)
        # print('errors_encountered: {}'.format(err_count))
        # print('strategy: {}'.format(str(self.strategy)))



# random.seed(0)
# seeds = [random.randint(min_size,max_size) for _ in range(5)]
# print(seeds)
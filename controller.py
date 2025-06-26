from settings import *
from game_state_manager import GSM
import time
from sprites import *
from solver import Solver
#import probability as prob
import solver_test
import merge_tester

import probability_test as prob
import pickle
#import player as P

test=True

board = None
game = None
player = None
mx = 0
my = 0
# def set_board_and_game(b, g):
#     global board, game
#     board = b
#     game = g

def set_player(p):
    global player
    player = p
def set_board(b):
    global board
    board = b
    player.set_board(b)

def set_game(g):
    global game
    game = g
    player.set_game(g)



def update_mouse_pos(x,y):
    global mx,my
    mx=x
    my=y

def reset_board():
    if not test:
        b = Solver()
    else:
        b = solver_test.Solver()
        #b = merge_tester.SolverData()
    set_board(b)

def draw_board(screen):
    board.draw(screen)

def get_flag_count():
    return board.get_flag_count()


def game_won():
    won = board.is_complete() and board.verify_win()
    if won and GSM.get_game_state():
        board.reveal_mines()
        GSM.set_game_state(False)
    return won

def game_over():
    return not GSM.get_game_state() or game_won() 


def handle_settings_button():
    #if not GSM.settings_open:
    game.elapsed_time = time.time() - game.start_time

    game.settings_menu.show()
    GSM.settings_open = True
    GSM.set_game_state(False)
    # else:
    #     game.start_time = time.time() - game.elapsed_time

    #     game.settings_menu.hide()
    #     GSM.settings_open = False
    #     #if game.first_click is False:
    #     GSM.set_game_state(True)


def handle_settings_back_button():
    game.start_time = time.time() - game.elapsed_time
    game.settings_menu.hide()
    GSM.set_game_state(True)

def handle_easy_button():
    GSM.set_board(EASY_SETTINGS)
    game.reset()
    game.resize()
    reset_board()

def handle_intermediate_button():
    GSM.set_board(INTERMEDIATE_SETTINGS)
    game.reset()
    game.resize()
    reset_board()

def handle_expert_button():
    GSM.set_board(EXPERT_SETTINGS)
    game.reset()
    game.resize()
    reset_board()

def handle_custom_button():
    custom_settings = (game.settings_menu.w_slider.get_current_value(),game.settings_menu.h_slider.get_current_value(),game.settings_menu.m_slider.get_current_value())
    GSM.set_board(custom_settings)
    game.reset()
    game.resize()
    reset_board()

def handle_board_click(mines=False,seed=None):
    if my<0:
        return
    if game.first_click:
        board.populate((mx,my),custom_mines=mines,seed=seed)
        game.first_click = False
        game.start_time = time.time()
    if board.tiles[mx][my].is_revealed():
        board.chord((mx,my))

    board.reveal_tiles(mx,my)

def handle_board_right_click():
    if my<0:
        return
    if not game.first_click:
        board.toggle_flag_at_loc(mx,my)  


def handle_keypress_p():
    player.set_strategy(prob.CombinedSafetyAndOpeningScore())
    player.play_one_step()

def handle_keypress_q():
    board.solve_trivial_and_open()

def handle_keypress_w():
    #board.solve_exhaustive(instant_break=True)
    start=time.time()
    board.solve_exhaustive_and_open()
    Board.display_probs = 1
    print(time.time()-start)

def handle_keypress_e():
    board.solve_endgame_and_open()
    Board.display_probs = 1

    #prob.update_nonfrontier_tile_probs(board)
    # l = [(cc, sols) for cc, sols in board.ccs_dict.items() if len(cc) != len (sols[0])]
    # print(l)

def handle_keypress_t(seed=None):
    #test -8425763037098422648, -8433645031250545356,-3837008816949211577
    if GSM.get_game_state() is False:
        handle_keypress_n()
    update_mouse_pos(0,0)

    if seed is None:
        handle_board_click()
    else:
        handle_board_click(seed=seed)
    start = time.time()
    player.set_strategy(prob.SafestTile())

    #player.set_strategy(prob.CombinedSafetyAndOpeningScore())
    #player.set_strategy(prob.SafestTileAndLikeliestOpening())
    player.autoplay()
    print(game_won())
    print(time.time()-start)
    #print(f'merges executed: {solver_test.merge_encounters}')


def handle_keypress_a():
    player.set_strategy(prob.SafestTile())
    player.play_games(1000,seed=5)
def handle_keypress_s():
    player.set_strategy(prob.SafestTileAndLikeliestOpening())
    player.play_games(1000,seed=5)
def handle_keypress_d():
    player.set_strategy(prob.CombinedSafetyAndOpeningScore())
    player.play_games(1000,seed=5)
    #print(f'merges executed: {solver_test.merge_encounters}')

def handle_keypress_u():
    player.set_strategy(prob.SafestTile())
    player.play_one_step()


def handle_keypress_y():
    player.set_strategy(prob.SafestTileAndLikeliestOpening())
    player.play_one_step()

def handle_keypress_k():
    board.open_known_tiles()

def handle_keypress_o():
    
    # x,y = (0,0)
    # tile = board.tiles[x][y]
    # if not tile.is_revealed() and not tile.is_flagged():
    #     prob.calc_prob_of_opening_at_loc(board,(x,y))
    for x in range(GSM.rows):
        for y in range(GSM.cols):
            tile = board.tiles[x][y]
            if not tile.is_revealed() and not tile.is_flagged():
                prob.calc_prob_of_opening_at_loc(board,(x,y))
    Board.display_probs = 2

def handle_keypress_n():
    game.reset()
    reset_board()
def handle_keypress_m():
   reqs = {(0,0):1,(0,2):2,(29,0):1,(29,15):1,(27,15):2}
   #reqs = {(0,0):1}

   print(player.find_matching_board_state(reqs))


def handle_keypress_r():
    board.reveal_board()
    print(sorted(board.mines,key=lambda coord: (coord[0], coord[1]))
)
def handle_keypress_b():
    player.play_game()
def handle_keypress_space():
    if my<0:
        return
    if board.get_type_at_loc((mx,my)) is UNKNOWN or board.get_type_at_loc((mx,my)) is MINE:
        handle_board_right_click()
    elif board.get_type_at_loc((mx,my)) is NUMBER:
        handle_board_click()

def handle_customization_sliders(event):
    event.ui_element.update_text()
def handle_customization_text(event):
    event.ui_element.update_value()

def update_minecount_slider():
    prev_minecount = game.settings_menu.m_slider.get_current_value()
    new_max = game.settings_menu.w_slider.get_current_value() * game.settings_menu.h_slider.get_current_value()
    game.settings_menu.m_slider.value_range = (1,new_max)
    game.settings_menu.m_slider.set_current_value(prev_minecount) if prev_minecount <= new_max else game.settings_menu.m_slider.set_current_value(new_max)
    game.settings_menu.m_slider.update_text()

def update_game_after_first_click():
    game.first_click = False
    game.start_time = time.time()

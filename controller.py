from settings import *
from game_state_manager import GSM
import time
from sprites import *
from solver import Solver
#import probability as prob
import solver
import strategy as strat
import traceback
import config_sim as cs
import probability as prob
import progress as prog
from collections import defaultdict
#import player as P

test=True

board = None
board_ui = None
game = None
player = None
mx = 0
my = 0
default=False
# def set_board_and_game(b, g):
#     global board, game
#     board = b
#     game = g

def set_player(p):
    global player
    player = p
def set_board(b):
    global board,board_ui
    board = b
    player.set_board(b)
    board_ui = BoardUI(board)

def set_game(g):
    global game
    game = g
    player.set_game(g)

def set_first_click(first_click):
    global game
    game.first_click = first_click


def update_mouse_pos(x,y):
    global mx,my
    mx=x
    my=y

def reset_board():
    b = Solver()

    set_board(b)

def draw_board(screen):
    board_ui.draw(screen)

def get_flag_count():
    return board.flag_count


def game_won():
    won = board.is_complete() and board.verify_win()
    if won and GSM.get_game_state():
        board.reveal_mines()
        GSM.set_game_state(False)
    return won

def game_over():
    game_over = board.game_over
    if game_over:
        GSM.set_game_state(False)
    return game_over

def handle_settings_button():
    game.elapsed_time = time.time() - game.start_time

    game.settings_menu.show()
    GSM.settings_open = True
    GSM.set_game_state(False)


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
    
    if board.tile_state_tracker[mx,my] == REVEALED:
        board.chord((mx,my))

    board.reveal_tiles((mx,my))

def handle_board_right_click():
    if my<0:
        return
    if not game.first_click:
        board.toggle_flag_at_loc((mx,my))


def handle_keypress_p():
    player.set_strategy(strat.SecSafety())
    player.play_one_step()

def handle_keypress_q():
    board.solve_trivial_and_open()

def handle_keypress_w():
    #board.solve_exhaustive(instant_break=True)
    start=time.time()
    #board.solve_exhaustive()
    board.solve_exhaustive_and_open()
    Board.display_probs = 1
    print(time.time()-start)

def handle_keypress_e():
    player.set_strategy(strat.SecSafety())
    print(player.get_suggestion())


def handle_keypress_t(seed=None,timeout=None):
    if GSM.get_game_state() is False:
        handle_keypress_n()
    update_mouse_pos(0,0)

    if seed is None:
        handle_board_click()
    else:
        handle_board_click(seed=seed)
    #player.set_strategy(strat.SafestTile())
    #player.set_strategy(strat.SafestTileAndLikeliestOpening())

    player.set_strategy(strat.SecSafety())
    
    start = time.time()
    if timeout is not None:
        player.board.deadline = start + timeout

    try:
        print(player.autoplay(risk=True))
    except Exception as e:
        print(e)
        traceback.print_exc()
    print(time.time()-start)


def handle_keypress_a():
    player.set_strategy(strat.SafestTile())
    player.play_games(1000,seed=5)
def handle_keypress_s():
    player.set_strategy(strat.SafestTileAndLikeliestOpening())
    player.play_games(10,seed=5,parallel=True)
def handle_keypress_d():
    player.set_strategy(strat.SecSafety())
    player.play_games(100,seed=5,parallel=False)
    # solver.print_frontier_summary()
def handle_keypress_f():
    player.board.find_possibilities()


def handle_keypress_u():
    player.set_strategy(strat.SafestTile())
    player.play_one_step()


def handle_keypress_y():
    player.set_strategy(strat.SafestTileAndLikeliestOpening())
    player.play_one_step()

def handle_keypress_l():
    board = Board.load_board('testboard.npz')
    board = Solver.from_board(board)
    set_board(board)
    set_first_click(False)
    GSM.set_game_state(True)


def handle_keypress_k():
    player.board.save_board('testboard')


def handle_keypress_o():
    Board.display_probs = 2

def handle_keypress_n():
    game.reset()
    reset_board()
def handle_keypress_m():
    #reqs = {(0,0):1,(0,4):1,(2,1):1,(2,3):1}
    reqs = {(0,0):1,(0,15):1}
    #reqs = {(0,0):3}
    #reqs = {(12,4):1,(16,4):1,(12,8):1,(16,8):1}
    first_click=(0,0)
    #first_click = (12,4)
    print(player.find_matching_board_state(reqs,first_click=first_click))


def handle_keypress_r():
    board.reveal_board()
    #print(sorted(board.mines,key=lambda coord: (coord[0], coord[1])))
def handle_keypress_b():
    global board

    if len(board.global_ps) == 0:
        board.solve_exhaustive()

    num_samples = 200
    samples = cs.sample_mines_per_group_x_times(board,num_samples)
    # cs.verify_sampling_distribution_from_samples(board,samples)
    start = time.time()
    nonfrontier_tiles_list = sorted(board.nonfrontier_tiles)
    genned_boards = []
    for sample in samples:
        genned_board = cs.gen_board_from_sample(board,sample,nonfrontier_tiles_list)
        genned_boards.append(genned_board)
    moves = [(14,13),(14,9)]
    wins = {}
    sim_board = Solver()
    for move in moves:
        won_at_loc = 0
        for i,b in enumerate(genned_boards):
            if i% 100 == 0:
                print(i)
            sim_board.clone_board(b,copy_num_mine_tracker=True)
            sim_board.copy_solver_info(b)
            result = cs.play_genned_board(sim_board,move)
            if result:
                won_at_loc+=1
        wins[move] = won_at_loc
    for k,v in wins.items():
        print(f'{k}: {v/num_samples * 100}')
    print('total time:',time.time()-start)
    GSM.set_game_state(True)
    #set_board(board)

    
def handle_keypress_c(seed):
    result = player.play_game(seed=seed)
    print(result)
def handle_keypress_v():
    loc = (mx,my)
    info = prog.calc_progress_info_at_loc(board,loc,0,threshold_on=False)
    print(f'secondary safety at {loc}:',info.sec_safety)
    print(f'finished: {info.finished}')
    # if info.finished:
    #     print(f'probs at {loc}:',info.probs.items())
def handle_keypress_space():
    if my<0:
        return
    if board.tile_state_tracker[mx,my] == UNKNOWN or board.tile_state_tracker[mx,my] == FLAGGED:
        handle_board_right_click()
    else:
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
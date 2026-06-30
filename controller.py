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
from replay_manager import ReplayManager as rm
#import player as P


test=True
executor=None
board = None
board_ui = None
game = None
player = None
mx = 0
my = 0
default=False
future = None
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


def set_executor(ex):
    global executor
    executor = ex

def set_game(g):
    global game
    game = g

def set_first_click(first_click):
    global game
    game.first_click = first_click


def update_mouse_pos(x,y):
    global mx,my
    mx=x
    my=y
def mouse_pos_in_bounds():
    in_bounds = 0 <= mx < board.rows and 0 <= my < board.cols
    return in_bounds
def get_game():
    global game
    return game

def reset_board():
    b = Solver()

    set_board(b)

def draw_board(screen):
    board_ui.draw(screen)

def get_flag_count():
    return board.flag_count


def game_won():
    won = board.is_complete() and board.verify_win()
    if won and GSM.get_game_state() == GSM.running:
        board.reveal_mines()
        GSM.set_game_state(GSM.over)
    return won

def game_over():
    game_over = board.is_complete()
    if game_over:
        GSM.set_game_state(GSM.over)
    return game_over

def toggle_replay():
    if game.replay_paused: #resume
        pause_dur = time.time() - game.replay_paused_time
        game.replay_start += pause_dur
        BoardUI.display_probs = 0

        print(game.replay_paused_time)
        print(pause_dur)
        print(game.replay_start)
    else: #pause
        game.replay_paused_time = time.time()
    game.replay_paused = not game.replay_paused




def handle_pause_button():
    toggle_replay()

def handle_settings_button():
    if not GSM.settings_open:
        game.elapsed_time = time.time() - game.start_time

        game.settings_menu.show()
        GSM.settings_open = True
        GSM.set_game_state(GSM.paused)
    else:
        handle_settings_back_button()
        


def handle_settings_back_button():
    game.start_time = time.time() - game.elapsed_time
    game.settings_menu.hide()
    GSM.set_game_state(GSM.prev_game_state)
    GSM.settings_open = False

def handle_easy_button():
    GSM.set_board(EASY_SETTINGS)
    game.reset()
    #game.resize()
    reset_board()
    GSM.settings_open = False



def handle_intermediate_button():
    GSM.set_board(INTERMEDIATE_SETTINGS)
    game.reset()
    #game.resize()
    reset_board()
    GSM.settings_open = False

def handle_expert_button():
    GSM.set_board(EXPERT_SETTINGS)
    game.reset()
    #game.resize()
    reset_board()
    GSM.settings_open = False



def handle_custom_button():
    custom_settings = (game.settings_menu.w_slider.get_current_value(),game.settings_menu.h_slider.get_current_value(),game.settings_menu.m_slider.get_current_value())
    GSM.set_board(custom_settings)
    game.reset()
    reset_board()
    GSM.settings_open = False


def update_mine_probs_after_click():
    mask = (board.mine_probs != 0) & (board.mine_probs != 1)
    board.mine_probs[mask] = -1.0

def handle_board_click(mines=False,seed=None):

    if GSM.input_disabled():
        return
    in_bounds = mouse_pos_in_bounds()
    if not in_bounds:
        return
    if game.first_click:
        board.populate((mx,my),custom_mines=mines,seed=seed)
        game.first_click = False
        rm.replay_log = []

        game.start_time = time.time()
        event_time = 0
        GSM.set_game_state(GSM.running)
    else:
        event_time = time.time() - game.start_time
    if board.tile_state_tracker[mx,my] == REVEALED:
        board.chord((mx,my))

    board.reveal_tiles((mx,my))
    update_mine_probs_after_click()
    if not game.replay_mode:
        rm.append_event(event_time, 'left_click',(mx,my))


def handle_board_right_click():
    if GSM.input_disabled():
        return
    in_bounds = mouse_pos_in_bounds()
    if not in_bounds:
        return
    event_time = time.time() - game.start_time
    if not game.first_click:
        board.toggle_flag_at_loc((mx,my))
    update_mine_probs_after_click()
    if not game.replay_mode:
        rm.append_event(event_time, 'right_click',(mx,my))


def handle_keypress_p():
    player.set_strategy(strat.SecSafety())
    player.play_one_step()

def handle_keypress_q():
    board.solve_trivial_and_open()

def handle_keypress_w():
    #board.solve_exhaustive(instant_break=True)
    start=time.time()
    board.solve_exhaustive(force=True)
    #board.solve_exhaustive_and_open()
    BoardUI.display_probs = 1
    print(time.time()-start)

def handle_keypress_e():
    player.set_strategy(strat.SecSafety())
    print(player.get_suggestion())


def handle_keypress_t(seed=None,timeout=None):
    global executor
    if GSM.get_game_state() == GSM.over:
        handle_keypress_n()
    GSM.set_game_state(GSM.fresh)
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
    #pickle.dumps(player)

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

def handle_keypress_l(filename='testboard.npz'):
    GSM.set_game_state(GSM.paused)
    game.start_time = time.time()
    #game.reset()
    #GSM.update_dims(board.dims)
    #GSM.update_minecount(board.minecount)
    #board = Board.load_board('testboard.npz')
    # board = Board.load_board('replay.npz')
    board = Board.load_board(filename)
    board = Solver.from_board(board)
    set_board(board)
    game.board = board
    set_first_click(False)
    GSM.set_game_state(GSM.running)

    #print(rm.get_metadata(board))


def handle_keypress_k():
    player.board.save_board('testboard')
    # player.board.save_board('replay')


def handle_keypress_o():
    BoardUI.display_probs = 2

def handle_keypress_n():
    game.reset()
    reset_board()
def handle_keypress_m():
    #reqs = {(0,0):1,(0,4):1,(2,1):1,(2,3):1}
    reqs = {(0,14):3,(0,15):1}
    #reqs = {(0,0):3}
    #reqs = {(12,4):1,(16,4):1,(12,8):1,(16,8):1}
    first_click=(0,0)
    #first_click = (12,4)
    print(player.find_matching_board_state(reqs,first_click=first_click))


def handle_keypress_r():
    board.reveal_board()
    #print(sorted(board.mines,key=lambda coord: (coord[0], coord[1])))


def run_move_sim(board,num_samples):

    if len(board.global_ps) == 0:
        board.solve_exhaustive(force=True)

    num_samples = 1000
    samples = cs.sample_mines_per_group_x_times(board,num_samples)
    # cs.verify_sampling_distribution_from_samples(board,samples)
    start = time.time()
    nonfrontier_tiles_list = sorted(board.nonfrontier_tiles)
    genned_boards = []
    for sample in samples:
        genned_board = cs.gen_board_from_sample(board,sample,nonfrontier_tiles_list)
        genned_boards.append(genned_board)
    moves = [(2,11),(2,12),(2,13),(2,14),(2,15),(3,11),(3,12),(3,13),(3,14),(3,15)]
    workers = 3
    wins = executor.submit(cs.sim_moves_on_genned_boards, genned_boards, moves, workers)
    #wins = cs.sim_moves_on_genned_boards(genned_boards,moves,workers=1)
    # for k,v in wins.items():
    #     print(f'{k}: {v/num_samples * 100}')
    # print('total time:',time.time()-start)
    #set_board(board)
    #print(wins)

def handle_keypress_x():
    rm.save_replay('replay.json',board)
    print('done')


def handle_keypress_z():
    # global board
    # replay_data,replay_board = rm.load_replay('replay.json')
    # board = replay_board
    # set_board(board)
    game.replay_mode = not game.replay_mode

    if game.replay_mode:

        replay_data, _ = load_replay_board()
        game.replay_paused_time = game.replay_start

        #print(replay_data)
        game.replay_index = 0

        game.replay_log = replay_data
        # print(len(game.replay_log))

    else:
        handle_keypress_n()
        game.reset_replay_info()
    #print(game.replay_start)

def load_replay_board():
    global board
    replay_data,replay_board = rm.load_replay('replay.json')
    board = replay_board
    set_board(board)
    game.replay_start = time.time()
    return replay_data,replay_board

def get_replay_dur():
    return rm.replay_dur

def save_replay(filename='replay.json'):
    rm.save_replay(filename,board)
    print('saved')

def process_replay_event(event):
    global mx,my
    mx,my = event['pos']
    if event['action'] == "left_click":
        handle_board_click()
    else:
        handle_board_right_click()



    
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
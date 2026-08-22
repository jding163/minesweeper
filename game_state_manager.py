from settings import *

class GSM:
    fresh,running,paused,over = [0,1,2,3]

    game_state = fresh
    prev_game_state = fresh
    rows = ROWS
    cols = COLS
    width = cols * TILESIZE
    height = rows * TILESIZE
    mine_count = NUM_MINES
    settings_open = False
    @staticmethod
    def get_game_state():
        return GSM.game_state
    
    @staticmethod
    def set_game_state(state):
        GSM.prev_game_state = GSM.game_state
        GSM.game_state = state
    @staticmethod
    def input_disabled():
        return GSM.game_state == GSM.paused or GSM.game_state == GSM.over

    def set_board(settings):
        GSM.rows = settings[0]
        GSM.cols = settings[1]
        GSM.mine_count = settings[2]
        GSM.width = GSM.cols * TILESIZE
        GSM.height = GSM.rows * TILESIZE
    @staticmethod
    def game_won(board):
        won = board.is_complete() and board.verify_win()
        if won and GSM.get_game_state() == GSM.running:
            board.reveal_mines()
            GSM.set_game_state(GSM.over)
        return won
    @staticmethod
    def game_over():
        return GSM.get_game_state() == GSM.over
    @staticmethod
    def update_dims(dims):
        GSM.rows = dims[0]
        GSM.cols = dims[1]


    @staticmethod
    def update_minecount(minecount):
        GSM.mine_count = minecount





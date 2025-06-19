from settings import *
class GSM:

    game_running = True
    rows = ROWS
    cols = COLS
    width = rows * TILESIZE
    height = cols * TILESIZE
    mine_count = NUM_MINES
    settings_open = False
    @staticmethod
    def get_game_state():
        return GSM.game_running
    
    @staticmethod
    def toggle_game_state():
        GSM.game_running = not GSM.game_running
    
    @staticmethod
    def set_game_state(state):
        GSM.game_running = state

    def set_board(settings):
        GSM.rows = settings[0]
        GSM.width = settings[0] * TILESIZE
        GSM.cols = settings[1]
        GSM.height = settings[1] * TILESIZE
        GSM.mine_count = settings[2]
    @staticmethod
    def game_won(board):
        won = board.is_complete() and board.verify_win()
        if won and GSM.get_game_state():
            board.reveal_mines()
            GSM.set_game_state(False)
        return won
    @staticmethod
    def game_over(board):
        return not GSM.get_game_state() or GSM.game_won(board) 




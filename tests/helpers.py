import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np
from game_state_manager import GSM
from settings import FLAGGED, REVEALED, UNKNOWN
from sprites import Board

def make_board(rows, cols, mines=None, first_click=(0, 0)):
    GSM.update_dims((rows, cols))
    mines = set(mines) if mines is not None else set()
    GSM.update_minecount(len(mines))
    board = Board()
    board.populate(first_click, custom_mines=mines)
    return board

# Check that numpy trackers and Python sets are in sync
def assert_state_consistent(board):
    revealed = set(zip(*np.where(board.tile_state_tracker == REVEALED)))
    flagged = set(zip(*np.where(board.tile_state_tracker == FLAGGED)))
    unknown = set(zip(*np.where(board.tile_state_tracker == UNKNOWN)))

    assert revealed == board.revealed_tiles
    assert flagged == board.flagged_tiles
    assert unknown == board.unrevealed_tiles
    assert board.num_revealed == len(revealed)
    assert board.flag_count == len(flagged)

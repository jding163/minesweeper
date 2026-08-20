import os

# might be necessary for image loading problems
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest
from game_state_manager import GSM
from sprites import Board


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset shared/global state before every test."""
    GSM.set_game_state(GSM.fresh)
    Board.suggestion_safe = set()
    Board.suggestion_guess = None
    Board.suggestion_mine = set()
    yield

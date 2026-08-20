import numpy as np
import pytest
from tests.helpers import assert_state_consistent, make_board
from game_state_manager import GSM
from settings import FLAGGED, REVEALED, UNKNOWN


class TestReveal:
    def test_reveal_number_tile(self):
        r, c = 3, 3
        board = make_board(r, c, mines={(0, 0)}, first_click=(2, 2))
        board.reveal_tiles((1, 1))
        assert board.tile_state_tracker[1, 1] == REVEALED
        assert board.num_revealed == 1
        assert (1, 1) in board.revealed_tiles
        assert (1, 1) in board.unfinished_clues
        assert_state_consistent(board)

    def test_reveal_number_does_not_flood(self):
        r, c = 3, 3
        board = make_board(r, c, mines={(0, 0)}, first_click=(2, 2))
        board.reveal_tiles((1, 1))
        assert board.tile_state_tracker[0, 2] == UNKNOWN
        assert board.tile_state_tracker[2, 2] == UNKNOWN
        assert board.num_revealed == 1

    def test_reveal_zero_floods_all_safe(self):
        r, c = 5, 5
        board = make_board(r, c, mines={(0, 0)}, first_click=(4, 4))
        board.reveal_tiles((4, 4))
        assert board.tile_state_tracker[0, 0] == UNKNOWN  # mine stays hidden
        assert board.num_revealed == r * c - 1
        assert board.unrevealed_tiles == {(0, 0)}
        assert_state_consistent(board)

    def test_reveal_flagged_tile_is_ignored(self):
        r, c = 3, 3
        board = make_board(r, c, mines={(0, 0)}, first_click=(2, 2))
        board.toggle_flag_at_loc((1, 1))
        board.reveal_tiles((1, 1))
        assert board.tile_state_tracker[1, 1] == FLAGGED
        assert board.num_revealed == 0

    def test_reveal_already_revealed_is_noop(self):
        r, c = 3, 3
        board = make_board(r, c, mines={(0, 0)}, first_click=(2, 2))
        board.reveal_tiles((1, 1))
        before_revealed = board.num_revealed
        board.reveal_tiles((1, 1))
        assert board.num_revealed == before_revealed

    def test_reveal_mine_sets_death_click_and_game_over(self):
        r, c = 3, 3
        board = make_board(r, c, mines={(1, 1)}, first_click=(0, 0))
        board.reveal_tiles((1, 1))
        assert board.death_click == (1, 1)
        assert board.tile_state_tracker[1, 1] == REVEALED
        assert GSM.get_game_state() == GSM.over


class TestFlag:
    def test_flag_unknown_tile(self):
        r, c = 3, 3
        board = make_board(r, c, mines={(1, 1)})
        board.toggle_flag_at_loc((0, 0))
        assert board.tile_state_tracker[0, 0] == FLAGGED
        assert board.flag_count == 1
        assert (0, 0) in board.flagged_tiles
        assert (0, 0) not in board.unrevealed_tiles
        assert_state_consistent(board)

    def test_unflag_restores_unknown(self):
        r, c = 3, 3
        board = make_board(r, c, mines={(1, 1)})
        board.toggle_flag_at_loc((0, 0))
        board.toggle_flag_at_loc((0, 0))
        assert board.tile_state_tracker[0, 0] == UNKNOWN
        assert board.flag_count == 0
        assert (0, 0) not in board.flagged_tiles
        assert (0, 0) in board.unrevealed_tiles
        assert_state_consistent(board)

    def test_flag_updates_adjacent_counts(self):
        r, c = 3, 3
        board = make_board(r, c, mines={(1, 1)})
        board.toggle_flag_at_loc((0, 0))
        assert board.adj_flag_tracker[1, 1] == 1
        board.toggle_flag_at_loc((0, 2))
        assert board.adj_flag_tracker[1, 1] == 2
        board.toggle_flag_at_loc((0, 0))  # unflag
        assert board.adj_flag_tracker[1, 1] == 1

    def test_flag_on_revealed_tile_is_ignored(self):
        r, c = 3, 3
        board = make_board(r, c, mines={(0, 0)}, first_click=(2, 2))
        board.reveal_tiles((1, 1))
        board.toggle_flag_at_loc((1, 1))
        assert board.tile_state_tracker[1, 1] == REVEALED
        assert board.flag_count == 0

    def test_flag_mine_then_reveal_mines(self):
        r, c = 3, 3
        board = make_board(r, c, mines={(0, 0), (2, 2)}, first_click=(1, 2))
        board.toggle_flag_at_loc((0, 0))
        board.reveal_mines()
        # flagged mine stays flagged; unflagged mines are revealed
        assert board.tile_state_tracker[0, 0] == FLAGGED
        assert board.tile_state_tracker[2, 2] == REVEALED


class TestChord:
    def test_chord_reveals_when_flags_match(self):
        r, c = 3, 3
        board = make_board(r, c, mines={(0, 0)}, first_click=(2, 2))
        board.reveal_tiles((1, 1))
        board.toggle_flag_at_loc((0, 0))
        board.chord((1, 1))
        for loc in board.lookup_neighbors((1, 1)):
            if board.num_mine_tracker[loc] != 9:
                assert board.tile_state_tracker[loc] == REVEALED
        assert_state_consistent(board)

    def test_chord_does_nothing_when_flags_dont_match(self):
        r, c = 3, 3
        board = make_board(r, c, mines={(0, 0), (2, 2)}, first_click=(1, 0))
        board.reveal_tiles((1, 1))
        board.toggle_flag_at_loc((0, 0))
        # (1,1) sees 2 mines but only 1 flag
        board.chord((1, 1))
        assert board.tile_state_tracker[2, 2] == UNKNOWN
        assert board.num_revealed == 1

    def test_chord_removes_finished_clue(self):
        r, c = 3, 3
        board = make_board(r, c, mines={(0, 0)}, first_click=(2, 2))
        board.reveal_tiles((1, 1))
        assert (1, 1) in board.unfinished_clues
        board.toggle_flag_at_loc((0, 0))
        board.chord((1, 1))
        assert (1, 1) not in board.unfinished_clues


class TestWinLoss:
    def test_win_on_all_safe_revealed(self):
        r, c = 2, 2
        board = make_board(r, c, mines={(0, 0)}, first_click=(1, 1))
        board.reveal_tiles((0, 1))
        board.reveal_tiles((1, 0))
        board.reveal_tiles((1, 1))
        assert board.is_complete()
        assert board.verify_win()

    def test_not_complete_with_hidden_safe(self):
        r, c = 2, 2
        board = make_board(r, c, mines={(0, 0)}, first_click=(1, 1))
        board.reveal_tiles((0, 1))
        assert not board.is_complete()
        assert not board.verify_win()

    def test_loss_on_mine_reveal(self):
        r, c = 2, 2
        board = make_board(r, c, mines={(0, 0)}, first_click=(1, 1))
        board.reveal_tiles((0, 0))
        assert not board.verify_win()
        assert GSM.get_game_state() == GSM.over


class TestStateConsistency:
    def test_reveal_maintains_set_consistency(self):
        r, c = 5, 5
        board = make_board(r, c, mines={(0, 0)}, first_click=(4, 4))
        board.reveal_tiles((4, 4))
        assert_state_consistent(board)

    def test_flag_maintains_set_consistency(self):
        r, c = 4, 4
        board = make_board(r, c, mines={(0, 0)}, first_click=(3, 3))
        board.toggle_flag_at_loc((1, 1))
        board.toggle_flag_at_loc((2, 2))
        board.toggle_flag_at_loc((1, 1))  # unflag
        assert_state_consistent(board)

    def test_chord_maintains_set_consistency(self):
        r, c = 3, 3
        board = make_board(r, c, mines={(0, 0)}, first_click=(2, 2))
        board.reveal_tiles((1, 1))
        board.toggle_flag_at_loc((0, 0))
        board.chord((1, 1))
        assert_state_consistent(board)

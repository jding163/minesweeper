import numpy as np
from tests.helpers import assert_state_consistent, make_board
from game_state_manager import GSM
from settings import FLAGGED, REVEALED, UNKNOWN
from sprites import Board

class TestConstruction:
    def test_board_dims_match_gsm(self):
        r,c = 10,20
        board = make_board(r, c)
        assert board.rows == r
        assert board.cols == c
        assert board.dims == (r, c)
        assert GSM.rows == r
        assert GSM.cols == c

    def test_populate_no_mines(self):
        r,c = 5,5
        board = make_board(r, c, mines=set())
        assert board.minecount == 0
        assert board.mines == []
        assert np.all(board.num_mine_tracker == 0)
        assert np.all(board.tile_state_tracker == UNKNOWN)
        assert_state_consistent(board)

    def test_populate_with_mines(self):
        r,c = 5,5
        mines = {(1, 1), (2, 3), (4, 4)}
        board = make_board(r, c, mines=mines, first_click=(0, 0))
        assert board.minecount == len(mines)
        assert set(board.mines) == mines
        for loc in mines:
            assert board.num_mine_tracker[loc] == 9

    # verify that board construction with custom_mines does NOT relocate a mine off first_click
    def test_custom_populate_keeps_first_click_mine(self):
        r,c = 5,5
        board = make_board(r, c, mines={(1, 1)}, first_click=(1, 1))
        assert (1, 1) in board.mines
        assert board.num_mine_tracker[1, 1] == 9

    #verify that board construction without custom mines DOES relocate mine off first click
    def test_populate_seed_avoids_first_click_mine(self):
        r,c = 5,5
        GSM.update_dims((r, c))
        GSM.update_minecount(r*c-1)
        first_click_mine = False
        for _ in range(100):
            board = Board()
            board.populate((0, 0), seed=123123123)
            if (0, 0) in board.mines or board.num_mine_tracker[0, 0] == 9:
                first_click_mine = True
                break
        assert first_click_mine == False

    def test_initial_state_all_unknown(self):
        r,c = 5,5
        board = make_board(r, c, mines={(1, 1)})
        assert np.all(board.tile_state_tracker == UNKNOWN)
        assert board.num_revealed == 0
        assert board.flag_count == 0
        assert_state_consistent(board)


class TestAdjacencyAndNumbers:
    def test_single_mine_neighbors_are_one(self):
        r,c = 3,3
        board = make_board(r, c, mines={(1, 1)})
        assert board.num_mine_tracker[1, 1] == 9
        for loc in board.lookup_neighbors((1, 1)):
            assert board.num_mine_tracker[loc] == 1

    def test_neighbor_loc_accuracy(self):
        r,c = 3,3
        board = make_board(r, c)
        corner = (0,0)
        corner_neighbors = board.lookup_neighbors(corner)
        assert len(corner_neighbors) == 3
        edge = (0,1)
        edge_neighbors = board.lookup_neighbors(edge)
        assert len(edge_neighbors) == 5
        center = (1,1)
        center_neighbors = board.lookup_neighbors(center)
        assert len(center_neighbors) == 8
        neighbors_list = [(corner_neighbors,corner),(center_neighbors,center),(edge_neighbors,edge)]
        for neighbors,loc in neighbors_list:
            for neighbor in neighbors:
                assert neighbor != loc
                assert 0 <= neighbor[0] < r
                assert 0 <= neighbor[1] < c
                x_dist = abs(neighbor[0]-loc[0])
                y_dist = abs(neighbor[1]-loc[1])
                assert x_dist <= 1
                assert y_dist <= 1

    def test_multiple_mines_next_to_tiles(self):
        r,c = 3,3
        board = make_board(r, c, mines={(0, 0), (0, 1)})
        assert board.num_mine_tracker[0, 2] == 1  # adjacent only to (0,1)
        assert board.num_mine_tracker[1, 0] == 2  # adjacent to both mines
        assert board.num_mine_tracker[1, 1] == 2  # adjacent to both mines

    def test_neighbor_caching_matches_lookup(self):
        r,c = 4,4
        board = make_board(r, c)
        for r in range(board.rows):
            for c in range(board.cols):
                assert board.tile_neighbors[r][c] == board.lookup_neighbors((r, c))


class TestGuaranteedOpening:
    
    def test_guarantee_opening_first_click_is_zero(self):
        r, c = 9, 9
        GSM.update_dims((r, c))
        GSM.update_minecount(10)
        board = Board()
        board.populate((0, 0), seed=42, guarantee_opening=True)
        assert board.num_mine_tracker[(0, 0)] == 0

    def test_guarantee_opening_neighbors_are_safe(self):
        r, c = 9, 9
        GSM.update_dims((r, c))
        GSM.update_minecount(10)
        first_click = (4, 4)
        board = Board()
        board.populate(first_click, seed=42, guarantee_opening=True)

        protected = set([first_click])
        protected.update(board.lookup_neighbors(first_click))
        for loc in protected:
            assert loc not in board.mines
            assert board.num_mine_tracker[loc] != 9

    def test_guarantee_opening_consistent_across_seeds(self):
        r, c = 16, 16
        GSM.update_dims((r, c))
        GSM.update_minecount(40)
        first_click = (7, 7)
        for seed in range(100):
            board = Board()
            board.populate(first_click, seed=seed, guarantee_opening=True)
            protected = set([first_click])
            protected.update(board.lookup_neighbors(first_click))
            for loc in protected:
                assert loc not in board.mines
            assert board.num_mine_tracker[first_click] == 0
    def test_guarantee_opening_keeps_consistent_minecount(self):
        r, c = 16, 16
        GSM.update_dims((r, c))
        GSM.update_minecount(40)
        first_click = (7, 7)
        for seed in range(100):
            board = Board()
            board.populate(first_click, seed=seed, guarantee_opening=True)
            assert len(board.mines) == GSM.mine_count


class TestPersistence:
    def test_save_load_roundtrip(self, tmp_path):
        r,c = 5,5
        board = make_board(r,c, mines={(0, 0), (3, 3)}, first_click=(4, 4))
        board.reveal_tiles((4, 4))
        board.toggle_flag_at_loc((1, 1))

        path = tmp_path / "board.npz"
        board.save_board(str(path))
        loaded = Board.load_board(str(path))

        assert np.array_equal(board.num_mine_tracker, loaded.num_mine_tracker)
        assert np.array_equal(board.tile_state_tracker, loaded.tile_state_tracker)
        assert np.array_equal(board.adj_flag_tracker, loaded.adj_flag_tracker)
        assert loaded.rows == board.rows
        assert loaded.cols == board.cols
        assert loaded.minecount == board.minecount
        assert loaded.revealed_tiles == board.revealed_tiles
        assert loaded.unrevealed_tiles == board.unrevealed_tiles
        assert loaded.flagged_tiles == board.flagged_tiles
        assert loaded.num_revealed == board.num_revealed
        assert loaded.flag_count == board.flag_count
        assert_state_consistent(loaded)



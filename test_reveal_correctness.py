"""Verify the optimized reveal_tiles matches the original recursive behavior."""
import numpy as np
import copy
from game_state_manager import GSM
from sprites import Board


def make_board(rows, cols, mines, seed=42):
    GSM.update_dims((rows, cols))
    GSM.update_minecount(mines)
    board = Board()
    board.populate((0, 0), seed=seed)
    return board


def original_reveal_tiles(board, loc):
    """Copy of the old recursive implementation for comparison."""
    if board.tile_state_tracker[loc] != 0:  # UNKNOWN
        return
    board.reveal_tile(loc)
    if board.num_mine_tracker[loc] > 0:
        board.unfinished_clues.add(loc)
    else:
        for nloc in board.lookup_neighbors(loc):
            original_reveal_tiles(board, nloc)


def boards_equal(a, b):
    return (
        np.array_equal(a.tile_state_tracker, b.tile_state_tracker)
        and a.num_revealed == b.num_revealed
        and a.revealed_tiles == b.revealed_tiles
        and a.unrevealed_tiles == b.unrevealed_tiles
        and a.unfinished_clues == b.unfinished_clues
    )


def main():
    configs = [
        (10, 10, 10),
        (30, 16, 99),
    ]

    for rows, cols, mines in configs:
        for seed in range(5):
            board1 = make_board(rows, cols, mines, seed=seed)
            board2 = copy.deepcopy(board1)

            zeros = np.where(board1.num_mine_tracker == 0)
            if len(zeros[0]) == 0:
                continue
            click = (int(zeros[0][0]), int(zeros[1][0]))

            board1.reveal_tiles(click)
            original_reveal_tiles(board2, click)

            if not boards_equal(board1, board2):
                print(f"MISMATCH {rows}x{cols}/{mines} seed={seed}")
                print("  new:", board1.tile_state_tracker)
                print("  old:", board2.tile_state_tracker)
                return
    print("All correctness tests passed.")


if __name__ == "__main__":
    main()

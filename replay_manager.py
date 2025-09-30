from dataclasses import dataclass
from dataclasses import asdict

import json
from sprites import Board

@dataclass
class ReplayEvent:
    time: float
    action: str
    pos: tuple[int, int]

class ReplayManager:
    replay_log = []

    def append_event(time, action, pos):
        event = ReplayEvent(time, action, pos)
        ReplayManager.replay_log.append(event)


    def save_replay(filename):
        with open(filename, "w") as f:
            json.dump([asdict(event) for event in ReplayManager.replay_log], f, indent=2)

    def load_replay(replay_file,board_file):
        with open(replay_file, 'r') as f:
            replay_data = json.load(f)
        board = Board.load_board(board_file)
        return replay_data,board
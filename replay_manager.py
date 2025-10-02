from dataclasses import dataclass
from dataclasses import asdict
from typing import Optional, Literal
import json
from sprites import Board
from game_state_manager import GSM

@dataclass
class ReplayMetadata:
    rows: int
    cols: int
    minecount: int
    mode: Literal["seeded", "custom"]   
    seed: Optional[int]                 
    mine_positions: list[tuple[int, int]]

@dataclass
class ReplayEvent:
    time: float
    action: str
    pos: tuple[int, int]

class ReplayManager:
    replay_log = []
    replay_dur = 0

    def append_event(time, action, pos):
        event = ReplayEvent(time, action, pos)
        ReplayManager.replay_log.append(event)

    def get_metadata(board):
        mode = 'custom' if board.seed == None else 'seeded'
        metadata = ReplayMetadata(board.rows,board.cols,board.minecount,mode,board.seed,sorted(board.mines))
        return metadata
    def save_replay(filename,board):
        ReplayManager.replay_dur = ReplayManager.replay_log[-1]['time']
        metadata = ReplayManager.get_metadata(board)
        data = {
            "metadata": asdict(metadata),       # ReplayMetadata dataclass → dict
            "events": [asdict(event) for event in ReplayManager.replay_log]  # list of ReplayEvent dataclasses
        }
        with open(filename, "w") as f:
            json.dump(data,f,indent=2)

    def load_replay(replay_file):
        with open(replay_file, 'r') as f:
            replay_data = json.load(f)
        metadata = replay_data['metadata']
        events = replay_data['events']

        GSM.update_dims((metadata['rows'],metadata['cols']))
        board = Board()
        first_click = events[0]['pos']
        if metadata['mode'] == 'seeded':
            board.populate(first_click,seed=metadata['seed'])
        else:
            board.populate(first_click,custom_mines=metadata['mine_positions'])

        
        #board = Board.load_board(board_file)
        return events,board
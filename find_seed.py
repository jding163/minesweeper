from player import Player
from solver import Solver
import time
from game_state_manager import GSM
import sys
import random
import strategy as strat
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import time
from line_profiler import profile
import logging
import statistics
import math
from solver import TimeoutException
import fifty_fifty_detection as ffd
import controller as C
import os
import argparse
from settings import ROWS, COLS, NUM_MINES   


executor = ProcessPoolExecutor(max_workers=os.cpu_count())

p = Player(timeout=60)
p.set_strategy(strat.SecSafety())

# print(res)
# seed=-7778276623403
games = args.games
parallel = args.parallel
seed = args.seed
w1 = p.play_games(games,seed=seed,parallel=parallel,timeout=timeout)
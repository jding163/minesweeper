# Minesweeper — Probability Solver & Game

A Minesweeper solver that computes exact per-tile mine probabilities and plays expert difficulty (16×30, 99 mines) at a ~53.5% win rate with a guaranteed open first click and ~40.7% win rate with a guaranteed safe first click.
Includes the full game (pygame), live probability overlays, a replay system, and a
seeded benchmark harness.

## Benchmarks

Standard expert board (16×30, 99 mines), first-click-safe, solver knows the total
mine count. Every game is seeded and fully replayable. These results were achieved with a 10-core 2021 Macbook Pro M1 Max.

| Opening | Games | Win rate | Avg time/game |
|---------|------:|---------:|--------------:|
| No      | 10,000 | 40.73%   | 0.11s |
| No      |  1,000 | 42.00%   | 0.09s |
| Yes     | 10,000 | 53.54%   | 0.12s |
| Yes     |  1,000 | 54.90%   | 0.11s |

Reproduce the top row with:

```bash
./sim.sh -s 90743215016795749 -g 10000
```

Or with guaranteed opening:

```bash
./sim.sh -s 90743215016795749 -g 10000 --guarantee-opening
```

### Opening on start vs. no opening

Modern Minesweeper clients guarantee that the first click reveals an opening, so
the clicked tile and its neighbors are mine-free. Older clients only guarantee that the first-click
tile itself is safe.

For this solver, the guaranteed-opening rule is worth roughly 12–14 percentage
points of win rate on expert difficulty. The extra initial information lets the
exact-probability engine resolve more tiles before it has to guess.

### Single-threaded vs. multi-threaded performance

The solver is CPU-bound, and most of the work is embarrassingly parallel across
games. On a 10-core M1 Max, running 1,000 games multi-threaded is about 7–8×
faster than single-threaded, with the same win rate:

| Mode | Games | Total time | Avg time/game | Win rate |
|------|------:|-----------:|--------------:|---------:|
| Single-threaded (`--no-parallel`) | 1,000 | 85.05s | 0.08s | 40.80% |
| Multi-threaded (default) | 1,000 | 11.28s | 0.10s | 40.80% |

```bash
# Single-threaded
./sim.sh -s -7778276623403 -g 1000 --no-parallel

# Multi-threaded
./sim.sh -s -7778276623403 -g 1000
```
## How it works

The solver treats each board state as a constraint-satisfaction problem and
computes the *exact* probability that every hidden tile contains a mine:

1. **Region decomposition** (`solver.py`) — the frontier of hidden tiles bordering
   revealed clues is split into independent connected components, each solvable
   on its own.
2. **Equivalence-class grouping** — hidden tiles with identical clue neighborhoods
   are collapsed into groups; enumeration tracks mines-per-group instead of
   per-tile, shrinking the search space combinatorially.
3. **Per-region enumeration** — all valid mine assignments per region are
   enumerated with constraint propagation, processing clues in an order that
   minimizes the active boundary (a treewidth-style heuristic).
4. **Exact global probabilities** — per-region mine-count frequency distributions
   are convolved, weighted by the combinatorial number of ways to place remaining
   mines on non-frontier tiles (`C(n, k)`), yielding exact per-tile probabilities
   across the full solution ensemble.
5. **Move selection** (`strategy.py`, `progress.py`) — when no move is provably
   safe, the "secondary safety" strategy (`SecSafety`) evaluates each candidate
   click by one-step lookahead: the probability-weighted safety of the board
   after the reveal, plus expected tiles cleared (progress). 
   
6. **50/50 detection** - forced two-tile 50/50s are detected and resolved immediately, because they may provide useful info for the rest of the board (`fifty_fifty_detection.py`); additionally, evaluation scores of tiles that would create 50/50s are slightly boosted.

Performance comes from caching: regions are memoized across moves and their
enumerated possibilities reformatted in place rather than recomputed.

### Monte Carlo move evaluation

`config_sim.py` can also sample boards uniformly from the exact solution
ensemble and play out candidate moves in parallel
across processes (`ProcessPoolExecutor`).  

## Features

- **Playable game** (pygame): three-panel UI, difficulty presets + custom boards,
  scrollable large boards, settings screen
- **Live probability overlays**: exact mine probability rendered on every hidden tile
- **Solver assist**: suggest safest move / auto-flag certain mines in-game
- **Replays**: every game is event-sourced (seed + mine positions + timed actions);
  replay with seek, pause, and analysis tools
- **Benchmark harness**: seeded batch runner with win-rate, timing, and timeout
  stats; per-seed reproducibility for debugging losses

## Setup

Requires **Python 3.11 or newer**. Verified on Python 3.12 (macOS, arm64).

Run the setup script once to create the virtual environment and install dependencies:

```bash
./setup.sh
```

`setup.sh` will automatically use `python3.12` or `python3.11` if available, falling back to `python3` otherwise. If the fallback is too old, you'll get a clear error.

Or do it manually with Python 3.11+:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

On Windows, use `.venv\Scripts\python.exe` and `.venv\Scripts\pip.exe` instead.

## Run

Use the wrapper scripts to run the project with the correct virtual environment:

```bash
./run.sh              # play the game (pygame UI)
./play.sh             # headless benchmark: 100 seeded expert games, prints win rate
pytest                # unit tests
```

All command-line flags are passed through, e.g.:

```bash
./play.sh -s -7778276623403 --no-parallel
```

If you prefer not to use the wrapper scripts, run the venv Python directly:

```bash
.venv/bin/python main.py
.venv/bin/python player.py
```

### Controls

| Input | Action |
|---|---|
| left click / right click | reveal / flag |
| `n` | new game |
| `w` | solve one step |
| `e` | suggest safest move |
| `t` | autoplay |
| `i` | toggle probability overlay |
| `b` | run simulation |
| `k` / `l` | save / load board |
| mouse or trackpad scroll | pan large boards |

## Project structure

```
solver.py                exact-probability CSP engine (regions, enumeration, convolution)
probability.py           opening probabilities, non-frontier probabilities, distributions
strategy.py              move-selection strategies (SafestTile → SecSafety lookahead)
progress.py              one-step-lookahead evaluation of candidate clicks
fifty_fifty_detection.py forced 50/50 and 50/50-influence detection
config_sim.py            uniform sampler over the exact solution ensemble + parallel sims
player.py                autoplay + seeded benchmark harness
sprites.py               board/tile state, reveal/flag mechanics
UI.py, screens/          pygame interface, settings screen
replay_manager.py        event-sourced replay recording/playback
test_config_sim.py       pytest suite (sampler helpers)
```


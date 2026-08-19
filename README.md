# Minesweeper — Exact-Probability Solver & Game

A Minesweeper solver that computes exact per-tile mine probabilities and plays expert difficulty (30×16, 99 mines) at a ~40% win rate.
Includes the full game (pygame), live probability overlays, a replay system, and a
seeded benchmark harness.

## Benchmarks

Standard expert board (30×16, 99 mines), first-click-safe, solver knows the total
mine count. Every game is seeded and fully replayable. These results were achieved with a 10-core 2021 Macbook Pro M1 Max.

| Strategy  | Games | Win rate | Errors | Timeouts | Avg time/game |
|-----------|------:|---------:|-------:|---------:|--------------:|
| SecSafety | 1,000 | 40.8% | 0 | 0 | 0.11s |
| SecSafety |   100 | 47.0% | 0 | 0 | 0.08s |

Reproduce the 100-game row with `python player.py` (seed `-7778276623403`,
`SecSafety` strategy, 100 games — the defaults in `player.py:main()`).

Actual output:

```console
$ python player.py -s -7778276623403 --no-parallel

--- Statistics Summary ---
Strategy used: SecSafety
Total games: 1000
Total time: 85.05231595039368
Wins: 408
Losses: 592
Errors: 0
Winrate: 40.80%
Average time per game: 0.08 seconds
Average time per win: 0.10 seconds
timeouts: 0
```

Result with multithreading enabled:
```console
$ python player.py -s -7778276623403
--- Statistics Summary ---
Strategy used: SecSafety
Total games: 1000
Total time: 11.28255319595337
Wins: 408
Losses: 592
Errors: 0
Winrate: 40.80%
Average time per game: 0.10 seconds
Average time per win: 0.13 seconds
timeouts: 0
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

Verified on Python 3.12 (macOS, arm64).

```bash
python3.11.8 -m venv .venv
source .venv/bin/activate
pip install pygame-ce numpy scipy line_profiler pytest pygame_gui
```

## Run

```bash
python main.py        # play the game (pygame UI)
python player.py      # headless benchmark: 100 seeded expert games, prints win rate
pytest                # unit tests
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


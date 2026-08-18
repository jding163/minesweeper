# Minesweeper — Exact-Probability Solver & Game

A Minesweeper AI that computes **exact** per-tile mine probabilities — not Monte Carlo
estimates — and plays expert difficulty (30×16, 99 mines) at a **~41% win rate**.
Includes the full game (pygame), live probability overlays, a replay system, and a
seeded benchmark harness.

## Benchmarks

Standard expert board (30×16, 99 mines), first-click-safe, solver knows the total
mine count. Every game is seeded and fully replayable.

| Strategy  | Games | Win rate | Errors | Timeouts | Avg time/game |
|-----------|------:|---------:|-------:|---------:|--------------:|
| SecSafety | 1,000 | **40.8%** | 0 | 0 | 0.07s |
| SecSafety |   100 | 47.0% | 0 | 0 | 0.06s |

Reproduce the 100-game row with `python player.py` (seed `-7778276623403`,
`SecSafety` strategy, 100 games — the defaults in `player.py:main()`).

Actual output:

```console
$ python player.py

--- Statistics Summary ---
Strategy used: SecSafety
Total games: 100
Total time: 6.361629009246826
Wins: 47
Losses: 53
Errors: 0
Winrate: 47.00%
Average time per game: 0.06 seconds
Average time per win: 0.09 seconds
timeouts: 0
```

Per-move cost is sub-millisecond in the common case; a full expert game completes in
roughly 60–70ms of solver time. For context, published constraint-based solvers
typically report win rates in the 30–40% range on expert under these rules, so exact
(non-sampled) probabilities put this in a competitive range.

<!-- TODO: add a short GIF of the UI: start expert game, let the solver play with
     probability overlays visible, then a replay seek. ~15-20s max. -->
<!-- ![solver playing expert with probability overlays](docs/demo.gif) -->

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
   across the full solution ensemble (often >10⁹⁹ configurations).
5. **Move selection** (`strategy.py`, `progress.py`) — when no move is provably
   safe, the "secondary safety" strategy (`SecSafety`) evaluates each candidate
   click by one-step lookahead: the probability-weighted safety of the board
   *after* the reveal, plus expected tiles cleared, with early termination against
   the current best. Forced two-tile 50/50s and tiles that would *create* 50/50s
   are detected specially (`fifty_fifty_detection.py`) — dying to such a tile
   implies a coin-flip was unavoidable anyway.

Performance comes from caching: regions are memoized across moves and their
enumerated possibilities reformatted in place rather than recomputed (3× speedup
in the probability pass, 1.5× overall).

### Monte Carlo move evaluation

`config_sim.py` can also *sample* boards uniformly from the exact solution
ensemble (suffix-convolution weighting) and play out candidate moves in parallel
across processes (`ProcessPoolExecutor`). `validate_sampler()` verifies the sampler
empirically against the solver's exact probabilities (max error tracked per tile).
Sampling is used for evaluation experiments only — never for the headline
probabilities.

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
python3.12 -m venv .venv
source .venv/bin/activate
pip install pygame-ce numpy scipy line_profiler pytest pygame_gui
```

Install `pygame-ce`, **not** upstream `pygame` — `pygame_gui` requires symbols
(`DIRECTION_LTR`) that only exist in the CE fork. The two packages share the
`pygame` namespace and overwrite each other if both are installed.

> **Note:** `requirements.txt` currently pins *both* `pygame` and `pygame-ce`, so
> `pip install -r requirements.txt` produces a broken environment depending on
> install order. Use the explicit command above until that line is removed.

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

## Tests

```bash
pytest                             # config_sim unit tests
python test_reveal_correctness.py  # standalone differential check
```

`test_reveal_correctness.py` compares the optimized iterative `reveal_tiles`
against a reference copy of the original recursive implementation across several
board sizes and seeds. It currently runs as a script rather than as part of the
pytest suite.

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
test_reveal_correctness.py  standalone reveal-correctness differential check
```

## Roadmap

- [ ] Wire `test_reveal_correctness.py` into the pytest suite
- [ ] Fix the `pygame`/`pygame-ce` conflict in `requirements.txt`
- [ ] Deeper lookahead (2+ plies) for endgame play
- [ ] Opening-book optimization for the first-click region
- [ ] Publish full benchmark data across strategies and difficulties
- [ ] Package solver as a standalone library (no pygame dependency)

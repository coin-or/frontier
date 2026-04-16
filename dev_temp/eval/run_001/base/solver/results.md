# Solver Results Overview

## Run Configuration
- Algorithm: NSGA-III (pymoo)
- Population: 200, Generations: 400
- Reference directions: 91 (Das-Dennis, 3 objectives, 12 partitions)
- Seed: 42
- ETF universe: 30 tickers
- Solve time: 4.9s

## Solution Counts
| Metric | Count |
|--------|-------|
| Raw Pareto solutions | 45 |
| Constraint violations filtered | 7 |
| Valid solutions (post-filter) | 38 |
| Unique solutions (post-dedup, d < 0.1) | 38 |

## Objective Ranges (Pareto frontier)
| Objective | Min | Max | Spread |
|-----------|-----|-----|--------|
| Expected Return (%) | 2.22 | 18.33 | 16.11 |
| Volatility (%) | 4.24 | 15.91 | 11.67 |
| Dividend Yield (%) | 0.79 | 5.10 | 4.31 |

## Pareto Set Observations
- 38 solutions span the three-objective frontier across return, volatility, and yield.
- The frontier is well-spread: return covers an 8x range (2.22% to 18.33%), volatility spans nearly 4x (4.24% to 15.91%), and yield varies by 6x (0.79% to 5.10%).
- Holdings range from 4 to 10 per portfolio, with most solutions clustering at 4-7.
- HYG (high-yield corporate bonds) and VGSH (short-term treasuries) appear in the majority of solutions, serving as yield and stability anchors respectively.
- VGT (tech sector) and VDE (energy) dominate the high-return end of the frontier.

## Data Reference
Full solution data in `results.json`. Metadata in `metadata.json`.

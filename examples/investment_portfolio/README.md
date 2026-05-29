# Portfolio optimization

Loadable Frontier example — a 30-ETF portfolio balancing return, volatility (via covariance), and yield.

- **`problem.json`** — the definition: 3 objectives (Return / Volatility / Yield), proportional approach, constraints (single-fund ≤30%, ≤3 per sector, volatility ≤20%), and `rate_cuts` / `recession` scenarios.
- **`scores.json`** — the 30 funds, their per-objective scores, and the covariance matrix (the `Volatility` interaction matrix).

Load both into Frontier (`model create` → `model update` with the objectives/options/scores/constraints/interaction_matrices/scenarios → `solve run` → `explore`), or paste this to an agent connected to Frontier:

> Build a diversified ETF portfolio from the funds in scores.json — maximize return, minimize volatility (use the covariance matrix, not weighted-average vol), maximize yield. Constraints: no fund over 30%, ≤3 per sector, volatility under 20%. Show the tradeoffs across base and a recession where US-equity correlations rise 50% — the range of non-dominated portfolios and where the knees are, not one "best."

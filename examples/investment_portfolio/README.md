# Investment portfolio

Loadable Frontier example — a 30-ETF portfolio balancing return, volatility (via covariance), and yield.

- **`problem.json`** — the definition: 3 objectives (Return / Volatility / Yield), proportional approach, constraints (single-fund ≤30%, ≤3 per sector, volatility ≤20%), and three macro scenarios (`recession`, `inflation`, `rate_cuts`).
- **`scores.json`** — the 30 funds, their per-objective scores, and the covariance matrix (the `Volatility` interaction matrix).

Load both into Frontier (`model create` → `model update` with the objectives/options/scores/constraints/interaction_matrices/scenarios → `solve run` → `explore`), or paste this to an agent connected to Frontier:

> Build a diversified ETF portfolio from the funds in scores.json — maximize return, minimize volatility (use the covariance matrix, not weighted-average vol), maximize yield. Constraints: no fund over 30%, ≤3 per sector, volatility under 20%. Show the tradeoffs across base and the macro scenarios — recession (US-equity correlations rise 50%), inflation, and rate cuts — the range of non-dominated portfolios and where the knees are, not one "best."

## Explainability — shadow prices & near-misses

Solve this problem with an **exact** continuous backend and Frontier surfaces solver-exact duals — the *why* behind a portfolio, not just the *what*:

```
solve  solver="highs" exact=true     # exact mean-variance QP per frontier point (CPU; solver="cuopt" on GPU)
explore sensitivity                   # shadow prices + reduced costs, tagged source=solver_exact
```

For the balanced portfolio on this 30-ETF frontier, that returns (abridged, real output):

- **Where to invest** — constraint shadow prices, the marginal objective change per unit a binding limit is relaxed:
  - `Yield` floor → **+55**, `Return` floor → **+14** (risk units). Yield is the more expensive axis to push *here*.
  - `frontier_shadow_price_trend` for `Return`: **18.5 at the high-return end → 2.2 at the low-return end** — return gets steadily more expensive the more you demand of it. Diminishing returns, made exact (not a slope fitted across nearby points).
- **Near-misses** — `reduced_cost` of unheld funds, how far each must improve to enter: `VEA` (60.5) is the closest miss, then `VTV` (66.6), `VNQI` (71.1)… A small improvement in VEA's return or correlation would pull it into the optimal mix.
- **Capped** — `HYG` sits at its 30% single-fund cap with reduced cost **−75**: the cap is binding; it would take more if the cap allowed.

**Scope.** Exact for the **continuous** mean-variance (QP) shape. The ≤3-per-sector caps pin 15 of the 30 funds out of the support — those are *structurally excluded* (held out by a cap, not by their own score), so they're filtered from the near-miss list rather than mislabeled as near-misses. Integer/MILP selection problems carry no exact duals; there `explore sensitivity` falls back to the frontier-inferred `binding_analysis`, tagged `source=frontier_inferred`.

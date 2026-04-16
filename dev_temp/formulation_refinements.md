# ETF Portfolio Demo — Formulation Refinements

Working notes on issues found during evaluation + actionable fixes.

---

## Formulation Refinements (Problem Design)

### 1. Max Single-Position Concentration Limit

| Field | Detail |
|-------|--------|
| **Change** | Add `max_weight` constraint, e.g. no single ETF > 30% |
| **Why** | HYG at 95-97% and VGSH at near-100% are unrealistic. Real portfolios cap concentration for risk/compliance reasons. |
| **Expected impact** | Forces diversification, equity ETFs get a foothold, Income/Balanced strategies become meaningfully different from each other. Probably the highest-leverage single fix. |

**Suggested values:** 30% for aggressive/income, 25% for balanced, 20% for conservative.

---

### 2. Correlation-Aware Volatility

| Field | Detail |
|-------|--------|
| **Change** | Replace weighted-average vol with proper portfolio variance: `σ_p = sqrt(w^T Σ w)` using a covariance matrix |
| **Why** | Linear-average vol gives no diversification credit. A 50/50 stock+bond portfolio should have lower vol than either alone. Under current formulation, the optimizer has zero incentive to diversify by asset class. |
| **Expected impact** | Equity ETFs become attractive because they diversify against bond/commodity positions. Balanced portfolios look genuinely different from income portfolios. |

**If full covariance is too complex for the demo:** at minimum document this as a known simplification in the problem description, and use a simple correlation penalty (e.g., vol = weighted_avg_vol * (1 - 0.3 * herfindahl_index)) as a proxy for diversification benefit.

---

### 3. Minimum Equity Exposure Constraint

| Field | Detail |
|-------|--------|
| **Change** | Add a group-level floor constraint: e.g., sum of equity ETF weights >= 20% for balanced, >= 10% for income |
| **Why** | 11 equity ETFs available, zero appear above 1% in any strategy. This makes the demo look like a bond/commodity optimizer, not a multi-asset portfolio tool. |
| **Expected impact** | Forces equity presence, makes strategies visually/intuitively distinct, and showcases the full ETF universe. |

**Implementation note:** Tag ETFs by asset class in the problem data (equity, fixed_income, commodity, alternatives). Then add group constraints per scenario type.

---

### 4. Widen Scenario Score Adjustments

| Field | Detail |
|-------|--------|
| **Change** | Use more aggressive multipliers on objective scores, or add scenario-specific hard constraints |
| **Why** | Current adjustments produce nearly identical frontiers (return range: 20.32-20.42% max, 1.96-2.09% min). Scenarios rotate in/out 1% satellites but don't change the dominant positions. |
| **Expected impact** | Genuinely different Pareto frontiers per scenario — the whole point of the scenario feature. |

**Options:**

| Approach | Example | Tradeoff |
|----------|---------|----------|
| Larger multipliers | 2x-5x on yield score in income scenario | Simple, but can cause instability |
| Scenario constraints | Growth scenario requires >= 40% equity | More predictable, cleaner |
| Exclude asset classes | Income scenario excludes commodity ETFs | Aggressive but creates clear differentiation |

Recommended: combine moderate multipliers (2x) with one scenario-specific group constraint per scenario type.

---

### 5. Sharpe-Ratio-Like Derived Objective

| Field | Detail |
|-------|--------|
| **Change** | Add a risk-adjusted return metric as a third objective or replace raw return: `risk_adj_return = return / vol` |
| **Why** | Raw return + raw vol as separate objectives lets the optimizer pile into high-yield/high-vol without penalty to return. A Sharpe-like term captures the tradeoff in a single dimension and produces more intuitive "efficient" portfolios. |
| **Expected impact** | Balanced and income portfolios look qualitatively different on the frontier. Users can see a "best risk/reward" region clearly. |

**Note:** With linear-average vol (issue #2), Sharpe will still be distorted. Fix #2 first or simultaneously.

---

## Secondary Issues (Output/Engine)

These are lower priority but affect demo quality.

| Issue | Recommendation |
|-------|---------------|
| **Marginal analysis too large** (~166K chars) | Truncate to top-10 ETFs by marginal impact; add `summary_only` flag |
| **Robustness metric too broad** (28/30 "robust") | Change to frequency-based: robust = appears in >50% of solutions, not just any |
| **Solve overflow** (329 solutions vs 100 requested) | Add hard cap in engine; deduplicate by objective distance threshold |
| **Balanced selection unstable** | Document the centroid-distance method; consider offering "closest to equal-weight" as an alternative balanced selector |

---

## Priority Order

1. Max single-position limit (easy, immediate visible impact)
2. Widen scenario adjustments + add group constraints (makes scenarios meaningful)
3. Minimum equity exposure (showcases full universe)
4. Correlation-aware vol (most realistic, most complex)
5. Sharpe derived objective (nice-to-have, depends on #4)

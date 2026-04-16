# Curated Strategies

## Growth
Maximizes expected return. Highest return on the frontier at the cost of maximum volatility and minimal yield.

| Metric | Value |
|--------|-------|
| Return | 18.33% |
| Volatility | 15.91% |
| Yield | 1.22% |

**Allocations (4 holdings):**
| Ticker | Weight | Notes |
|--------|--------|-------|
| VGT | 31% | **CONSTRAINT VIOLATION: exceeds 30% max** |
| VDE | 30% | At cap |
| GLD | 30% | At cap |
| EWJ | 9% | |

**Binding constraints:** Max allocation cap (30%) binds on VDE and GLD. VGT exceeds it at 31%. Min holdings (4) binds -- portfolio is at the floor.

**Constraint violation:** VGT at 31% violates the max single allocation constraint of 30%. The repair operator caps at 30% (line 116: `x = np.minimum(x, 30.0)`) but post-normalization re-scaling (lines 139-147) can push allocations back above 30% when the iterative convergence loop exits after 10 iterations without fully resolving. The validation filter on line 283 uses a 30.5% tolerance (`max_alloc > 30.5`), so 31% (which rounds from ~30.6-31.4% raw) passes through.

---

## Safety
Minimizes portfolio volatility. Achieves the lowest risk on the frontier with strong yield but modest return.

| Metric | Value |
|--------|-------|
| Return | 3.43% |
| Volatility | 4.24% |
| Yield | 4.39% |

**Allocations (7 holdings):**
| Ticker | Weight | Notes |
|--------|--------|-------|
| VGSH | 29% | Near cap |
| HYG | 29% | Near cap |
| BND | 22% | |
| SCHD | 12% | |
| DBA | 5% | |
| VPU | 2% | |
| EWJ | 1% | At min |

**Binding constraints:** Min holding size (1%) binds on EWJ. No constraint violations.

---

## Income
Maximizes dividend yield. Achieves highest yield on the frontier but accepts high volatility relative to return.

| Metric | Value |
|--------|-------|
| Return | 2.22% |
| Volatility | 7.10% |
| Yield | 5.10% |

**Allocations (5 holdings):**
| Ticker | Weight | Notes |
|--------|--------|-------|
| HYG | 30% | At cap |
| EMB | 30% | At cap |
| VNQI | 22% | |
| VGSH | 13% | |
| EWJ | 5% | |

**Binding constraints:** Max allocation cap (30%) binds on HYG and EMB. No violations.

---

## Balanced
Closest to the ideal point (max return, min vol, max yield) in normalized objective space. Represents the Pareto-optimal compromise.

| Metric | Value |
|--------|-------|
| Return | 9.42% |
| Volatility | 8.31% |
| Yield | 3.99% |

**Allocations (4 holdings):**
| Ticker | Weight | Notes |
|--------|--------|-------|
| HYG | 31% | **CONSTRAINT VIOLATION: exceeds 30% max** |
| DBA | 29% | Near cap |
| VDE | 21% | |
| VGSH | 19% | |

**Binding constraints:** Min holdings (4) binds. HYG at 31% violates the 30% max allocation constraint (same repair operator issue as Growth).

---

## Summary of Constraint Violations in Curated Set

| Strategy | Ticker | Weight | Max Allowed | Violation |
|----------|--------|--------|-------------|-----------|
| Growth | VGT | 31% | 30% | +1% |
| Balanced | HYG | 31% | 30% | +1% |

Both violations stem from the same root cause: the repair operator's iterative normalization loop can push weights above the 30% cap, and the validation filter's 0.5% tolerance (line 283) allows these through.

# Pyomo ETF Portfolio Optimization -- Epsilon-Constraint Method

**Date:** 2026-04-12
**Solver:** GLPK 5.0 via Pyomo 6.10.0
**Method:** Epsilon-constraint on 3-objective MILP

---

## Problem Formulation

**Objectives (3):**
1. Maximize Expected Return (ann_return_5yr_pct)
2. Minimize Volatility (ann_volatility_5yr_pct)
3. Maximize Dividend Yield (dividend_yield_pct)

**Decision Variables:**
- `x[i]` -- integer % allocation for each of 25 ETFs (0-100)
- `y[i]` -- binary indicator (1 if ETF is held)

**Constraints:**
- Allocations sum to 100%
- Minimum 1% if held (link between x and y)
- Cardinality: 4-12 holdings
- Volatility cap: weighted average <= 20%
- Max 2 sector ETFs (VGT, VHT, VDE, VFH)
- Max 2 alternative ETFs (VNQ, GLD, GSG)

---

## Setup Effort & Solver Requirements

| Step | Effort |
|------|--------|
| Install Pyomo | `pip install pyomo` -- 1 command |
| Install GLPK solver | `brew install glpk` -- 1 command, but must be separately installed and discoverable on PATH |
| Model formulation | ~120 lines of Python defining variables, constraints, objective, and epsilon logic |
| Epsilon sweep design | Manual selection of grid points across 3 objective ranges; 75 solve calls across 3 sweeps |
| Pareto filtering | Custom dominance-check code required (Pyomo does not do this) |
| Curation | Manual post-processing to select representative strategies |
| **Total script** | **~220 lines of Python** |
| **Total wall time** | **~1.0 seconds** (75 MILP solves) |

**Key friction points:**
- Pyomo requires a separate solver binary (GLPK, CBC, Gurobi, etc.) -- it has no built-in solver
- The solver must be on the system PATH or its path specified explicitly in code
- Multi-objective optimization is not natively supported; the epsilon-constraint method must be hand-coded
- The user must decide how to discretize the epsilon grid (how many steps, which ranges)
- Pareto dominance filtering must be implemented manually
- No built-in way to interpret or curate solutions; raw output is a list of allocation vectors

---

## Results Summary

| Metric | Value |
|--------|-------|
| Total MILP solves | 75 |
| Unique feasible solutions | 41 |
| Pareto-optimal solutions | 41 (all unique solutions were non-dominated) |
| Solve time | 1.0 seconds |
| Return range | 1.79% -- 20.64% |
| Volatility range | 2.33% -- 19.96% |
| Dividend range | 0.90% -- 6.67% |

---

## Full Pareto Frontier (41 Solutions)

| # | Return | Vol | Div Yield | Holdings | Top Allocations |
|---|--------|-----|-----------|----------|-----------------|
| 1 | 20.64% | 19.96% | 0.90% | 4 | GLD:61%, VDE:37%, GSG:1%, VGT:1% |
| 2 | 18.64% | 16.36% | 0.90% | 4 | GLD:79%, VDE:11%, HYG:9%, VXUS:1% |
| 3 | 16.69% | 13.78% | 0.94% | 4 | GLD:81%, VGSH:11%, HYG:7%, EMB:1% |
| 4 | 16.18% | 16.37% | 2.35% | 4 | GLD:49%, HYG:26%, VDE:24%, VYM:1% |
| 5 | 15.96% | 15.97% | 2.34% | 4 | GLD:51%, HYG:27%, VDE:21%, VYM:1% |
| 6 | 15.96% | 16.43% | 2.50% | 4 | GLD:46%, HYG:27%, VDE:26%, TIP:1% |
| 7 | 15.95% | 12.98% | 0.91% | 4 | GLD:77%, VGSH:20%, HYG:2%, VYM:1% |
| 8 | 15.94% | 13.78% | 1.53% | 5 | GLD:75%, HYG:20%, VGSH:3%, TIP:1%, VYM:1% |
| 9 | 14.69% | 13.79% | 2.34% | 4 | GLD:61%, HYG:33%, VDE:5%, VOO:1% |
| 10 | 13.70% | 16.41% | 3.79% | 4 | HYG:43%, VDE:37%, GLD:19%, VOO:1% |
| 11 | 13.54% | 11.14% | 1.32% | 4 | GLD:64%, VGSH:34%, VOO:1%, BNDX:1% |
| 12 | 12.30% | 11.14% | 2.42% | 4 | GLD:55%, HYG:24%, VGSH:20%, TIP:1% |
| 13 | 12.17% | 13.70% | 3.79% | 4 | HYG:50%, GLD:32%, VDE:17%, VYM:1% |
| 14 | 11.23% | 11.13% | 3.28% | 4 | GLD:47%, HYG:43%, VGSH:9%, TIP:1% |
| 15 | 11.23% | 15.58% | 4.93% | 4 | HYG:57%, VDE:41%, TIP:1%, EMB:1% |
| 16 | 11.22% | 9.38% | 1.85% | 4 | GLD:51%, VGSH:47%, VOO:1%, HYG:1% |
| 17 | 11.22% | 10.00% | 2.35% | 4 | GLD:50%, VGSH:33%, HYG:16%, BNDX:1% |
| 18 | 11.22% | 12.08% | 3.80% | 4 | HYG:54%, GLD:39%, VDE:6%, VGSH:1% |
| 19 | 11.22% | 13.78% | 4.37% | 4 | HYG:56%, VDE:23%, GLD:20%, TIP:1% |
| 20 | 10.57% | 11.13% | 3.79% | 4 | HYG:54%, GLD:41%, VGSH:4%, VDE:1% |
| 21 | 10.02% | 8.47% | 2.12% | 4 | VGSH:53%, GLD:45%, TIP:1%, HYG:1% |
| 22 | 9.96% | 14.26% | 5.23% | 4 | HYG:64%, VDE:34%, TIP:1%, EMB:1% |
| 23 | 9.70% | 8.49% | 2.36% | 4 | VGSH:50%, GLD:42%, HYG:7%, VOO:1% |
| 24 | 9.69% | 13.74% | 5.23% | 4 | HYG:67%, VDE:30%, GLD:2%, VOO:1% |
| 25 | 8.18% | 11.14% | 5.24% | 4 | HYG:74%, GLD:14%, VDE:11%, VOO:1% |
| 26 | 7.95% | 8.50% | 3.79% | 5 | HYG:38%, VGSH:31%, GLD:29%, TIP:1%, VYM:1% |
| 27 | 6.53% | 5.85% | 2.80% | 4 | VGSH:72%, GLD:26%, TIP:1%, BNDX:1% |
| 28 | 6.53% | 5.86% | 2.81% | 4 | VGSH:73%, GLD:25%, HYG:1%, GSG:1% |
| 29 | 6.52% | 5.84% | 2.78% | 4 | VGSH:72%, GLD:26%, BND:1%, BNDX:1% |
| 30 | 6.52% | 7.04% | 3.80% | 4 | VGSH:47%, HYG:30%, GLD:22%, VYM:1% |
| 31 | 6.52% | 10.70% | 6.04% | 4 | HYG:83%, VDE:15%, TIP:1%, EMB:1% |
| 32 | 6.51% | 8.49% | 4.97% | 4 | HYG:65%, VGSH:16%, GLD:18%, VOO:1% |
| 33 | 6.51% | 8.83% | 5.23% | 4 | HYG:71%, GLD:18%, VGSH:8%, TIP:3% |
| 34 | 6.17% | 8.48% | 5.24% | 4 | HYG:70%, GLD:15%, VGSH:14%, VDE:1% |
| 35 | 5.36% | 5.82% | 3.79% | 4 | VGSH:60%, HYG:22%, GLD:17%, TIP:1% |
| 36 | 3.76% | 7.91% | 6.67% | 4 | HYG:97%, LQD:1%, TIP:1%, EMB:1% |
| 37 | 3.55% | 5.84% | 5.24% | 5 | HYG:54%, VGSH:41%, GLD:3%, TIP:1%, VYM:1% |
| 38 | 3.05% | 5.85% | 5.63% | 4 | HYG:62%, VGSH:35%, TIP:2%, BND:1% |
| 39 | 2.73% | 5.09% | 5.23% | 4 | VGSH:48%, HYG:47%, TIP:4%, BND:1% |
| 40 | 1.82% | 2.34% | 3.79% | 4 | VGSH:97%, BND:1%, HYG:1%, BNDX:1% |
| 41 | 1.79% | 2.33% | 3.78% | 4 | VGSH:97%, BND:1%, TIP:1%, BNDX:1% |

---

## Curated Strategies

### 1. Growth-Oriented (Solution #1)

| Metric | Value |
|--------|-------|
| Expected Return | 20.64% |
| Volatility | 19.96% |
| Dividend Yield | 0.90% |
| Holdings | 4 |

| ETF | Allocation | Category |
|-----|-----------|----------|
| GLD | 61% | Gold |
| VDE | 37% | Energy |
| GSG | 1% | Commodities |
| VGT | 1% | Technology |

Maximizes return at the cost of near-zero dividend income and near-cap volatility. Heavily concentrated in gold and energy -- the two highest-returning ETFs over the 5-year period. The 1% VGT and GSG positions exist only to satisfy the 4-holding minimum.

### 2. Balanced (Solution #14)

| Metric | Value |
|--------|-------|
| Expected Return | 11.23% |
| Volatility | 11.13% |
| Dividend Yield | 3.28% |
| Holdings | 4 |

| ETF | Allocation | Category |
|-----|-----------|----------|
| GLD | 47% | Gold |
| HYG | 43% | High Yield Bond |
| VGSH | 9% | Short-Term Treasury |
| TIP | 1% | TIPS |

Moderate return with roughly half the volatility of the growth portfolio and meaningful dividend yield. The gold/high-yield-bond pairing provides return with income, and the short-term treasury anchor reduces overall vol.

### 3. Income-Oriented (Solution #36)

| Metric | Value |
|--------|-------|
| Expected Return | 3.76% |
| Volatility | 7.91% |
| Dividend Yield | 6.67% |
| Holdings | 4 |

| ETF | Allocation | Category |
|-----|-----------|----------|
| HYG | 97% | High Yield Bond |
| LQD | 1% | IG Corporate Bond |
| TIP | 1% | TIPS |
| EMB | 1% | EM Bond |

Maximum dividend yield at 6.67%. Essentially a single-ETF portfolio in high yield bonds with token diversifiers. Sacrifices almost all capital appreciation for income.

### 4. Safety / Conservative (Solution #41)

| Metric | Value |
|--------|-------|
| Expected Return | 1.79% |
| Volatility | 2.33% |
| Dividend Yield | 3.78% |
| Holdings | 4 |

| ETF | Allocation | Category |
|-----|-----------|----------|
| VGSH | 97% | Short-Term Treasury |
| BND | 1% | US Aggregate Bond |
| TIP | 1% | TIPS |
| BNDX | 1% | Intl Bond |

Minimum volatility at 2.33%. Almost entirely short-term treasuries. Very low return but very stable, with a decent yield from the short-duration bonds.

---

## Commentary on Traditional Optimization Approach

### What worked well
- **Speed:** 75 MILP solves completed in ~1 second. GLPK handles this problem size easily.
- **Constraint enforcement:** All solutions rigorously satisfy every constraint -- no heuristic violations.
- **Exactness:** Integer % allocations are solved exactly (no rounding from continuous solutions).

### What was difficult
- **No native multi-objective support:** Pyomo solves single-objective problems. The epsilon-constraint method must be hand-coded, including grid design, sweep logic, and Pareto filtering.
- **Grid design is ad hoc:** The quality of the Pareto frontier depends heavily on how many epsilon levels you choose and where you place them. Too few and you miss interesting tradeoffs; too many and you waste solve time on infeasible or dominated points.
- **Installation friction:** Pyomo is a modeling layer but requires a separate solver binary. Getting GLPK on PATH can be non-trivial depending on the user's system.
- **Raw output is opaque:** The solver returns allocation vectors with no narrative, no strategy labels, no tradeoff commentary. Converting 41 raw solutions into actionable strategies requires significant manual effort.
- **Degenerate solutions:** Many solutions cluster around the same 4-5 ETFs (GLD, HYG, VGSH, VDE) because the linear weighted-average objectives strongly favor corner solutions. The 1% token positions are artifacts of the 4-holding minimum cardinality constraint.
- **No interactivity:** There is no way to ask "what if I care more about dividends?" without re-running with different epsilon bounds.

### Observations on solution quality
- The optimizer heavily favors GLD (20% 5yr return) and VDE (22% 5yr return) for growth, and HYG (6.7% yield) for income. These are the dominant ETFs on their respective objective axes.
- Diversified equity portfolios (mixing VOO, VTV, VUG, international) rarely appear because the linear objective formulation doesn't value diversification -- it only sees weighted average metrics.
- Most solutions have exactly 4 holdings (the minimum), with 1% token positions. The optimizer has no incentive to hold more ETFs because diversification doesn't improve any single objective.
- The model uses **weighted-average volatility** as a simplification. True portfolio volatility would require a covariance matrix and quadratic programming (QCQP), which GLPK cannot handle -- you'd need a solver like Gurobi or CPLEX.

### Lines of code comparison
| Component | Lines |
|-----------|-------|
| Data loading | 15 |
| Model construction (build_model) | 55 |
| Solve + extract | 20 |
| Epsilon sweep logic | 40 |
| Pareto filtering | 15 |
| Output formatting | 30 |
| Curation logic | 25 |
| **Total** | **~220** |

---

## Script Source

The complete Pyomo script is at: `dev_temp/pyomo_etf_optimizer.py`

Key dependencies:
- Python 3.11+
- `pyomo` (pip install)
- `glpk` solver binary (brew install glpk, or apt-get install glpk-utils)

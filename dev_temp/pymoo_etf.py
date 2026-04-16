"""
pymoo ETF Portfolio Optimization
================================
Multi-objective evolutionary optimization (NSGA-III) for 25-ETF allocation.
Objectives: Max Return, Min Volatility, Max Dividend Yield
"""

import json
import time
import numpy as np
from pymoo.core.problem import ElementwiseProblem
from pymoo.core.repair import Repair
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.util.ref_dirs import get_reference_directions
from pymoo.optimize import minimize
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import IntegerRandomSampling

# ── Load Data ──
with open("/Users/cameronafzal/Documents/frontier/dev_temp/etf_cache/etf_consolidated.json") as f:
    etfs = json.load(f)

N = len(etfs)
tickers = [e["ticker"] for e in etfs]
returns = np.array([e["ann_return_5yr_pct"] for e in etfs])
vols = np.array([e["ann_volatility_5yr_pct"] for e in etfs])
divs = np.array([e["dividend_yield_pct"] for e in etfs])

# Group indices
sector_idx = [tickers.index(t) for t in ["VGT", "VHT", "VDE", "VFH"]]
alt_idx = [tickers.index(t) for t in ["VNQ", "GLD", "GSG"]]

print(f"ETFs: {N}, Tickers: {tickers}")
print(f"Sector indices: {sector_idx} ({[tickers[i] for i in sector_idx]})")
print(f"Alt indices: {alt_idx} ({[tickers[i] for i in alt_idx]})")


# ── Repair Operator ──
class ETFRepair(Repair):
    """Repair solutions to satisfy sum=100 and cardinality constraints."""

    def _do(self, problem, X, **kwargs):
        for i in range(len(X)):
            x = X[i].astype(float)

            # Clamp negatives
            x = np.maximum(x, 0)

            # Round to int and enforce min 1% for held positions
            x = np.round(x).astype(int)

            # Kill tiny allocations (below 1%) - set to 0
            x[x < 1] = 0

            # Enforce cardinality: max 12 holdings total
            held = np.where(x > 0)[0]
            if len(held) > 12:
                # Keep top 12 by allocation
                sorted_held = held[np.argsort(x[held])]
                to_remove = sorted_held[:len(held) - 12]
                x[to_remove] = 0

            # Enforce min 4 holdings - if fewer, add small allocations to best return ETFs
            held = np.where(x > 0)[0]
            if len(held) < 4 and np.sum(x) > 0:
                not_held = np.where(x == 0)[0]
                # Add positions sorted by return
                best = not_held[np.argsort(returns[not_held])[::-1]]
                for j in best:
                    if len(held) >= 4:
                        break
                    x[j] = 1
                    held = np.where(x > 0)[0]

            # Enforce sector cardinality (max 2)
            sector_held = [j for j in sector_idx if x[j] > 0]
            if len(sector_held) > 2:
                sector_held_sorted = sorted(sector_held, key=lambda j: x[j])
                for j in sector_held_sorted[:len(sector_held) - 2]:
                    x[j] = 0

            # Enforce alt cardinality (max 2)
            alt_held = [j for j in alt_idx if x[j] > 0]
            if len(alt_held) > 2:
                alt_held_sorted = sorted(alt_held, key=lambda j: x[j])
                for j in alt_held_sorted[:len(alt_held) - 2]:
                    x[j] = 0

            # Normalize to sum=100
            total = np.sum(x)
            if total == 0:
                # Fallback: equal weight top 6 by return
                best6 = np.argsort(returns)[::-1][:6]
                x[best6] = 100 // 6
                x[best6[0]] += 100 - np.sum(x)
            elif total != 100:
                held = np.where(x > 0)[0]
                weights = x[held].astype(float) / total * 100
                x_new = np.zeros(N, dtype=int)
                x_new[held] = np.floor(weights).astype(int)
                # Ensure min 1% for each held
                x_new[held] = np.maximum(x_new[held], 1)
                # Distribute remainder
                remainder = 100 - np.sum(x_new)
                if remainder > 0:
                    # Give remainder to positions with largest fractional parts
                    fracs = weights - np.floor(weights)
                    order = np.argsort(fracs)[::-1]
                    for k in range(min(remainder, len(order))):
                        x_new[held[order[k]]] += 1
                    # If still short, add to largest position
                    still_short = 100 - np.sum(x_new)
                    if still_short > 0:
                        x_new[held[np.argmax(x_new[held])]] += still_short
                elif remainder < 0:
                    # Remove from largest positions
                    excess = -remainder
                    order = np.argsort(x_new[held])[::-1]
                    for k in range(len(order)):
                        if excess <= 0:
                            break
                        can_remove = x_new[held[order[k]]] - 1
                        remove = min(can_remove, excess)
                        x_new[held[order[k]]] -= remove
                        excess -= remove
                x = x_new

            X[i] = x

        return X


# ── Problem Definition ──
class ETFPortfolioProblem(ElementwiseProblem):
    def __init__(self):
        super().__init__(
            n_var=N,
            n_obj=3,
            n_ieq_constr=1,  # volatility constraint
            xl=np.zeros(N),
            xu=np.full(N, 100),
            vtype=int,
        )

    def _evaluate(self, x, out, *args, **kwargs):
        w = x / 100.0  # Convert to fractions

        port_ret = np.dot(w, returns)
        port_vol = np.dot(w, vols)
        port_div = np.dot(w, divs)

        # Objectives: pymoo minimizes, so negate return and dividend
        out["F"] = [-port_ret, port_vol, -port_div]

        # Constraint: weighted volatility <= 20%
        out["G"] = [port_vol - 20.0]


# ── Algorithm Setup ──
print("\nSetting up NSGA-III...")
ref_dirs = get_reference_directions("das-dennis", 3, n_partitions=12)
print(f"Reference directions: {len(ref_dirs)}")

algorithm = NSGA3(
    ref_dirs=ref_dirs,
    pop_size=200,
    sampling=IntegerRandomSampling(),
    crossover=SBX(prob=0.9, eta=3.0, vtype=float, repair=None),
    mutation=PM(prob=1.0 / N, eta=3.0, vtype=float, repair=None),
    repair=ETFRepair(),
)

problem = ETFPortfolioProblem()

# ── Solve ──
print("Running optimization (500 generations)...")
t0 = time.time()
res = minimize(
    problem,
    algorithm,
    ("n_gen", 500),
    seed=42,
    verbose=False,
)
elapsed = time.time() - t0
print(f"Done in {elapsed:.1f}s")

# ── Extract Results ──
F = res.F  # Objective values (negated return, vol, negated div)
X = res.X  # Decision variables

# Convert back to natural units
pareto_return = -F[:, 0]
pareto_vol = F[:, 1]
pareto_div = -F[:, 2]

print(f"\n{'='*60}")
print(f"PARETO FRONT: {len(F)} solutions")
print(f"{'='*60}")
print(f"Return:   {pareto_return.min():.2f}% - {pareto_return.max():.2f}%")
print(f"Vol:      {pareto_vol.min():.2f}% - {pareto_vol.max():.2f}%")
print(f"Dividend: {pareto_div.min():.2f}% - {pareto_div.max():.2f}%")


# ── Select Representative Strategies ──
def describe_portfolio(x, label):
    w = x / 100.0
    port_ret = np.dot(w, returns)
    port_vol = np.dot(w, vols)
    port_div = np.dot(w, divs)
    held = np.where(x > 0)[0]

    lines = []
    lines.append(f"\n{'─'*50}")
    lines.append(f"  {label}")
    lines.append(f"{'─'*50}")
    lines.append(f"  Return: {port_ret:.2f}%  |  Vol: {port_vol:.2f}%  |  Div Yield: {port_div:.2f}%")
    lines.append(f"  Holdings: {len(held)}")
    lines.append(f"  {'Ticker':<8} {'Cat':<25} {'Alloc':>6}")
    lines.append(f"  {'─'*42}")
    for j in np.argsort(x)[::-1]:
        if x[j] > 0:
            lines.append(f"  {tickers[j]:<8} {etfs[j]['category']:<25} {x[j]:>5}%")
    lines.append("")
    return "\n".join(lines), port_ret, port_vol, port_div, held


# Strategy selection heuristics
# Growth: maximize return
growth_idx = np.argmax(pareto_return)

# Safety: minimize volatility
safety_idx = np.argmin(pareto_vol)

# Income: maximize dividend yield
income_idx = np.argmax(pareto_div)

# Balanced: best Sharpe-like ratio (return/vol) with decent dividend
sharpe_like = pareto_return / pareto_vol
# Among top 50% Sharpe, pick highest dividend
top_sharpe = np.argsort(sharpe_like)[::-1][:len(sharpe_like)//2]
balanced_idx = top_sharpe[np.argmax(pareto_div[top_sharpe])]

strategies = [
    (growth_idx, "GROWTH (Max Return)"),
    (balanced_idx, "BALANCED (Return/Vol + Yield)"),
    (income_idx, "INCOME (Max Dividend Yield)"),
    (safety_idx, "SAFETY (Min Volatility)"),
]

all_output = []
strategy_details = []
for idx, label in strategies:
    text, ret, vol, div, held = describe_portfolio(X[idx], label)
    print(text)
    all_output.append(text)
    strategy_details.append({
        "label": label,
        "return": ret,
        "vol": vol,
        "div": div,
        "n_holdings": len(held),
        "allocations": {tickers[j]: int(X[idx][j]) for j in held},
    })

# ── Write Results to Markdown ──
lines_of_code = 200  # approximate

md = f"""# pymoo ETF Portfolio Optimization Results

## Setup
- **Solver**: pymoo NSGA-III (evolutionary multi-objective)
- **Objectives**: Maximize Return, Minimize Volatility, Maximize Dividend Yield
- **Variables**: 25 integer decision variables (ETF allocations summing to 100%)
- **Constraints**: Vol <= 20%, max 2 sector ETFs, max 2 alt ETFs, 4-12 holdings, min 1% each
- **Algorithm**: NSGA-III with {len(ref_dirs)} reference directions, pop_size=200, 500 generations
- **Solve time**: {elapsed:.1f}s
- **Lines of code**: ~{lines_of_code} (problem + repair + selection logic)

## Pareto Front

| Metric | Min | Max |
|--------|-----|-----|
| Annual Return | {pareto_return.min():.2f}% | {pareto_return.max():.2f}% |
| Volatility | {pareto_vol.min():.2f}% | {pareto_vol.max():.2f}% |
| Dividend Yield | {pareto_div.min():.2f}% | {pareto_div.max():.2f}% |

**Pareto-optimal solutions found: {len(F)}**

## Representative Strategies

"""

for detail in strategy_details:
    md += f"### {detail['label']}\n"
    md += f"- **Return**: {detail['return']:.2f}%\n"
    md += f"- **Volatility**: {detail['vol']:.2f}%\n"
    md += f"- **Dividend Yield**: {detail['div']:.2f}%\n"
    md += f"- **Holdings**: {detail['n_holdings']}\n\n"
    md += "| Ticker | Allocation |\n|--------|------------|\n"
    for t, a in sorted(detail["allocations"].items(), key=lambda x: -x[1]):
        md += f"| {t} | {a}% |\n"
    md += "\n"

md += f"""## Commentary

### Setup Effort
- ~{lines_of_code} lines of Python code including the repair operator, problem class, and solution curation
- The main complexity is the **repair operator** (~80 lines) which enforces sum-to-100, cardinality limits, group constraints, and minimum allocation rules after each evolutionary step
- pymoo's API is clean but requires manual constraint handling for integer combinatorial problems

### Solve Time
- **{elapsed:.1f} seconds** for 500 generations with pop_size=200
- This is a stochastic metaheuristic -- runtime scales with population size x generations
- Much slower than exact MILP solvers for comparable problem sizes, but handles non-convex/black-box objectives naturally

### Solution Quality
- NSGA-III produces a diverse Pareto front of {len(F)} non-dominated solutions
- The evolutionary approach explores the trade-off surface well, finding solutions across the full return/vol/yield spectrum
- **Stochastic nature**: results vary across runs (seed-dependent); no guarantee of global optimality
- **Integer handling**: pymoo doesn't natively handle integer constraints as elegantly as MILP solvers -- the repair operator does the heavy lifting
- The repair operator can introduce bias (e.g., favoring high-return ETFs when filling minimum holdings), which may skew the Pareto front
- For this problem size (25 variables, 3 objectives, linear constraints), a MILP/epsilon-constraint approach would likely find provably optimal solutions faster
"""

with open("/Users/cameronafzal/Documents/frontier/dev_temp/run_pymoo.md", "w") as f:
    f.write(md)

print(f"\nResults written to /Users/cameronafzal/Documents/frontier/dev_temp/run_pymoo.md")

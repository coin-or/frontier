"""
30-ETF Portfolio Allocation using pymoo (NSGA-III)
Multi-objective: Max Return, Min Volatility, Max Dividend Yield
Integer percentage allocations summing to 100%.
"""

import json
import time
import numpy as np
from pymoo.core.problem import Problem
from pymoo.core.repair import Repair
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.util.ref_dirs import get_reference_directions
from pymoo.optimize import minimize
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import IntegerRandomSampling

# ── Load ETF data ──────────────────────────────────────────────────────────
with open("/Users/cameronafzal/Documents/frontier/dev_temp/etf_cache/etf_30_consolidated.json") as f:
    etfs = json.load(f)

N = len(etfs)
tickers = [e["ticker"] for e in etfs]
returns = np.array([e["ann_return_5yr_pct"] for e in etfs])
vols = np.array([e["ann_volatility_5yr_pct"] for e in etfs])
yields_ = np.array([e["dividend_yield_pct"] for e in etfs])

# Group indices
SECTOR_TICKERS = {"VGT", "VHT", "VDE", "VFH", "VPU", "VDC", "VOX"}
ALT_TICKERS = {"VNQ", "VNQI", "GLD", "GSG", "DBA", "IGF"}
sector_idx = [i for i, t in enumerate(tickers) if t in SECTOR_TICKERS]
alt_idx = [i for i, t in enumerate(tickers) if t in ALT_TICKERS]


# ── Repair operator ───────────────────────────────────────────────────────
class PortfolioRepair(Repair):
    """Enforce: sum=100, cardinality 4-12, group limits, min 1% if held."""

    def _do(self, problem, X, **kwargs):
        for i in range(len(X)):
            x = X[i].copy().astype(float)
            x = np.maximum(x, 0)

            # Step 1: Enforce group limits (before anything else)
            for group_idx, max_held in [(sector_idx, 3), (alt_idx, 3)]:
                g_held = [j for j in group_idx if x[j] > 0]
                if len(g_held) > max_held:
                    g_sorted = sorted(g_held, key=lambda j: x[j], reverse=True)
                    for j in g_sorted[max_held:]:
                        x[j] = 0

            # Step 2: Determine which positions to keep
            held = np.where(x > 0)[0]

            # Too many holdings: keep top 12
            if len(held) > 12:
                order = held[np.argsort(x[held])]
                for j in order[: len(held) - 12]:
                    x[j] = 0
                held = np.where(x > 0)[0]

            # Too few holdings: add ETFs (pick ones with decent return/vol ratio)
            if len(held) < 4:
                zeros = np.where(x == 0)[0]
                need = 4 - len(held)
                # Pick randomly from available
                activate = np.random.choice(zeros, size=min(need, len(zeros)), replace=False)
                for j in activate:
                    x[j] = 1  # will be scaled
                held = np.where(x > 0)[0]

            # Step 3: Integer allocation with guaranteed min 1% per holding
            n_held = len(held)
            if n_held == 0:
                # Fallback
                top4 = np.argsort(-returns)[:4]
                x[:] = 0
                x[top4] = 25
            else:
                # Reserve 1% per holding, distribute remaining proportionally
                remaining = 100 - n_held  # each gets at least 1%
                if remaining < 0:
                    # Too many holdings for 100%, trim to 12 max
                    order = held[np.argsort(x[held])]
                    while len(held) > 100:
                        x[order[0]] = 0
                        order = order[1:]
                        held = np.where(x > 0)[0]
                    remaining = 100 - len(held)
                    n_held = len(held)

                # Proportional allocation of the remaining budget
                weights = x[held]
                total_w = weights.sum()
                if total_w == 0:
                    # Equal weight
                    alloc = np.full(n_held, remaining / n_held)
                else:
                    alloc = weights / total_w * remaining

                # Floor and distribute remainder via largest-remainder method
                alloc_int = np.floor(alloc).astype(int)
                fracs = alloc - alloc_int
                leftover = remaining - alloc_int.sum()
                if leftover > 0:
                    top_frac_idx = np.argsort(-fracs)[:int(leftover)]
                    for j in top_frac_idx:
                        alloc_int[j] += 1

                # Final allocation: 1 (reserved) + proportional share
                x[:] = 0
                for k, j in enumerate(held):
                    x[j] = 1 + alloc_int[k]

            # Final sum correction
            diff = int(x.sum()) - 100
            if diff != 0:
                held = np.where(x > 0)[0]
                if diff > 0:
                    # Remove from largest positions
                    order = held[np.argsort(-x[held])]
                    for j in order:
                        take = min(diff, int(x[j]) - 1)
                        x[j] -= take
                        diff -= take
                        if diff == 0:
                            break
                else:
                    # Add to largest position
                    biggest = held[np.argmax(x[held])]
                    x[biggest] -= diff

            X[i] = x.astype(int)
        return X


# ── Problem definition ────────────────────────────────────────────────────
class ETFPortfolioProblem(Problem):
    def __init__(self):
        super().__init__(
            n_var=N,
            n_obj=3,
            n_ieq_constr=1,  # volatility <= 20%
            xl=np.zeros(N),
            xu=np.full(N, 100),
            vtype=int,
        )

    def _evaluate(self, X, out, *args, **kwargs):
        W = X / 100.0  # weights as fractions

        ret = W @ returns       # weighted return
        vol = W @ vols          # weighted volatility
        yld = W @ yields_       # weighted yield

        # pymoo minimizes: negate return and yield
        out["F"] = np.column_stack([-ret, vol, -yld])

        # Constraint: vol <= 20  =>  vol - 20 <= 0
        out["G"] = (vol - 20.0).reshape(-1, 1)


# ── Algorithm setup ───────────────────────────────────────────────────────
ref_dirs = get_reference_directions("das-dennis", 3, n_partitions=12)
print(f"Reference directions: {len(ref_dirs)}")

algorithm = NSGA3(
    pop_size=200,
    ref_dirs=ref_dirs,
    sampling=IntegerRandomSampling(),
    crossover=SBX(prob=0.9, eta=15, vtype=float, repair=PortfolioRepair()),
    mutation=PM(eta=20, vtype=float, repair=PortfolioRepair()),
    repair=PortfolioRepair(),
)

problem = ETFPortfolioProblem()

print("Starting optimization...")
t0 = time.time()
result = minimize(
    problem,
    algorithm,
    termination=("n_gen", 500),
    seed=42,
    verbose=False,
)
elapsed = time.time() - t0
print(f"Optimization complete in {elapsed:.1f}s")

# ── Extract Pareto front ──────────────────────────────────────────────────
F = result.F.copy()
# Un-negate objectives
F[:, 0] = -F[:, 0]  # return (maximize)
F[:, 2] = -F[:, 2]  # yield (maximize)
X = result.X

print(f"\nPareto front: {len(F)} solutions")
print(f"Return range: {F[:, 0].min():.2f}% - {F[:, 0].max():.2f}%")
print(f"Volatility range: {F[:, 1].min():.2f}% - {F[:, 1].max():.2f}%")
print(f"Yield range: {F[:, 2].min():.2f}% - {F[:, 2].max():.2f}%")


# ── Curate 4 strategies ──────────────────────────────────────────────────
def describe_portfolio(idx, name):
    w = X[idx]
    ret = F[idx, 0]
    vol = F[idx, 1]
    yld = F[idx, 2]
    held = [(tickers[j], int(w[j])) for j in range(N) if w[j] > 0]
    held.sort(key=lambda x: -x[1])
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"  Return: {ret:.2f}%  |  Volatility: {vol:.2f}%  |  Yield: {yld:.2f}%")
    print(f"  Holdings: {len(held)}")
    print(f"{'='*60}")
    for t, pct in held:
        etf = next(e for e in etfs if e["ticker"] == t)
        print(f"    {t:6s}  {pct:3d}%   ({etf['category']})")
    return {"name": name, "return": round(ret, 2), "vol": round(vol, 2),
            "yield": round(yld, 2), "holdings": held}


# Strategy selection
growth_idx = np.argmax(F[:, 0])
safety_idx = np.argmin(F[:, 1])
income_idx = np.argmax(F[:, 2])

# Balanced: closest to normalized center of Pareto front
F_norm = (F - F.min(axis=0)) / (F.max(axis=0) - F.min(axis=0) + 1e-9)
center = np.array([0.5, 0.5, 0.5])
# For balanced: want high return (close to 1), low vol (close to 0), high yield (close to 1)
target = np.array([0.5, 0.5, 0.5])
dists = np.linalg.norm(F_norm - target, axis=1)
balanced_idx = np.argmin(dists)

strategies = []
strategies.append(describe_portfolio(growth_idx, "Growth (Highest Return)"))
strategies.append(describe_portfolio(balanced_idx, "Balanced (Center of Frontier)"))
strategies.append(describe_portfolio(income_idx, "Income (Highest Yield)"))
strategies.append(describe_portfolio(safety_idx, "Safety (Lowest Volatility)"))

# ── Build output data ─────────────────────────────────────────────────────
pareto_solutions = []
for i in range(len(F)):
    sol = {
        "return": round(float(F[i, 0]), 2),
        "vol": round(float(F[i, 1]), 2),
        "yield": round(float(F[i, 2]), 2),
    }
    pareto_solutions.append(sol)

output = {
    "solve_time_s": round(elapsed, 1),
    "n_solutions": len(F),
    "strategies": strategies,
    "solutions": pareto_solutions,
    "return_range": [round(float(F[:, 0].min()), 2), round(float(F[:, 0].max()), 2)],
    "vol_range": [round(float(F[:, 1].min()), 2), round(float(F[:, 1].max()), 2)],
    "yield_range": [round(float(F[:, 2].min()), 2), round(float(F[:, 2].max()), 2)],
}

with open("/Users/cameronafzal/Documents/frontier/dev_temp/pymoo_30_etf_results.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"\nResults saved to pymoo_30_etf_results.json")
print(f"Script lines: ~{sum(1 for _ in open(__file__))}")

"""
ETF Portfolio Multi-Objective Optimization using pymoo NSGA-III.

Three objectives:
  1. Expected Return (%) — maximize (sum aggregation: sum(w_i * ret_i))
  2. Volatility (%) — minimize (quadratic: sqrt(w^T @ Cov @ w))
  3. Dividend Yield (%) — maximize (weighted average: sum(w_i * yield_i) / sum(w_i))

Decision: 30 continuous weights summing to 100 (percentages).
Constraints:
  - Max single allocation <= 30%
  - Portfolio volatility <= 20%
  - At most 3 Sector ETFs held
  - At most 3 Alternative ETFs held
  - Between 4 and 12 holdings total
  - Each held position >= 1%
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
from pymoo.operators.sampling.rnd import FloatRandomSampling

# ─── Load data ───────────────────────────────────────────────────────────────

DATA_DIR = "/Users/cameronafzal/Documents/frontier/dev_temp"
OUT_DIR = "/Users/cameronafzal/Documents/frontier/dev_temp/eval/run_001/base/solver"

with open(f"{DATA_DIR}/etf_cache/etf_30_consolidated.json") as f:
    etfs = json.load(f)

with open(f"{DATA_DIR}/etf_cov_matrix.json") as f:
    cov_raw = json.load(f)

N = len(etfs)
tickers = [e["ticker"] for e in etfs]
returns = np.array([e["ann_return_5yr_pct"] for e in etfs])
yields_ = np.array([e["dividend_yield_pct"] for e in etfs])
groups = [e["group"] for e in etfs]

# Build covariance matrix in ticker order
cov_matrix = np.zeros((N, N))
for i, ti in enumerate(tickers):
    for j, tj in enumerate(tickers):
        cov_matrix[i, j] = cov_raw[ti][tj]

# Group indices
sector_idx = [i for i, g in enumerate(groups) if g == "Sectors"]
alt_idx = [i for i, g in enumerate(groups) if g == "Alternatives"]

print(f"ETFs: {N}, Sectors: {len(sector_idx)}, Alts: {len(alt_idx)}")
print(f"Sector tickers: {[tickers[i] for i in sector_idx]}")
print(f"Alt tickers: {[tickers[i] for i in alt_idx]}")


# ─── Repair operator ────────────────────────────────────────────────────────

class PortfolioRepair(Repair):
    """Repair solutions to satisfy hard constraints."""

    def _do(self, problem, X, **kwargs):
        for k in range(len(X)):
            x = X[k].copy()
            x = np.maximum(x, 0)

            # Zero out tiny positions (below 0.5) to control cardinality
            x[x < 0.5] = 0

            # Count held positions
            held = np.where(x > 0)[0]

            # If too few holdings, activate random ones
            if len(held) < 4:
                zero_idx = np.where(x <= 0)[0]
                needed = 4 - len(held)
                if len(zero_idx) >= needed:
                    activate = np.random.choice(zero_idx, needed, replace=False)
                    x[activate] = 5.0  # give them some weight
                    held = np.where(x > 0)[0]

            # If too many holdings, zero out smallest ones
            if len(held) > 12:
                sorted_held = held[np.argsort(x[held])]
                remove = sorted_held[:len(held) - 12]
                x[remove] = 0
                held = np.where(x > 0)[0]

            # Enforce group limits: at most 3 sector ETFs
            sector_held = [i for i in sector_idx if x[i] > 0]
            if len(sector_held) > 3:
                sector_weights = [(i, x[i]) for i in sector_held]
                sector_weights.sort(key=lambda t: t[1])
                for i, _ in sector_weights[:len(sector_held) - 3]:
                    x[i] = 0

            # Enforce group limits: at most 3 alternative ETFs
            alt_held = [i for i in alt_idx if x[i] > 0]
            if len(alt_held) > 3:
                alt_weights = [(i, x[i]) for i in alt_held]
                alt_weights.sort(key=lambda t: t[1])
                for i, _ in alt_weights[:len(alt_held) - 3]:
                    x[i] = 0

            # Enforce minimum 1% for held positions
            held = np.where(x > 0)[0]
            x[held] = np.maximum(x[held], 1.0)

            # Cap at 30%
            x = np.minimum(x, 30.0)

            # Re-check cardinality after group limit enforcement
            held = np.where(x > 0)[0]
            if len(held) < 4:
                zero_idx = np.where(x <= 0)[0]
                needed = 4 - len(held)
                if len(zero_idx) >= needed:
                    activate = np.random.choice(zero_idx, needed, replace=False)
                    x[activate] = 5.0
                    held = np.where(x > 0)[0]

            # Normalize to sum to 100
            total = x.sum()
            if total > 0:
                x = x * (100.0 / total)
            else:
                # Fallback: equal weight across 6 random ETFs
                chosen = np.random.choice(N, 6, replace=False)
                x[:] = 0
                x[chosen] = 100.0 / 6.0

            # After normalization, re-enforce min 1% and max 30%
            for _ in range(10):  # iterate to converge
                held = np.where(x > 0)[0]
                x[held] = np.maximum(x[held], 1.0)
                x = np.minimum(x, 30.0)
                total = x[x > 0].sum()
                if total > 0 and abs(total - 100.0) > 0.01:
                    x[x > 0] = x[x > 0] * (100.0 / total)
                else:
                    break

            X[k] = x
        return X


# ─── Problem definition ─────────────────────────────────────────────────────

class ETFPortfolioProblem(Problem):
    def __init__(self):
        super().__init__(
            n_var=N,
            n_obj=3,
            n_ieq_constr=5,  # vol<=20, sectors<=3, alts<=3, holdings>=4, holdings<=12
            xl=np.zeros(N),
            xu=np.full(N, 30.0),
        )

    def _evaluate(self, X, out, *args, **kwargs):
        n_pop = X.shape[0]
        F = np.zeros((n_pop, 3))
        G = np.zeros((n_pop, 5))

        for k in range(n_pop):
            w = X[k]  # weights in percentage points (sum to 100)
            w_frac = w / 100.0  # fractional weights

            # Obj 1: Expected return (maximize -> minimize negative)
            port_return = np.dot(w_frac, returns)
            F[k, 0] = -port_return  # minimize negative = maximize

            # Obj 2: Volatility (minimize)
            # cov_matrix is in pct^2 units, w_frac is fractional
            port_var = w_frac @ cov_matrix @ w_frac
            port_vol = np.sqrt(max(port_var, 0))
            F[k, 1] = port_vol

            # Obj 3: Dividend yield (maximize -> minimize negative)
            # weighted average
            total_w = w.sum()
            if total_w > 0:
                port_yield = np.dot(w, yields_) / total_w
            else:
                port_yield = 0
            F[k, 2] = -port_yield  # minimize negative = maximize

            # Constraints (<=0 means feasible)
            held = np.where(w > 0.5)[0]  # positions above 0.5%
            n_held = len(held)

            # G[0]: vol <= 20 -> vol - 20 <= 0
            G[k, 0] = port_vol - 20.0

            # G[1]: sector count <= 3
            n_sector = sum(1 for i in sector_idx if w[i] > 0.5)
            G[k, 1] = n_sector - 3

            # G[2]: alt count <= 3
            n_alt = sum(1 for i in alt_idx if w[i] > 0.5)
            G[k, 2] = n_alt - 3

            # G[3]: holdings >= 4 -> 4 - n_held <= 0
            G[k, 3] = 4 - n_held

            # G[4]: holdings <= 12 -> n_held - 12 <= 0
            G[k, 4] = n_held - 12

        out["F"] = F
        out["G"] = G


# ─── Solver configuration ───────────────────────────────────────────────────

# NSGA-III with 3 objectives
ref_dirs = get_reference_directions("das-dennis", 3, n_partitions=12)
print(f"Reference directions: {len(ref_dirs)}")

algorithm = NSGA3(
    ref_dirs=ref_dirs,
    pop_size=200,
    sampling=FloatRandomSampling(),
    crossover=SBX(prob=0.9, eta=15),
    mutation=PM(eta=20),
    repair=PortfolioRepair(),
)

problem = ETFPortfolioProblem()

print("Starting optimization...")
t0 = time.time()

result = minimize(
    problem,
    algorithm,
    termination=("n_gen", 400),
    seed=42,
    verbose=True,
)

solve_time = time.time() - t0
print(f"\nSolve time: {solve_time:.1f}s")
print(f"Solutions found: {len(result.F)}")

# ─── Extract and validate solutions ─────────────────────────────────────────

solutions = []
constraint_violations = 0

for k in range(len(result.F)):
    w = result.X[k]
    w_frac = w / 100.0
    f = result.F[k]

    port_return = -f[0]
    port_vol = f[1]
    port_yield = -f[2]

    # Validate constraints
    held = np.where(w > 0.5)[0]
    n_held = len(held)
    n_sector = sum(1 for i in sector_idx if w[i] > 0.5)
    n_alt = sum(1 for i in alt_idx if w[i] > 0.5)
    max_alloc = w.max()

    violations = []
    if port_vol > 20.05:
        violations.append(f"vol={port_vol:.2f}")
    if n_held < 4:
        violations.append(f"holdings={n_held}")
    if n_held > 12:
        violations.append(f"holdings={n_held}")
    if n_sector > 3:
        violations.append(f"sectors={n_sector}")
    if n_alt > 3:
        violations.append(f"alts={n_alt}")
    if max_alloc > 30.5:
        violations.append(f"max_alloc={max_alloc:.1f}")

    if violations:
        constraint_violations += 1
        continue

    # Round allocations to integers for cleanliness
    allocs = {}
    for i in held:
        allocs[tickers[i]] = round(float(w[i]))

    # Adjust rounding to sum to 100
    total_rounded = sum(allocs.values())
    if total_rounded != 100:
        diff = 100 - total_rounded
        # Adjust the largest allocation
        largest = max(allocs, key=allocs.get)
        allocs[largest] += diff

    solutions.append({
        "return_pct": round(port_return, 2),
        "volatility_pct": round(port_vol, 2),
        "yield_pct": round(port_yield, 2),
        "allocations": allocs,
        "n_holdings": n_held,
        "n_sectors": n_sector,
        "n_alts": n_alt,
    })

print(f"Valid solutions: {len(solutions)}")
print(f"Constraint violations filtered: {constraint_violations}")

# ─── Deduplicate similar solutions ───────────────────────────────────────────

def solution_distance(s1, s2):
    return np.sqrt(
        (s1["return_pct"] - s2["return_pct"]) ** 2 +
        (s1["volatility_pct"] - s2["volatility_pct"]) ** 2 +
        (s1["yield_pct"] - s2["yield_pct"]) ** 2
    )

unique = []
for s in solutions:
    is_dup = False
    for u in unique:
        if solution_distance(s, u) < 0.1:
            is_dup = True
            break
    if not is_dup:
        unique.append(s)

solutions = unique
print(f"After dedup: {len(solutions)} unique solutions")

# ─── Curate representative strategies ───────────────────────────────────────

def curate_strategies(solutions):
    """Select Growth, Balanced, Income, Safety from Pareto set."""
    if not solutions:
        return {}

    # Growth: maximize return
    growth = max(solutions, key=lambda s: s["return_pct"])

    # Safety: minimize volatility
    safety = min(solutions, key=lambda s: s["volatility_pct"])

    # Income: maximize dividend yield
    income = max(solutions, key=lambda s: s["yield_pct"])

    # Balanced: closest to ideal point (normalized)
    rets = [s["return_pct"] for s in solutions]
    vols = [s["volatility_pct"] for s in solutions]
    ylds = [s["yield_pct"] for s in solutions]

    ret_range = max(rets) - min(rets) if max(rets) > min(rets) else 1
    vol_range = max(vols) - min(vols) if max(vols) > min(vols) else 1
    yld_range = max(ylds) - min(ylds) if max(ylds) > min(ylds) else 1

    best_dist = float('inf')
    balanced = solutions[0]
    for s in solutions:
        # Normalized distance to ideal (max ret, min vol, max yield)
        d = (
            ((max(rets) - s["return_pct"]) / ret_range) ** 2 +
            ((s["volatility_pct"] - min(vols)) / vol_range) ** 2 +
            ((max(ylds) - s["yield_pct"]) / yld_range) ** 2
        )
        if d < best_dist:
            best_dist = d
            balanced = s

    return {
        "Growth": growth,
        "Safety": safety,
        "Income": income,
        "Balanced": balanced,
    }

curated = curate_strategies(solutions)

# ─── Print summary ──────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("RESULTS SUMMARY")
print("=" * 70)

if solutions:
    rets = [s["return_pct"] for s in solutions]
    vols = [s["volatility_pct"] for s in solutions]
    ylds = [s["yield_pct"] for s in solutions]
    print(f"Return range:  {min(rets):.2f}% — {max(rets):.2f}%")
    print(f"Vol range:     {min(vols):.2f}% — {max(vols):.2f}%")
    print(f"Yield range:   {min(ylds):.2f}% — {max(ylds):.2f}%")

print(f"\nCurated strategies:")
for name, s in curated.items():
    print(f"  {name}: ret={s['return_pct']:.2f}%, vol={s['volatility_pct']:.2f}%, yield={s['yield_pct']:.2f}%")
    print(f"    Holdings ({s['n_holdings']}): {s['allocations']}")

# ─── Write results.json ─────────────────────────────────────────────────────

output = {
    "base": {
        "solutions": [
            {
                "return_pct": s["return_pct"],
                "volatility_pct": s["volatility_pct"],
                "yield_pct": s["yield_pct"],
                "allocations": s["allocations"],
            }
            for s in solutions
        ],
        "curated": {
            name: {
                "return_pct": s["return_pct"],
                "volatility_pct": s["volatility_pct"],
                "yield_pct": s["yield_pct"],
                "allocations": s["allocations"],
            }
            for name, s in curated.items()
        },
    }
}

with open(f"{OUT_DIR}/results.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"\nResults written to {OUT_DIR}/results.json")

# ─── Save metadata for report generation ────────────────────────────────────

metadata = {
    "solve_time_s": round(solve_time, 1),
    "total_raw_solutions": len(result.F),
    "constraint_violations_filtered": constraint_violations,
    "valid_solutions": len(solutions),
    "return_range": [round(min(rets), 2), round(max(rets), 2)] if solutions else [],
    "vol_range": [round(min(vols), 2), round(max(vols), 2)] if solutions else [],
    "yield_range": [round(min(ylds), 2), round(max(ylds), 2)] if solutions else [],
    "algorithm": "NSGA-III",
    "pop_size": 200,
    "generations": 400,
    "ref_directions": len(ref_dirs),
    "seed": 42,
    "n_etfs": N,
}

with open(f"{OUT_DIR}/metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)

print(f"Metadata written to {OUT_DIR}/metadata.json")
print("\nDone.")

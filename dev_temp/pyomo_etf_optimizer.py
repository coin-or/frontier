"""
ETF Portfolio Optimization using Pyomo + GLPK
Epsilon-constraint method for multi-objective optimization.

3 objectives: maximize return, minimize volatility, maximize dividend yield
Constraints: vol cap 20%, max 2 sector ETFs, max 2 alternatives, 4-12 holdings, sum=100%
"""

import json
import time
from itertools import product as iterproduct

import pyomo.environ as pyo

# ── Load data ──────────────────────────────────────────────────────────────
with open("/Users/cameronafzal/Documents/frontier/dev_temp/etf_cache/etf_consolidated.json") as f:
    etfs = json.load(f)

tickers = [e["ticker"] for e in etfs]
N = len(tickers)
idx = {t: i for i, t in enumerate(tickers)}

ret = {i: etfs[i]["ann_return_5yr_pct"] for i in range(N)}
vol = {i: etfs[i]["ann_volatility_5yr_pct"] for i in range(N)}
div = {i: etfs[i]["dividend_yield_pct"] for i in range(N)}

SECTOR_ETFS = [idx[t] for t in ["VGT", "VHT", "VDE", "VFH"]]
ALT_ETFS = [idx[t] for t in ["VNQ", "GLD", "GSG"]]

# ── Build model ────────────────────────────────────────────────────────────
def build_model(ret_lb=None, vol_ub=None, div_lb=None, primary_obj="return"):
    """Build a MILP model with epsilon constraints on non-primary objectives."""
    m = pyo.ConcreteModel()
    m.I = pyo.RangeSet(0, N - 1)

    # x[i] = integer % allocation (0-100)
    m.x = pyo.Var(m.I, domain=pyo.NonNegativeIntegers, bounds=(0, 100))
    # y[i] = binary: 1 if ETF i is held
    m.y = pyo.Var(m.I, domain=pyo.Binary)

    # Allocations sum to 100
    m.sum_100 = pyo.Constraint(expr=sum(m.x[i] for i in m.I) == 100)

    # Link x and y: if x[i] > 0 then y[i] = 1; min allocation 1% if held
    m.link_upper = pyo.ConstraintList()
    m.link_lower = pyo.ConstraintList()
    for i in m.I:
        m.link_upper.add(m.x[i] <= 100 * m.y[i])
        m.link_lower.add(m.x[i] >= 1 * m.y[i])  # min 1% if selected

    # Cardinality: 4-12 holdings
    m.card_lb = pyo.Constraint(expr=sum(m.y[i] for i in m.I) >= 4)
    m.card_ub = pyo.Constraint(expr=sum(m.y[i] for i in m.I) <= 12)

    # Max 2 sector ETFs
    m.sector_cap = pyo.Constraint(
        expr=sum(m.y[i] for i in SECTOR_ETFS) <= 2
    )

    # Max 2 alternative ETFs
    m.alt_cap = pyo.Constraint(
        expr=sum(m.y[i] for i in ALT_ETFS) <= 2
    )

    # Volatility cap at 20% (weighted average)
    m.vol_hard_cap = pyo.Constraint(
        expr=sum(vol[i] * m.x[i] for i in m.I) <= 20.0 * 100
    )

    # Epsilon constraints
    if ret_lb is not None:
        m.ret_eps = pyo.Constraint(
            expr=sum(ret[i] * m.x[i] for i in m.I) >= ret_lb * 100
        )
    if vol_ub is not None:
        m.vol_eps = pyo.Constraint(
            expr=sum(vol[i] * m.x[i] for i in m.I) <= vol_ub * 100
        )
    if div_lb is not None:
        m.div_eps = pyo.Constraint(
            expr=sum(div[i] * m.x[i] for i in m.I) >= div_lb * 100
        )

    # Objective
    if primary_obj == "return":
        m.obj = pyo.Objective(
            expr=sum(ret[i] * m.x[i] for i in m.I), sense=pyo.maximize
        )
    elif primary_obj == "vol":
        m.obj = pyo.Objective(
            expr=sum(vol[i] * m.x[i] for i in m.I), sense=pyo.minimize
        )
    elif primary_obj == "dividend":
        m.obj = pyo.Objective(
            expr=sum(div[i] * m.x[i] for i in m.I), sense=pyo.maximize
        )

    return m


def solve_model(m, solver_name="glpk"):
    solver = pyo.SolverFactory(solver_name, executable="/opt/homebrew/bin/glpsol")
    result = solver.solve(m, tee=False)
    if result.solver.termination_condition != pyo.TerminationCondition.optimal:
        return None
    return extract_solution(m)


def extract_solution(m):
    allocs = {}
    for i in m.I:
        v = pyo.value(m.x[i])
        if v is not None and v > 0.5:
            allocs[tickers[i]] = int(round(v))

    w_ret = sum(ret[idx[t]] * allocs[t] for t in allocs) / 100
    w_vol = sum(vol[idx[t]] * allocs[t] for t in allocs) / 100
    w_div = sum(div[idx[t]] * allocs[t] for t in allocs) / 100

    return {
        "allocations": allocs,
        "return_pct": round(w_ret, 2),
        "volatility_pct": round(w_vol, 2),
        "dividend_pct": round(w_div, 2),
        "num_holdings": len(allocs),
    }


# ── Generate Pareto frontier ──────────────────────────────────────────────
print("=" * 70)
print("PYOMO ETF PORTFOLIO OPTIMIZER — Epsilon-Constraint Method")
print("=" * 70)

start_time = time.time()
solutions = []
seen = set()  # deduplicate by allocation tuple

def solution_key(sol):
    return tuple(sorted(sol["allocations"].items()))

# Step 1: Find extreme points (anchor solutions)
print("\n--- Phase 1: Anchor solutions ---")

# Max return (no extra eps constraints)
m = build_model(primary_obj="return")
sol = solve_model(m)
if sol:
    k = solution_key(sol)
    if k not in seen:
        seen.add(k)
        solutions.append(sol)
        print(f"  Max return: ret={sol['return_pct']}%, vol={sol['volatility_pct']}%, div={sol['dividend_pct']}%")

# Min volatility
m = build_model(primary_obj="vol")
sol = solve_model(m)
if sol:
    k = solution_key(sol)
    if k not in seen:
        seen.add(k)
        solutions.append(sol)
        print(f"  Min vol: ret={sol['return_pct']}%, vol={sol['volatility_pct']}%, div={sol['dividend_pct']}%")

# Max dividend
m = build_model(primary_obj="dividend")
sol = solve_model(m)
if sol:
    k = solution_key(sol)
    if k not in seen:
        seen.add(k)
        solutions.append(sol)
        print(f"  Max div: ret={sol['return_pct']}%, vol={sol['volatility_pct']}%, div={sol['dividend_pct']}%")

# Get ranges from anchors
ret_range = (min(s["return_pct"] for s in solutions), max(s["return_pct"] for s in solutions))
vol_range = (min(s["volatility_pct"] for s in solutions), max(s["volatility_pct"] for s in solutions))
div_range = (min(s["dividend_pct"] for s in solutions), max(s["dividend_pct"] for s in solutions))

print(f"\n  Return range: {ret_range[0]} - {ret_range[1]}%")
print(f"  Vol range:    {vol_range[0]} - {vol_range[1]}%")
print(f"  Div range:    {div_range[0]} - {div_range[1]}%")

# Step 2: Epsilon-constraint sweeps
print("\n--- Phase 2: Epsilon-constraint sweep ---")

# Sweep 1: Maximize return, vary vol_ub and div_lb
vol_steps = [vol_range[0] + (vol_range[1] - vol_range[0]) * f for f in [0.2, 0.35, 0.5, 0.65, 0.8]]
div_steps = [div_range[0] + (div_range[1] - div_range[0]) * f for f in [0.0, 0.25, 0.5, 0.75, 1.0]]

count = 0
for vub in vol_steps:
    for dlb in div_steps:
        m = build_model(vol_ub=vub, div_lb=dlb, primary_obj="return")
        sol = solve_model(m)
        if sol:
            k = solution_key(sol)
            if k not in seen:
                seen.add(k)
                solutions.append(sol)
                count += 1

print(f"  Sweep 1 (max return, vary vol/div): {count} new solutions")

# Sweep 2: Maximize dividend, vary vol_ub and ret_lb
ret_steps = [ret_range[0] + (ret_range[1] - ret_range[0]) * f for f in [0.0, 0.25, 0.5, 0.75, 1.0]]

count2 = 0
for vub in vol_steps:
    for rlb in ret_steps:
        m = build_model(vol_ub=vub, ret_lb=rlb, primary_obj="dividend")
        sol = solve_model(m)
        if sol:
            k = solution_key(sol)
            if k not in seen:
                seen.add(k)
                solutions.append(sol)
                count2 += 1

print(f"  Sweep 2 (max div, vary vol/ret): {count2} new solutions")

# Sweep 3: Minimize vol, vary ret_lb and div_lb
count3 = 0
for rlb in ret_steps:
    for dlb in div_steps:
        m = build_model(ret_lb=rlb, div_lb=dlb, primary_obj="vol")
        sol = solve_model(m)
        if sol:
            k = solution_key(sol)
            if k not in seen:
                seen.add(k)
                solutions.append(sol)
                count3 += 1

print(f"  Sweep 3 (min vol, vary ret/div): {count3} new solutions")

elapsed = time.time() - start_time

# ── Pareto filter ──────────────────────────────────────────────────────────
# A solution is Pareto-optimal if no other solution is >= on all 3 objectives
# (return higher, vol lower, div higher) and strictly better on at least one.
def is_dominated(s, others):
    for o in others:
        if o is s:
            continue
        if (o["return_pct"] >= s["return_pct"] and
            o["volatility_pct"] <= s["volatility_pct"] and
            o["dividend_pct"] >= s["dividend_pct"] and
            (o["return_pct"] > s["return_pct"] or
             o["volatility_pct"] < s["volatility_pct"] or
             o["dividend_pct"] > s["dividend_pct"])):
            return True
    return False

pareto = [s for s in solutions if not is_dominated(s, solutions)]
pareto.sort(key=lambda s: (-s["return_pct"], s["volatility_pct"]))

print(f"\n--- Results ---")
print(f"  Total unique solutions found: {len(solutions)}")
print(f"  Pareto-optimal solutions: {len(pareto)}")
print(f"  Solve time: {elapsed:.1f}s")

# ── Print all Pareto solutions ─────────────────────────────────────────────
print(f"\n{'='*70}")
print("PARETO FRONTIER")
print(f"{'='*70}")
for i, s in enumerate(pareto):
    print(f"\n--- Solution {i+1} ---")
    print(f"  Return: {s['return_pct']}%  |  Volatility: {s['volatility_pct']}%  |  Dividend: {s['dividend_pct']}%  |  Holdings: {s['num_holdings']}")
    allocs_str = ", ".join(f"{t}:{pct}%" for t, pct in sorted(s["allocations"].items(), key=lambda x: -x[1]))
    print(f"  {allocs_str}")

# ── Curate 4 strategies ───────────────────────────────────────────────────
print(f"\n{'='*70}")
print("CURATED STRATEGIES")
print(f"{'='*70}")

# Growth: highest return
growth = max(pareto, key=lambda s: s["return_pct"])

# Income: highest dividend yield
income = max(pareto, key=lambda s: s["dividend_pct"])

# Safety: lowest volatility
safety = min(pareto, key=lambda s: s["volatility_pct"])

# Balanced: best composite score (normalize each 0-1, equal weight)
ret_min, ret_max = min(s["return_pct"] for s in pareto), max(s["return_pct"] for s in pareto)
vol_min, vol_max = min(s["volatility_pct"] for s in pareto), max(s["volatility_pct"] for s in pareto)
div_min, div_max = min(s["dividend_pct"] for s in pareto), max(s["dividend_pct"] for s in pareto)

def composite(s):
    r = (s["return_pct"] - ret_min) / (ret_max - ret_min) if ret_max > ret_min else 0.5
    v = (vol_max - s["volatility_pct"]) / (vol_max - vol_min) if vol_max > vol_min else 0.5
    d = (s["dividend_pct"] - div_min) / (div_max - div_min) if div_max > div_min else 0.5
    return (r + v + d) / 3

balanced = max(pareto, key=composite)

for label, s in [("GROWTH", growth), ("BALANCED", balanced), ("INCOME", income), ("SAFETY", safety)]:
    print(f"\n--- {label} ---")
    print(f"  Return: {s['return_pct']}%  |  Volatility: {s['volatility_pct']}%  |  Dividend: {s['dividend_pct']}%  |  Holdings: {s['num_holdings']}")
    allocs_str = ", ".join(f"{t}:{pct}%" for t, pct in sorted(s["allocations"].items(), key=lambda x: -x[1]))
    print(f"  {allocs_str}")

# ── Dump JSON for markdown ─────────────────────────────────────────────────
output = {
    "elapsed_seconds": round(elapsed, 1),
    "total_unique_solutions": len(solutions),
    "pareto_solutions": len(pareto),
    "pareto": pareto,
    "curated": {
        "growth": growth,
        "balanced": balanced,
        "income": income,
        "safety": safety,
    }
}

with open("/Users/cameronafzal/Documents/frontier/dev_temp/pyomo_results.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"\nResults written to pyomo_results.json")

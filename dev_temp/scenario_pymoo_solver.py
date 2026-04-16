#!/usr/bin/env python3
"""
Multi-objective ETF portfolio optimization using pymoo NSGA-III.
Optimizes across 4 macro scenarios independently, then performs robustness analysis.
"""

import json
import time
import copy
import numpy as np
from pymoo.core.problem import Problem
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.util.ref_dirs import get_reference_directions
from pymoo.optimize import minimize
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.core.repair import Repair

# ─── Load data ───────────────────────────────────────────────────────────────
with open("/Users/cameronafzal/Documents/frontier/dev_temp/etf_cache/etf_30_consolidated.json") as f:
    etfs = json.load(f)

N = len(etfs)
tickers = [e["ticker"] for e in etfs]
groups = [e["group"] for e in etfs]
base_returns = np.array([e["ann_return_5yr_pct"] for e in etfs])
base_vols = np.array([e["ann_volatility_5yr_pct"] for e in etfs])
base_yields = np.array([e["dividend_yield_pct"] for e in etfs])

ticker_to_idx = {t: i for i, t in enumerate(tickers)}
sector_idxs = [i for i, g in enumerate(groups) if g == "Sectors"]
alt_idxs = [i for i, g in enumerate(groups) if g == "Alternatives"]
equity_idxs = [i for i, g in enumerate(groups) if g in ("US Equity", "Intl Equity")]
bond_idxs = [i for i, g in enumerate(groups) if g == "Bonds"]

# ─── Scenario definitions ───────────────────────────────────────────────────
def make_scenario_data(scenario_name):
    """Apply scenario adjustments to base data, return (returns, vols, yields)."""
    ret = base_returns.copy()
    vol = base_vols.copy()
    yld = base_yields.copy()

    if scenario_name == "base":
        pass
    elif scenario_name == "rate_cuts":
        for i in equity_idxs:
            ret[i] *= 1.3
            vol[i] *= 0.9
        for i in bond_idxs:
            yld[i] *= 0.7
        ret[ticker_to_idx["VGLT"]] = 8.0
    elif scenario_name == "recession":
        for i in equity_idxs:
            ret[i] *= 0.4
            vol[i] *= 1.5
        for i in sector_idxs:
            ret[i] *= 0.4
            vol[i] *= 1.5
        ret[ticker_to_idx["VGSH"]] = 4.0
        ret[ticker_to_idx["BND"]] = 4.0
        ret[ticker_to_idx["HYG"]] = -2.0
        vol[ticker_to_idx["HYG"]] = 10.3
        ret[ticker_to_idx["EMB"]] = -2.0
        vol[ticker_to_idx["EMB"]] = 13.6
    elif scenario_name == "inflation":
        for i in equity_idxs:
            ret[i] *= 0.8
        for i in bond_idxs:
            yld[i] *= 1.1
        ret[ticker_to_idx["GLD"]] = 29.82
        ret[ticker_to_idx["GSG"]] = 23.79
        ret[ticker_to_idx["DBA"]] = 16.07
        ret[ticker_to_idx["TIP"]] = 6.0
        ret[ticker_to_idx["BND"]] = -3.0
        ret[ticker_to_idx["VGLT"]] = -8.0
    return ret, vol, yld


# ─── Portfolio repair: enforce integer weights summing to 100, 4-12 holdings ─
class PortfolioRepair(Repair):
    def _do(self, problem, X, **kwargs):
        # X shape: (pop_size, N) — continuous values in [0, 1]
        Xp = np.copy(X)
        for i in range(Xp.shape[0]):
            x = Xp[i]
            # Sort by weight descending, keep top 12 max
            order = np.argsort(-x)
            # Zero out beyond 12
            x[order[12:]] = 0.0
            # If fewer than 4 are positive, boost smallest of the top 4
            top4 = order[:4]
            for j in top4:
                if x[j] < 0.01:
                    x[j] = 0.01
            # Enforce sector constraint: at most 3 sectors
            sec_held = [idx for idx in sector_idxs if x[idx] > 0]
            if len(sec_held) > 3:
                sec_sorted = sorted(sec_held, key=lambda idx: x[idx])
                for idx in sec_sorted[:len(sec_held)-3]:
                    x[idx] = 0.0
            # Enforce alternatives constraint: at most 3 alts
            alt_held = [idx for idx in alt_idxs if x[idx] > 0]
            if len(alt_held) > 3:
                alt_sorted = sorted(alt_held, key=lambda idx: x[idx])
                for idx in alt_sorted[:len(alt_held)-3]:
                    x[idx] = 0.0
            # Ensure at least 4 holdings
            held = np.where(x > 0)[0]
            if len(held) < 4:
                candidates = [j for j in range(N) if x[j] == 0]
                np.random.shuffle(candidates)
                for j in candidates[:4 - len(held)]:
                    x[j] = 0.01
            # Normalize to sum to 100 and round to integers
            total = x.sum()
            if total > 0:
                x = x / total * 100.0
            else:
                x = np.ones(N) / N * 100.0
            # Round to integers: largest remainder method
            floors = np.floor(x).astype(int)
            remainders = x - floors
            deficit = 100 - floors.sum()
            if deficit > 0:
                top_rem = np.argsort(-remainders)
                for j in top_rem[:int(deficit)]:
                    floors[j] += 1
            elif deficit < 0:
                # rare: reduce from largest
                top_vals = np.argsort(-floors)
                for j in top_vals[:int(-deficit)]:
                    floors[j] -= 1
            # Set zeros for anything that rounded to 0
            # Minimum 1% if held
            held_mask = floors > 0
            n_held = held_mask.sum()
            if n_held < 4:
                # Force top 4 by original weight to have at least 1
                order2 = np.argsort(-x)
                for j in order2[:4]:
                    if floors[j] == 0:
                        floors[j] = 1
                excess = floors.sum() - 100
                if excess > 0:
                    top_vals2 = np.argsort(-floors)
                    for j in top_vals2:
                        if floors[j] > 1:
                            reduce = min(floors[j] - 1, excess)
                            floors[j] -= reduce
                            excess -= reduce
                            if excess <= 0:
                                break
            Xp[i] = floors.astype(float)
        return Xp


# ─── Problem definition ─────────────────────────────────────────────────────
class ETFPortfolioProblem(Problem):
    def __init__(self, returns, vols, yields):
        super().__init__(
            n_var=N,
            n_obj=3,  # return (neg for min), vol, yield (neg for min)
            n_ieq_constr=1,  # vol <= 20
            xl=np.zeros(N),
            xu=np.ones(N),
        )
        self.ret = returns
        self.vol = vols
        self.yld = yields

    def _evaluate(self, X, out, *args, **kwargs):
        # X is already repaired to integer weights summing to 100
        w = X / 100.0  # fractional weights
        port_ret = (w * self.ret).sum(axis=1)
        port_vol = (w * self.vol).sum(axis=1)
        port_yld = (w * self.yld).sum(axis=1)

        # Objectives: minimize all → negate return and yield
        out["F"] = np.column_stack([-port_ret, port_vol, -port_yld])
        # Constraint: vol <= 20
        out["G"] = np.column_stack([port_vol - 20.0])


# ─── Solve one scenario ─────────────────────────────────────────────────────
def solve_scenario(scenario_name, seed=42):
    ret, vol, yld = make_scenario_data(scenario_name)
    problem = ETFPortfolioProblem(ret, vol, yld)

    ref_dirs = get_reference_directions("das-dennis", 3, n_partitions=12)

    algorithm = NSGA3(
        ref_dirs=ref_dirs,
        pop_size=200,
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(eta=20),
        repair=PortfolioRepair(),
    )

    t0 = time.time()
    res = minimize(
        problem,
        algorithm,
        ("n_gen", 300),
        seed=seed,
        verbose=False,
    )
    elapsed = time.time() - t0

    # Extract results
    solutions = []
    if res.F is not None:
        for i in range(len(res.F)):
            weights = res.X[i].astype(int)
            held = {tickers[j]: int(weights[j]) for j in range(N) if weights[j] > 0}
            port_ret = -res.F[i, 0]
            port_vol = res.F[i, 1]
            port_yld = -res.F[i, 2]
            solutions.append({
                "allocations": held,
                "return_pct": round(float(port_ret), 2),
                "volatility_pct": round(float(port_vol), 2),
                "yield_pct": round(float(port_yld), 2),
                "n_holdings": len(held),
            })

    return {
        "scenario": scenario_name,
        "n_solutions": len(solutions),
        "solve_time_s": round(elapsed, 2),
        "solutions": solutions,
        "scenario_data": {
            "returns": {tickers[i]: round(float(ret[i]), 2) for i in range(N)},
            "vols": {tickers[i]: round(float(vol[i]), 2) for i in range(N)},
            "yields": {tickers[i]: round(float(yld[i]), 2) for i in range(N)},
        }
    }


# ─── Curate strategies ──────────────────────────────────────────────────────
def curate_strategies(solutions):
    """Pick Growth, Balanced, Income, Safety from the Pareto set."""
    if not solutions:
        return {}

    strategies = {}

    # Growth: highest return
    growth = max(solutions, key=lambda s: s["return_pct"])
    strategies["Growth"] = growth

    # Safety: lowest volatility
    safety = min(solutions, key=lambda s: s["volatility_pct"])
    strategies["Safety"] = safety

    # Income: highest yield
    income = max(solutions, key=lambda s: s["yield_pct"])
    strategies["Income"] = income

    # Balanced: best combined score (normalize each objective)
    rets = [s["return_pct"] for s in solutions]
    vols = [s["volatility_pct"] for s in solutions]
    ylds = [s["yield_pct"] for s in solutions]

    ret_min, ret_max = min(rets), max(rets)
    vol_min, vol_max = min(vols), max(vols)
    yld_min, yld_max = min(ylds), max(ylds)

    def balanced_score(s):
        r = (s["return_pct"] - ret_min) / (ret_max - ret_min + 1e-9)
        v = 1.0 - (s["volatility_pct"] - vol_min) / (vol_max - vol_min + 1e-9)
        y = (s["yield_pct"] - yld_min) / (yld_max - yld_min + 1e-9)
        return r + v + y

    balanced = max(solutions, key=balanced_score)
    strategies["Balanced"] = balanced

    return strategies


# ─── Robustness analysis ────────────────────────────────────────────────────
def robustness_analysis(all_results):
    """Which ETFs appear across all scenarios in any Pareto solution."""
    scenario_etfs = {}
    for result in all_results:
        name = result["scenario"]
        etf_set = set()
        for sol in result["solutions"]:
            etf_set.update(sol["allocations"].keys())
        scenario_etfs[name] = etf_set

    all_scenarios = list(scenario_etfs.values())
    robust_etfs = all_scenarios[0]
    for s in all_scenarios[1:]:
        robust_etfs = robust_etfs & s

    # Scenario-specific: appear in only one scenario
    scenario_specific = {}
    for name, etf_set in scenario_etfs.items():
        others = set()
        for other_name, other_set in scenario_etfs.items():
            if other_name != name:
                others |= other_set
        unique = etf_set - others
        if unique:
            scenario_specific[name] = sorted(unique)

    # Frequency analysis: how often each ETF appears (weighted by solution count)
    etf_freq = {}
    for result in all_results:
        for sol in result["solutions"]:
            for t in sol["allocations"]:
                etf_freq[t] = etf_freq.get(t, 0) + 1

    total_solutions = sum(r["n_solutions"] for r in all_results)
    etf_pct = {t: round(100 * c / total_solutions, 1) for t, c in etf_freq.items()}

    return {
        "robust_etfs": sorted(robust_etfs),
        "scenario_specific": scenario_specific,
        "etf_frequency_pct": dict(sorted(etf_pct.items(), key=lambda x: -x[1])),
        "per_scenario_etfs": {name: sorted(s) for name, s in scenario_etfs.items()},
    }


# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    scenarios = ["base", "rate_cuts", "recession", "inflation"]
    all_results = []
    all_strategies = {}

    for sc in scenarios:
        print(f"Solving scenario: {sc}...")
        result = solve_scenario(sc)
        all_results.append(result)
        strats = curate_strategies(result["solutions"])
        all_strategies[sc] = strats
        print(f"  -> {result['n_solutions']} solutions in {result['solve_time_s']}s")
        for sname, s in strats.items():
            print(f"  {sname}: ret={s['return_pct']}%, vol={s['volatility_pct']}%, yld={s['yield_pct']}%")

    robust = robustness_analysis(all_results)

    # Save everything to JSON
    output = {
        "all_results": all_results,
        "all_strategies": all_strategies,
        "robustness": robust,
    }

    with open("/Users/cameronafzal/Documents/frontier/dev_temp/scenario_pymoo_raw.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n=== ROBUSTNESS ===")
    print(f"Robust ETFs (all scenarios): {robust['robust_etfs']}")
    print(f"Scenario-specific: {robust['scenario_specific']}")
    print(f"\nTop ETFs by frequency:")
    for t, pct in list(robust['etf_frequency_pct'].items())[:15]:
        print(f"  {t}: {pct}%")

    print("\nDone. Results saved to scenario_pymoo_raw.json")

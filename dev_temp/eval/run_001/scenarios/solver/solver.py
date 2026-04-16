#!/usr/bin/env python3
"""
Multi-objective ETF portfolio optimizer with scenario analysis.
Uses pymoo NSGA-II to find Pareto-optimal portfolios across 4 scenarios.
"""

import json
import numpy as np
import copy
from pymoo.core.problem import Problem
from pymoo.core.repair import Repair
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.optimize import minimize
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting

# ── Load data ──────────────────────────────────────────────────────────────
with open("/Users/cameronafzal/Documents/frontier/dev_temp/etf_cache/etf_30_consolidated.json") as f:
    etfs = json.load(f)
with open("/Users/cameronafzal/Documents/frontier/dev_temp/etf_cov_matrix.json") as f:
    cov_raw = json.load(f)

TICKERS = [e["ticker"] for e in etfs]
N = len(TICKERS)
ticker_idx = {t: i for i, t in enumerate(TICKERS)}

# Build covariance matrix (pct^2 units)
COV = np.zeros((N, N))
for i, t1 in enumerate(TICKERS):
    for j, t2 in enumerate(TICKERS):
        COV[i, j] = cov_raw[t1][t2]

# Base scores
BASE_RETURN = np.array([e["ann_return_5yr_pct"] for e in etfs])
BASE_VOL = np.array([e["ann_volatility_5yr_pct"] for e in etfs])
BASE_YIELD = np.array([e["dividend_yield_pct"] for e in etfs])

# Group membership
GROUPS = {}
for e in etfs:
    GROUPS.setdefault(e["group"], []).append(e["ticker"])

SECTOR_TICKERS = {"VGT", "VHT", "VDE", "VFH", "VPU", "VDC", "VOX"}
ALT_TICKERS = {"VNQ", "VNQI", "GLD", "GSG", "DBA", "IGF"}

SECTOR_IDX = [ticker_idx[t] for t in SECTOR_TICKERS]
ALT_IDX = [ticker_idx[t] for t in ALT_TICKERS]

# Group indices for scenario adjustments
EQUITY_IDX = [ticker_idx[t] for t in GROUPS.get("US Equity", []) + GROUPS.get("Intl Equity", [])]
BOND_IDX = [ticker_idx[t] for t in GROUPS.get("Bonds", [])]
SECTOR_GROUP_IDX = [ticker_idx[t] for t in GROUPS.get("Sectors", [])]
ALT_GROUP_IDX = [ticker_idx[t] for t in GROUPS.get("Alternatives", [])]


def build_scenario_scores(scenario_name):
    """Build adjusted return/vol/yield arrays for a scenario."""
    ret = BASE_RETURN.copy()
    vol = BASE_VOL.copy()
    yld = BASE_YIELD.copy()

    if scenario_name == "base":
        pass

    elif scenario_name == "rate_cuts":
        # equity returns x1.5, equity vol x0.8, bond yields x0.5, sector returns x1.4
        for i in EQUITY_IDX:
            ret[i] *= 1.5
            vol[i] *= 0.8
        for i in BOND_IDX:
            yld[i] *= 0.5
        for i in SECTOR_GROUP_IDX:
            ret[i] *= 1.4
        # Overrides
        ret[ticker_idx["VGLT"]] = 10.0
        ret[ticker_idx["VGT"]] = BASE_RETURN[ticker_idx["VGT"]] * 1.8

    elif scenario_name == "recession":
        # equity returns x0.2, equity vol x1.8
        for i in EQUITY_IDX:
            ret[i] *= 0.2
            vol[i] *= 1.8
        # sector returns x0.2, sector vol x1.8
        for i in SECTOR_GROUP_IDX:
            ret[i] *= 0.2
            vol[i] *= 1.8
        # alternative returns x0.5
        for i in ALT_GROUP_IDX:
            ret[i] *= 0.5
        # Overrides
        ret[ticker_idx["VGSH"]] = 4.5
        ret[ticker_idx["BND"]] = 5.0
        ret[ticker_idx["VGLT"]] = 7.0
        ret[ticker_idx["HYG"]] = -4.0
        vol[ticker_idx["HYG"]] = BASE_VOL[ticker_idx["HYG"]] * 1.8
        ret[ticker_idx["EMB"]] = -5.0
        vol[ticker_idx["EMB"]] = BASE_VOL[ticker_idx["EMB"]] * 1.8
        ret[ticker_idx["GLD"]] = BASE_RETURN[ticker_idx["GLD"]] * 1.3

    elif scenario_name == "inflation":
        # equity returns x0.6, equity vol x1.3
        for i in EQUITY_IDX:
            ret[i] *= 0.6
            vol[i] *= 1.3
        # bond returns x0.3, bond yields x1.2
        for i in BOND_IDX:
            ret[i] *= 0.3
            yld[i] *= 1.2
        # Overrides
        ret[ticker_idx["GLD"]] = BASE_RETURN[ticker_idx["GLD"]] * 2.0
        ret[ticker_idx["GSG"]] = BASE_RETURN[ticker_idx["GSG"]] * 2.0
        ret[ticker_idx["DBA"]] = BASE_RETURN[ticker_idx["DBA"]] * 2.0
        ret[ticker_idx["TIP"]] = 8.0
        ret[ticker_idx["BND"]] = -5.0
        ret[ticker_idx["VGLT"]] = -12.0
        ret[ticker_idx["VDE"]] = BASE_RETURN[ticker_idx["VDE"]] * 1.5

    return ret, vol, yld


# ── Repair operator ───────────────────────────────────────────────────────
class PortfolioRepair(Repair):
    def _do(self, problem, X, **kwargs):
        for i in range(len(X)):
            x = X[i].copy()
            # Clip to [0, 30]
            x = np.clip(x, 0.0, 30.0)

            # Zero out tiny allocations (< 1%)
            x[x < 1.0] = 0.0

            # Enforce cardinality: if > 12 holdings, keep top 12
            held = np.where(x > 0)[0]
            if len(held) > 12:
                sorted_idx = held[np.argsort(x[held])]
                for idx in sorted_idx[:len(held) - 12]:
                    x[idx] = 0.0

            # Enforce group limits: at most 3 sectors
            sector_held = [idx for idx in SECTOR_IDX if x[idx] > 0]
            if len(sector_held) > 3:
                sector_sorted = sorted(sector_held, key=lambda idx: x[idx])
                for idx in sector_sorted[:len(sector_held) - 3]:
                    x[idx] = 0.0

            # At most 3 alternatives
            alt_held = [idx for idx in ALT_IDX if x[idx] > 0]
            if len(alt_held) > 3:
                alt_sorted = sorted(alt_held, key=lambda idx: x[idx])
                for idx in alt_sorted[:len(alt_held) - 3]:
                    x[idx] = 0.0

            # If fewer than 4 holdings, try to bring some back
            held = np.where(x > 0)[0]
            if len(held) < 4:
                zeros = np.where(x == 0)[0]
                np.random.shuffle(zeros)
                for idx in zeros:
                    if len(held) >= 4:
                        break
                    x[idx] = max(1.0, np.random.uniform(1.0, 10.0))
                    held = np.where(x > 0)[0]

            # Normalize to sum to 100
            total = x.sum()
            if total > 0:
                x = x * 100.0 / total
            else:
                # Emergency: equal weight top 6
                top6 = np.argsort(BASE_RETURN)[-6:]
                x[top6] = 100.0 / 6

            # Re-clip max 30
            x = np.clip(x, 0.0, 30.0)
            # Re-zero tiny
            x[x < 1.0] = 0.0
            # Renormalize
            total = x.sum()
            if total > 0:
                x = x * 100.0 / total
            # Final clip
            x = np.clip(x, 0.0, 30.0)

            X[i] = x
        return X


# ── Problem definition ────────────────────────────────────────────────────
class ETFPortfolioProblem(Problem):
    def __init__(self, returns, vols, yields, cov_matrix):
        super().__init__(
            n_var=N,
            n_obj=3,
            n_ieq_constr=5,  # vol<=20, sectors<=3, alts<=3, holdings>=4, holdings<=12
            xl=np.zeros(N),
            xu=np.ones(N) * 30.0,
        )
        self.returns = returns
        self.vols = vols
        self.yields = yields
        self.cov = cov_matrix

    def _evaluate(self, X, out, *args, **kwargs):
        n_pop = X.shape[0]
        F = np.zeros((n_pop, 3))
        G = np.zeros((n_pop, 5))

        for i in range(n_pop):
            w_pct = X[i]
            w_frac = w_pct / 100.0

            # Objective 1: Expected Return (maximize -> minimize negative)
            port_return = np.dot(w_frac, self.returns)
            F[i, 0] = -port_return

            # Objective 2: Volatility (minimize) - quadratic
            port_var = w_frac @ self.cov @ w_frac
            port_vol = np.sqrt(max(port_var, 0.0))
            F[i, 1] = port_vol

            # Objective 3: Dividend Yield (maximize -> minimize negative) - weighted avg
            total_w = w_frac.sum()
            if total_w > 0:
                port_yield = np.dot(w_frac, self.yields) / total_w
            else:
                port_yield = 0.0
            F[i, 2] = -port_yield

            # Constraints (<=0 means feasible)
            # G[0]: portfolio vol <= 20%
            G[i, 0] = port_vol - 20.0

            # G[1]: sectors held <= 3
            sectors_held = sum(1 for idx in SECTOR_IDX if w_pct[idx] >= 1.0)
            G[i, 1] = sectors_held - 3.0

            # G[2]: alternatives held <= 3
            alts_held = sum(1 for idx in ALT_IDX if w_pct[idx] >= 1.0)
            G[i, 2] = alts_held - 3.0

            # G[3]: holdings >= 4 (i.e. 4 - holdings <= 0)
            holdings = sum(1 for w in w_pct if w >= 1.0)
            G[i, 3] = 4.0 - holdings

            # G[4]: holdings <= 12
            G[i, 4] = holdings - 12.0

        out["F"] = F
        out["G"] = G


# ── Run optimizer for each scenario ───────────────────────────────────────
SCENARIOS = {
    "base": {"prob": 0.30},
    "rate_cuts": {"prob": 0.25},
    "recession": {"prob": 0.20},
    "inflation": {"prob": 0.25},
}

all_results = {}

for scenario_name in SCENARIOS:
    print(f"\n{'='*60}")
    print(f"Running scenario: {scenario_name}")
    print(f"{'='*60}")

    ret, vol, yld = build_scenario_scores(scenario_name)

    problem = ETFPortfolioProblem(ret, vol, yld, COV)

    algorithm = NSGA2(
        pop_size=300,
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(eta=20),
        repair=PortfolioRepair(),
        eliminate_duplicates=True,
    )

    res = minimize(
        problem,
        algorithm,
        termination=("n_gen", 500),
        seed=42,
        verbose=False,
    )

    print(f"  Solutions found: {len(res.F) if res.F is not None else 0}")

    if res.F is not None and len(res.F) > 0:
        solutions = []
        for i in range(len(res.F)):
            w_pct = res.X[i]
            w_frac = w_pct / 100.0
            port_return = -res.F[i, 0]
            port_vol = res.F[i, 1]
            port_yield = -res.F[i, 2]

            holdings = {}
            for j in range(N):
                if w_pct[j] >= 0.5:  # count anything >= 0.5% as held
                    holdings[TICKERS[j]] = round(float(w_pct[j]), 2)

            solutions.append({
                "id": i,
                "return_pct": round(float(port_return), 4),
                "volatility_pct": round(float(port_vol), 4),
                "dividend_yield_pct": round(float(port_yield), 4),
                "n_holdings": len(holdings),
                "holdings": holdings,
            })

        # Sort by return descending for readability
        solutions.sort(key=lambda s: s["return_pct"], reverse=True)
        for idx, s in enumerate(solutions):
            s["id"] = idx

        all_results[scenario_name] = {
            "n_solutions": len(solutions),
            "solutions": solutions,
        }

        # Print summary stats
        rets = [s["return_pct"] for s in solutions]
        vols = [s["volatility_pct"] for s in solutions]
        ylds = [s["dividend_yield_pct"] for s in solutions]
        print(f"  Return range:  {min(rets):.2f}% to {max(rets):.2f}%")
        print(f"  Vol range:     {min(vols):.2f}% to {max(vols):.2f}%")
        print(f"  Yield range:   {min(ylds):.2f}% to {max(ylds):.2f}%")
    else:
        all_results[scenario_name] = {"n_solutions": 0, "solutions": []}
        print("  WARNING: No feasible solutions found!")


# ── Curation: find Growth, Balanced, Income, Safety per scenario ──────────
def curate_solutions(solutions):
    """Pick representative strategies from the Pareto set."""
    if not solutions:
        return {}

    curated = {}

    # Growth: highest return
    growth = max(solutions, key=lambda s: s["return_pct"])
    curated["Growth"] = growth

    # Safety: lowest volatility
    safety = min(solutions, key=lambda s: s["volatility_pct"])
    curated["Safety"] = safety

    # Income: highest yield
    income = max(solutions, key=lambda s: s["dividend_yield_pct"])
    curated["Income"] = income

    # Balanced: closest to ideal point (normalized)
    rets = [s["return_pct"] for s in solutions]
    vols = [s["volatility_pct"] for s in solutions]
    ylds = [s["dividend_yield_pct"] for s in solutions]
    ret_range = max(rets) - min(rets) if max(rets) != min(rets) else 1
    vol_range = max(vols) - min(vols) if max(vols) != min(vols) else 1
    yld_range = max(ylds) - min(ylds) if max(ylds) != min(ylds) else 1

    best_dist = float("inf")
    best_sol = solutions[0]
    for s in solutions:
        # Ideal: max return, min vol, max yield
        d = ((max(rets) - s["return_pct"]) / ret_range) ** 2 + \
            ((s["volatility_pct"] - min(vols)) / vol_range) ** 2 + \
            ((max(ylds) - s["dividend_yield_pct"]) / yld_range) ** 2
        if d < best_dist:
            best_dist = d
            best_sol = s
    curated["Balanced"] = best_sol

    return curated


for scenario_name in all_results:
    sols = all_results[scenario_name]["solutions"]
    all_results[scenario_name]["curated"] = curate_solutions(sols)


# ── Robustness analysis ──────────────────────────────────────────────────
def robustness_analysis(all_results):
    """Analyze which ETFs appear across scenarios."""
    scenario_etfs = {}
    for scenario_name, data in all_results.items():
        etf_freq = {}
        for s in data["solutions"]:
            for ticker in s["holdings"]:
                etf_freq[ticker] = etf_freq.get(ticker, 0) + 1
        n_sols = max(data["n_solutions"], 1)
        # Normalize to percentage of solutions
        scenario_etfs[scenario_name] = {t: round(c / n_sols * 100, 1) for t, c in etf_freq.items()}

    # Core ETFs: appear in >50% of solutions in ALL scenarios
    all_tickers = set()
    for etf_freq in scenario_etfs.values():
        all_tickers.update(etf_freq.keys())

    core = []
    common = []
    marginal = []
    for t in all_tickers:
        freqs = [scenario_etfs.get(s, {}).get(t, 0) for s in all_results]
        min_freq = min(freqs)
        avg_freq = np.mean(freqs)
        if min_freq > 50:
            core.append((t, avg_freq, min_freq))
        elif avg_freq > 25:
            common.append((t, avg_freq, min_freq))
        else:
            marginal.append((t, avg_freq, min_freq))

    core.sort(key=lambda x: -x[1])
    common.sort(key=lambda x: -x[1])
    marginal.sort(key=lambda x: -x[1])

    # Scenario-specific: high in one scenario, low in others
    scenario_specific = {}
    for scenario_name in all_results:
        specific = []
        for t in all_tickers:
            this_freq = scenario_etfs.get(scenario_name, {}).get(t, 0)
            other_freqs = [scenario_etfs.get(s, {}).get(t, 0) for s in all_results if s != scenario_name]
            max_other = max(other_freqs) if other_freqs else 0
            if this_freq > 50 and max_other < 25:
                specific.append((t, this_freq))
        specific.sort(key=lambda x: -x[1])
        scenario_specific[scenario_name] = specific

    return {
        "core": core,
        "common": common,
        "marginal": marginal,
        "scenario_specific": scenario_specific,
        "per_scenario_freq": scenario_etfs,
    }

robustness = robustness_analysis(all_results)


# ── Write results.json ────────────────────────────────────────────────────
output_dir = "/Users/cameronafzal/Documents/frontier/dev_temp/eval/run_001/scenarios/solver"

# Prepare JSON-serializable curated
json_results = {}
for scenario_name, data in all_results.items():
    curated_json = {}
    for strategy_name, sol in data.get("curated", {}).items():
        curated_json[strategy_name] = sol
    json_results[scenario_name] = {
        "solutions": data["solutions"],
        "curated": curated_json,
    }

with open(f"{output_dir}/results.json", "w") as f:
    json.dump(json_results, f, indent=2)

print(f"\nWrote results.json with {sum(len(d['solutions']) for d in json_results.values())} total solutions")


# ── Write robustness.json ─────────────────────────────────────────────────
rob_json = {
    "core": [{"ticker": t, "avg_freq": f, "min_freq": m} for t, f, m in robustness["core"]],
    "common": [{"ticker": t, "avg_freq": f, "min_freq": m} for t, f, m in robustness["common"]],
    "marginal": [{"ticker": t, "avg_freq": f, "min_freq": m} for t, f, m in robustness["marginal"]],
    "scenario_specific": {k: [{"ticker": t, "freq": f} for t, f in v] for k, v in robustness["scenario_specific"].items()},
    "per_scenario_freq": robustness["per_scenario_freq"],
}

with open(f"{output_dir}/robustness.json", "w") as f:
    json.dump(rob_json, f, indent=2)

print("Wrote robustness.json")
print("\n=== DONE ===")

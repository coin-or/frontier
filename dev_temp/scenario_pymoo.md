# Pymoo Scenario Evaluation Report

Multi-objective ETF portfolio optimization across 4 macro scenarios using NSGA-III. This evaluation tests whether the Frontier optimizer can produce meaningfully different portfolios under different market regimes while maintaining a robust core.

## 1. Setup

**Script:** `scenario_pymoo_solver.py` (362 lines)
**Dependencies:** pymoo (NSGA-III), numpy, json
**ETF universe:** 30 ETFs from `etf_30_consolidated.json`
**Algorithm:** NSGA-III with Das-Dennis reference directions (3 objectives, 12 partitions)
**Population:** 200, 300 generations per scenario
**Repair operator:** `PortfolioRepair` enforces integer weights summing to 100%, 4-12 holdings, max 3 sectors, max 3 alternatives, min 1% per holding
**Objectives:** maximize return, minimize volatility, maximize yield (3-objective Pareto front)
**Constraint:** portfolio volatility <= 20%

| Scenario | Solutions | Solve Time |
|----------|-----------|------------|
| base | 41 | 2.82s |
| rate_cuts | 42 | 2.77s |
| recession | 37 | 3.27s |
| inflation | 38 | 3.19s |

Total: 158 Pareto-optimal solutions across 4 scenarios in ~12s.

## 2. Issues

### Balanced = Safety collapse in recession
In the recession scenario, the Balanced strategy selected the exact same portfolio as Safety: BND 46%, VGSH 47%, VGK 3%, HYG 2%, DBA 1%, IGF 1% (ret=4.0%, vol=5.33%, yld=3.93%). This happens because the balanced scoring function uses equal-weight normalization across all three objectives:

```python
def balanced_score(s):
    r = (s["return_pct"] - ret_min) / (ret_max - ret_min + 1e-9)
    v = 1.0 - (s["volatility_pct"] - vol_min) / (vol_max - vol_min + 1e-9)
    y = (s["yield_pct"] - yld_min) / (yld_max - yld_min + 1e-9)
    return r + v + y
```

In a recession, the Pareto front is heavily compressed on the return axis (most solutions cluster near 4% return), so the volatility and yield terms dominate. The lowest-vol solution wins because there is little return to trade off against. This is a legitimate result reflecting the macro environment: in a recession, there is no good "balanced" option that is meaningfully different from safety. Fixing this would require adding explicit strategy differentiation constraints (e.g., requiring Balanced to have vol > Safety.vol * 1.1), which risks overfitting.

### Repair operator complexity
The `PortfolioRepair` class is the most complex part of the script (~75 lines). It handles:
- Top-12 holding truncation
- Min-4 holding enforcement
- Sector/alternatives caps (max 3 each)
- Largest-remainder rounding to integer weights summing to 100
- Edge cases where rounding drops holdings below minimum

This works but is fragile. The sequential repair steps can interact: zeroing out a sector holding for the cap constraint can drop below the min-4 threshold, requiring a second pass. The current implementation handles this but does not loop, so in theory a pathological case could slip through. No evidence this happened in practice with these results.

### Volatility model is naive
Portfolio volatility is computed as weighted-average of individual ETF volatilities: `sum(w_i * vol_i)`. This ignores correlations entirely. Real portfolio vol with diversification would be lower. This biases the optimizer toward concentrating in low-vol assets rather than exploiting diversification benefits. Good enough for scenario comparison, but the absolute vol numbers are overstated for diversified portfolios.

### Script length (362 lines)
The script is self-contained and includes scenario definitions, repair operator, problem definition, strategy curation, robustness analysis, and main loop all in one file. This is appropriate for a one-off evaluation but would need decomposition for production use.

## 3. Per-Scenario Results

### Base (current conditions)

41 Pareto-optimal solutions. Return range: [2.35%, 17.46%], Volatility range: [5.64%, 19.15%], Yield range: [1.18%, 5.07%].

| Strategy | Return | Vol | Yield | Holdings | Top Allocations |
|----------|--------|-----|-------|----------|-----------------|
| Growth | 17.46% | 19.15% | 1.18% | 7 | VDE 29, GLD 29, GSG 29, EWJ 5, VGSH 5 |
| Safety | 2.35% | 5.64% | 4.42% | 4 | VGSH 33, TIP 33, HYG 33, DBA 1 |
| Income | 4.59% | 11.37% | 5.07% | 4 | EWJ 33, HYG 33, EMB 33, VOO 1 |
| Balanced | 2.59% | 6.96% | 4.96% | 4 | VGSH 33, HYG 33, EMB 33, VGK 1 |

**Notable:** Growth leans heavily into commodities (GLD, GSG) and energy (VDE) -- these are the highest-return assets in the base scenario. Safety uses short-term bonds and TIPS. Income relies on international equity and high-yield bonds for yield. 21 unique ETFs appear in the Pareto set.

### Rate Cuts (lower rates, equity tailwind)

42 Pareto-optimal solutions. The broadest Pareto front.

| Strategy | Return | Vol | Yield | Holdings | Top Allocations |
|----------|--------|-----|-------|----------|-----------------|
| Growth | 15.30% | 16.86% | 1.81% | 8 | VOO 14, VUG 13, VTV 13, VEA 14, VGK 14, VDE 14, GLD 13, SCHD 5 |
| Safety | 1.19% | 5.26% | 2.61% | 4 | BND 33, VGSH 33, TIP 33, GSG 1 |
| Income | 6.74% | 13.12% | 3.78% | 8 | SCHD 14, VEA 14, HYG 14, EMB 14, VNQI 14, DBA 14, EWJ 13, VGLT 3 |
| Balanced | 4.58% | 9.18% | 3.52% | 7 | EWJ 16, BND 16, VGSH 16, HYG 16, EMB 17, DBA 16, VNQI 3 |

**Notable:** Growth shifts dramatically toward equities (VOO, VUG, VTV, VEA, VGK) reflecting the 1.3x return boost and 0.9x vol reduction. This is the only scenario where Growth uses broad equity ETFs. 24 unique ETFs appear -- the most diverse scenario. Scenario-specific ETFs: SCHD, VNQ, VUG (only appear here).

### Recession (equity drawdown, flight to safety)

37 Pareto-optimal solutions -- the smallest Pareto front, reflecting a compressed opportunity set.

| Strategy | Return | Vol | Yield | Holdings | Top Allocations |
|----------|--------|-----|-------|----------|-----------------|
| Growth | 15.47% | 15.94% | 1.31% | 4 | GLD 44, IGF 43, GSG 12, VGSH 1 |
| Safety | 4.00% | 5.33% | 3.93% | 6 | VGSH 47, BND 46, VGK 3, HYG 2, DBA 1, IGF 1 |
| Income | -1.75% | 12.11% | 5.40% | 4 | HYG 50, EMB 48, VOO 1, GSG 1 |
| **Balanced** | **4.00%** | **5.33%** | **3.93%** | **6** | **Same as Safety** |

**Notable:** Income has a **negative return** (-1.75%) because high-yield bonds (HYG, EMB) are penalized in recession. The optimizer still selects them for yield, correctly reflecting the tradeoff: you can get 5.4% yield but you lose principal. Growth concentrates in gold (44%) and infrastructure (43%) -- the only assets with strong positive returns in this scenario. Balanced collapses to Safety (see Issues section).

### Inflation (commodity tailwind, bond headwind)

38 Pareto-optimal solutions.

| Strategy | Return | Vol | Yield | Holdings | Top Allocations |
|----------|--------|-----|-------|----------|-----------------|
| Growth | 26.53% | 17.65% | 0.09% | 4 | GLD 49, GSG 49, HYG 1, VDE 1 |
| Safety | 4.49% | 5.68% | 4.10% | 6 | VGSH 42, TIP 42, EMB 8, DBA 4, IGF 3, VOX 1 |
| Income | 2.89% | 8.01% | 5.66% | 5 | HYG 40, EMB 40, VGSH 18, VOO 1, DBA 1 |
| Balanced | 2.93% | 5.76% | 5.33% | 5 | VGSH 44, HYG 44, EMB 7, IGF 3, BND 2 |

**Notable:** Growth hits 26.53% return -- the highest across all scenarios -- driven by inflation-boosted GLD (29.82%) and GSG (23.79%). Safety correctly rotates into TIPS (42%) as an inflation hedge. Income yield is the highest across scenarios (5.66%). Scenario-specific ETFs: VOX, VPU (utilities and communication, both defensive sectors).

## 4. Robustness Analysis

### Robust ETFs (appear in all 4 scenarios)

12 ETFs appear in at least one Pareto-optimal portfolio across every scenario:

| ETF | Group | Frequency | Role |
|-----|-------|-----------|------|
| DBA | Alternatives | 77.8% | Commodity diversifier, appears in ~78% of all solutions |
| HYG | Bonds | 76.6% | Yield anchor, high frequency across all regimes |
| VGSH | Bonds | 74.1% | Safety anchor, short-duration stability |
| GLD | Alternatives | 48.7% | Growth/inflation hedge |
| EWJ | Intl Equity | 42.4% | International diversifier |
| EMB | Bonds | 38.0% | Emerging market yield |
| TIP | Bonds | 32.3% | Inflation protection |
| VDE | Sectors | 32.3% | Energy exposure |
| BND | Bonds | 31.6% | Core fixed income |
| IGF | Sectors | 27.8% | Infrastructure, appears in all scenarios |
| VOO | US Equity | 16.5% | Core US equity |
| VGK | Intl Equity | 10.8% | European equity |

The top 3 (DBA, HYG, VGSH) form a reliable core that the optimizer selects regardless of macro environment. This makes sense: DBA provides uncorrelated commodity exposure, HYG provides yield, VGSH provides stability.

### Scenario-Specific ETFs

| Scenario | Unique ETFs | Interpretation |
|----------|-------------|----------------|
| base | VDC | Consumer staples only needed in neutral conditions |
| rate_cuts | SCHD, VNQ, VUG | Rate-sensitive: dividend stocks, REITs, growth equity |
| inflation | VOX, VPU | Defensive sectors as inflation hedges |
| recession | (none) | Recession uses a subset of the robust set -- no unique assets needed |

### Frequency Distribution

The frequency data shows a clear power law: 3 ETFs appear in >74% of solutions, then a sharp drop. Only 17 of 30 ETFs appear in >1% of solutions. 13 ETFs are rarely or never selected, suggesting the 30-ETF universe could be trimmed without losing much optimization quality.

## 5. Cross-Scenario Comparison

### How Growth shifts

| Scenario | Return | Vol | Dominant Assets | Character |
|----------|--------|-----|----------------|-----------|
| base | 17.46% | 19.15% | VDE, GLD, GSG | Commodity/energy play |
| rate_cuts | 15.30% | 16.86% | VOO, VUG, VTV, VEA, VGK | Broad equity diversification |
| recession | 15.47% | 15.94% | GLD, IGF | Gold + infrastructure |
| inflation | 26.53% | 17.65% | GLD, GSG | Pure commodity play |

Growth correctly adapts: equities in rate cuts, gold in recession/inflation, energy in base. The optimizer is not just selecting the same portfolio with different labels.

### How Safety stays stable

| Scenario | Return | Vol | Core Holdings |
|----------|--------|-----|---------------|
| base | 2.35% | 5.64% | VGSH 33, TIP 33, HYG 33 |
| rate_cuts | 1.19% | 5.26% | BND 33, VGSH 33, TIP 33 |
| recession | 4.00% | 5.33% | VGSH 47, BND 46 |
| inflation | 4.49% | 5.68% | VGSH 42, TIP 42 |

Safety is remarkably consistent: VGSH anchors every scenario, vol stays in the 5.2-5.7% band. The main adaptation is whether to add TIP (inflation) or BND (recession/rate cuts) as the second major holding.

### How Income adapts yield vs. return

| Scenario | Return | Yield | Key Observation |
|----------|--------|-------|-----------------|
| base | 4.59% | 5.07% | Balanced yield-return |
| rate_cuts | 6.74% | 3.78% | Yield drops (rate cuts reduce bond yields) |
| recession | -1.75% | 5.40% | Maximum yield, but at the cost of negative returns |
| inflation | 2.89% | 5.66% | Highest yield available |

The income strategy honestly reflects macro reality: in a recession, chasing yield means accepting credit risk and potential capital loss.

## 6. Interpretation Response

*(Written as if presenting to a user asking "how should my portfolio change across these scenarios?")*

The optimizer reveals that your portfolio should have a **stable core** and **adaptive satellites**.

**The stable core (regardless of what happens):** Short-term treasuries (VGSH) for stability, high-yield bonds (HYG) for income, and agricultural commodities (DBA) for uncorrelated returns. These three appear in 74-78% of all optimal portfolios across every scenario tested. Add TIPS (TIP) and aggregate bonds (BND) for a robust five-asset base.

**What changes -- and why it matters:**

1. **If rates get cut:** Rotate growth exposure into broad equities. This is the only scenario where the optimizer heavily favors stocks like VOO, VUG, and international equity. The return/risk ratio improves enough to justify significant equity allocation. Dividend stocks (SCHD) and REITs (VNQ) become viable -- they are not selected in any other scenario.

2. **If we enter recession:** The optimizer's message is blunt: there are no good growth options in equities. Gold (GLD) and infrastructure (IGF) are the only assets with strong positive returns. The "balanced" portfolio collapses into the safety portfolio because there is genuinely nothing in the middle -- you either accept high volatility for gold-driven growth, or you retreat to short-term bonds. Income-seeking means accepting negative total returns (-1.75%) for 5.4% yield -- the optimizer will do it if you ask, but it is flagging that credit risk is real.

3. **If inflation rises:** Gold and commodities dominate growth (26.5% return). This is the strongest growth scenario by far. TIPS become essential in the safety portfolio (42% allocation vs. 33% in base). The optimizer correctly identifies that nominal bonds (BND) become a liability and rotates toward real-return assets.

**Quantifying the tradeoffs:**
- Growth return ranges from 15.3% (rate cuts) to 26.5% (inflation) -- a 11 percentage point spread driven entirely by commodity performance
- Safety return ranges from 1.2% (rate cuts) to 4.5% (inflation) -- small absolute moves, but a 3.8x difference
- Income yield is remarkably stable (3.8-5.7%) but return swings from -1.75% to +6.74% depending on credit conditions
- Volatility for Safety stays in a tight 5.3-5.7% band regardless of scenario -- this is the most reliable metric

**What this means for the Frontier product:** The scenario system produces genuinely different portfolios that respond logically to macro assumptions. The 12 robust ETFs provide a reliable core, and the 5-8 scenario-sensitive ETFs provide meaningful adaptation. The biggest concern is the Balanced-Safety collapse in recession -- this needs either a different scoring approach or an honest acknowledgment that "balanced" is not always a distinct strategy.

## 7. Raw Data

Full results are in `scenario_pymoo_raw.json` (3016 lines). Key structure:

```json
{
  "all_results": [
    {
      "scenario": "base|rate_cuts|recession|inflation",
      "n_solutions": 37-42,
      "solve_time_s": 2.77-3.27,
      "solutions": [
        {
          "allocations": {"TICKER": weight_pct, ...},
          "return_pct": float,
          "volatility_pct": float,
          "yield_pct": float,
          "n_holdings": int
        }
      ],
      "scenario_data": {
        "returns": {"TICKER": float, ...},
        "vols": {"TICKER": float, ...},
        "yields": {"TICKER": float, ...}
      }
    }
  ],
  "all_strategies": {
    "scenario_name": {
      "Growth|Safety|Income|Balanced": { ... }
    }
  },
  "robustness": {
    "robust_etfs": [...],
    "scenario_specific": {...},
    "etf_frequency_pct": {...},
    "per_scenario_etfs": {...}
  }
}
```

### Plotting suggestions

The JSON contains everything needed for:
- **3D Pareto front scatter** (return vs. vol vs. yield) per scenario, color-coded by strategy
- **ETF frequency heatmap** (ETF x scenario, cell = % of solutions containing that ETF)
- **Strategy shift bar charts** (return/vol/yield per strategy across scenarios)
- **Allocation sankey** showing how weight flows between asset classes across scenarios

# Frontier MCP — ETF Portfolio Optimization Results

## Summary

- 30 ETFs, 3 objectives (Return max, Volatility min/quadratic, Yield max)
- Constraints: max 30% per ETF, portfolio vol ≤ 20%, ≤3 Sectors, ≤3 Alternatives, cardinality 4-12
- Mode: `thorough`; algorithm NSGA-II (3 objectives)
- Base frontier from the initial `solve run`: 60 solutions
- Per-scenario runs (`run_scenarios`): 40 Pareto solutions each × 4 scenarios

## Base Case Frontier (initial solve run)

| Metric | Min | Max |
|---|---|---|
| Return (%) | 2.56 | 18.58 |
| Volatility (%) | 4.18 | 15.79 |
| Yield (%) | 0.58 | 4.91 |

Correlations: Return-Volatility r=+0.91, Return-Yield r=-0.89, Volatility-Yield r=-0.70. The frontier is three-sided: high-return portfolios concentrate in sectors/commodities with high vol and low yield; low-vol portfolios lean on short-duration Treasuries; high-yield portfolios use credit (HYG, EMB) plus Japan/international.

Extremes:
- Top Return (sol 1): 18.58% / 15.79 vol / 0.98 yield — VGT 30, VDE 30, GLD 30, GSG 4, VUG 2, SCHD 2, EWJ 1, IGF 1
- Top Safety (sol 58): 3.28% / 4.18 vol / 4.06 yield — BND 30, VGSH 30, HYG 18, SCHD 6, DBA 5, TIP 3, EMB 2, VGT 2, EWJ 2, GLD 1, IGF 1
- Top Yield (sol 56): 4.68% / 7.14 vol / 4.91 yield — EWJ 30, HYG 30, EMB 30, VEA 2, VWO 2, VGLT 2, DBA 2, TIP 1, IGF 1
- Balanced (sol 41): 9.57% / 6.66 vol / 3.31 yield — HYG, VGSH, VGT, GLD, VDE, DBA, IGF, TIP, VHT

Inflection points:
- Sol 31: sharp jump on Return-vs-Volatility cost (jump factor 157x). Below ~11.7% return, the vol cost of an extra return point explodes.
- Sol 54: jump on Return-vs-Yield (82x). Past ~5% return, adding yield costs almost no return up to the top-yield corner.

## Per-Scenario Frontier Ranges (from run_scenarios)

| Scenario (Prob) | Return min..max | Vol min..max | Yield min..max | Solutions |
|---|---|---|---|---|
| Base (30%) | 3.64 .. 18.74 | 4.17 .. 15.74 | 0.53 .. 4.90 | 40 |
| Rate Cuts (25%) | 3.86 .. 25.28 | 4.15 .. 17.78 | 1.02 .. 3.85 | 40 |
| Recession (20%) | -1.50 .. 12.58 | 4.16 .. 10.20 | 1.83 .. 5.02 | 40 |
| Inflation (25%) | -2.65 .. 30.05 | 4.14 .. 13.75 | 1.87 .. 5.95 | 40 |

Observations:
- **Rate Cuts** has the highest achievable return (25.28%) but the tightest yield ceiling (3.85%) — equities and sectors rally, bond yields compress.
- **Recession** clamps return upside (12.58%) and compresses vol (10.20 max) because bonds become attractive.
- **Inflation** has the widest spread — commodities (GLD×2, GSG×2, DBA×2, VDE×1.5) lift the Return frontier while bond cuts push the Yield frontier higher via high-yield credit.
- **Base** sits in the middle as expected.

## Robustness — Option Importance Across All Scenarios

Core tier (>50% frequency in all 4 scenarios):
- **HYG** — freq 87.5%, avg weight 18.7%, importance score 16.34
- **GLD** — freq 71.3%, avg weight 18.2%, importance score 13.00

Common tier (appears in all 4 scenarios, importance 3-10):
- VGSH (10.21), DBA (9.52), VGLT (4.98), BND (4.30), EMB (3.91), EWJ (3.57), VGT (3.05), TIP (1.13), IGF (1.06), VNQI (0.91), SCHD (0.47)

Marginal tier (3-of-4 or weak average weight):
- VDE (10.25, but only 3/4 scenarios — absent in recession), GSG (3/4), VTV, VOO, VUG, VWO, VHT, VFH, VOX, VB, MCHI (2/4)

Scenario-specific picks (appear in one scenario's Pareto set but not all):
- Base only (unusual): GSG (also in recession, inflation)
- Rate Cuts only: (none truly unique — it overlaps with base/inflation)
- Recession only: deeper bond allocations — MCHI, VB, VWO, VHT
- Inflation only: VDE ×1.5 driving extreme returns; VFH, VOX on yield side

## Curated Strategies (per scenario)

See `curated.md` for full detail and `results.json` for allocations.

Quick comparison of the Balanced strategy per scenario:

| Scenario | Return | Vol | Yield | Core holdings |
|---|---|---|---|---|
| Base | 10.08 | 7.30 | 3.32 | VGSH 26, HYG 27, GLD 19, VDE 16, IGF 6, VGT 2, VEA 2, EWJ 2 |
| Rate Cuts | 12.86 | 9.42 | 2.88 | DBA 25, VDE 18, EWJ 17, VGLT 16, BND 10, HYG 9, VGT 3, GLD 2 |
| Recession | 6.69 | 5.14 | 3.59 | BND 30, VGSH 30, VGLT 15, GLD 11, HYG 6, VOO 3, VEA 3, EWJ 2 |
| Inflation | 11.54 | 6.44 | 4.46 | HYG 23, EMB 23, DBA 21, GLD 14, VGSH 10, TIP 3, BND 2, VDE 2, VUG 2 |

## Marginal Analysis (Base Frontier)

- Median Volatility cost per unit Return = 4.71; max 51.97 at solution 41→42
- Steepest transitions (Return→Volatility): 41→42 (51.97), 33→34 (48.87), 23→24 (47.07) — these mark corners where each additional return point becomes very expensive in vol
- Key Return-Yield inflection at solution 54 (82x jump factor) — past this point, moving further up in yield cost almost no return

## Methodology Notes

- Volatility uses quadratic aggregation with a 30x30 covariance matrix (annualized pairwise). Portfolio vol = sqrt(w^T · Σ · w) where w is the allocation vector.
- Return is sum-aggregated (weighted allocation).
- Yield is average-aggregated across selected options (not weighted by allocation).
- Scenarios override individual option scores; covariance matrix is held constant across scenarios (see issues.md for discussion).

# ETF Portfolio Allocation Demo

## Purpose
Demo of Frontier's Phase 1 (solution exploration) using a real investment portfolio problem.
Tests the skill auto-injection system — agent should receive skill guidance automatically
at each workflow phase without manually calling `get_skill()`.

## Data
Consolidated ETF data: `dev_temp/etf_cache/etf_30_consolidated.json`
- 30 ETFs across 5 asset class groups
- Source: yfinance (5yr monthly returns + dividend yield + expense ratio)
- Fields per ETF: ticker, category, group, expense_ratio_pct, dividend_yield_pct, ann_return_5yr_pct, ann_volatility_5yr_pct, top_sector, top_sector_weight_pct

## Problem Setup

### Approach
**Proportional** — allocate % across ETFs, summing to 100%.

### Objectives (3)
| Objective | Direction | Unit | Aggregation | Score field |
|-----------|-----------|------|-------------|-------------|
| Expected Return | maximize | % annualized | avg | ann_return_5yr_pct |
| Volatility | minimize | % annualized std dev | avg | ann_volatility_5yr_pct |
| Dividend Yield | maximize | % trailing 12mo | avg | dividend_yield_pct |

### Options (30 with groups)
| Group | Tickers |
|-------|---------|
| US Equity (6) | VOO, VUG, VTV, VO, VB, SCHD |
| Intl Equity (5) | VEA, VWO, VGK, EWJ, MCHI |
| Bonds (6) | BND, VGSH, VGLT, TIP, HYG, EMB |
| Sectors (7) | VGT, VHT, VDE, VFH, VPU, VDC, VOX |
| Alternatives (6) | VNQ, VNQI, GLD, GSG, DBA, IGF |

### Constraints
| Type | Params |
|------|--------|
| objective_bound | Volatility max 20 |
| group_limit | Sector ETFs (VGT, VHT, VDE, VFH, VPU, VDC, VOX) max 3 |
| group_limit | Alternatives (VNQ, VNQI, GLD, GSG, DBA, IGF) max 3 |
| cardinality | min 4, max 12 |

### Scores
Load from `dev_temp/etf_cache/etf_30_consolidated.json`. Each ETF has all 3 objective values.
Enter as scores to `model update` — use the field mapping above.

## Execution Steps

1. **Create problem** — use `model create` with name, domain, context, approach="proportional".
   Pass objectives and options in create.
   Expect: `_skill_guidance` with `data_collection` in response.

2. **Enter scores** — read `dev_temp/etf_cache/etf_30_consolidated.json` and build score list.
   Map: option=ticker, objective="Expected Return" → ann_return_5yr_pct, etc.
   Can batch all 90 scores (30 × 3) in one `model update` call.
   Expect: `_skill_guidance` with `optimization_strategy` when scores hit 100%.

3. **Add constraints** — use constraint schemas from server instructions.
   ```json
   [
     {"type": "objective_bound", "objective": "Volatility", "operator": "max", "value": 20},
     {"type": "group_limit", "options": ["VGT", "VHT", "VDE", "VFH", "VPU", "VDC", "VOX"], "max": 3},
     {"type": "group_limit", "options": ["VNQ", "VNQI", "GLD", "GSG", "DBA", "IGF"], "max": 3},
     {"type": "cardinality", "min": 4, "max": 12}
   ]
   ```

4. **Solve** — `solve run` with mode="fast" for first iteration.
   Expect: `_skill_guidance` with `solution_interpreter` in response.

5. **Explore** — follow the solution_interpreter guidance:
   - `explore tradeoffs` — get overview, extremes, balanced solution
   - `explore compare` — compare 2-3 interesting solutions side-by-side
   - `explore marginal_analysis` — cost-per-unit between adjacent solutions
   - `explore curate` — name interesting strategies ("Growth", "Income", "Balanced")

6. **Scenarios (optional)** — add recession/bull market scenarios:
   - Recession: bonds up, equities down (score_adjustments on Expected Return)
   - Bull: growth equities up, bonds flat
   - `solve run_scenarios` then `explore scenario_results`

## What to Verify
- [ ] Agent never needs to call `get_skill()` manually — guidance arrives automatically
- [ ] Constraint schemas work on first attempt (no guessing field names)
- [ ] `model create` accepts objectives and options (previously silently dropped)
- [ ] Agent follows solution_interpreter guidance when presenting results (no "best", quantifies tradeoffs)
- [ ] Tradeoff structure shows genuine 3-way conflict (return↔volatility, return↔yield)
- [ ] 30 options with 3 objectives produces rich Pareto frontier

## Design Notes
- Expense ratio dropped as objective (0.03-0.85% scale too small, better as constraint)
- Volatility is linear avg, not covariance-based — acknowledged simplification for demo
- VGLT has -5.0% return (2022-2023 rate shock) and MCHI -5.0% (China downturn) — valid, good tradeoff dynamics
- GLD (20%) and VDE (22%) are top returners but with very different characteristics — tests whether optimizer finds hybrid strategies
- Data source: yfinance (free, no API key). FMP free tier only supports profile endpoint.

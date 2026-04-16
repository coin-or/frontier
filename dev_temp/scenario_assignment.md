# Assignment: ETF Portfolio Allocation with Scenario Analysis (v2)

## Problem

Allocate a portfolio across 30 ETFs to optimize three objectives simultaneously:
- **Expected Return (%)** — maximize, aggregation: sum
- **Volatility (%)** — minimize, aggregation: **quadratic** (uses covariance matrix for true portfolio risk)
- **Dividend Yield (%)** — maximize, aggregation: avg

## Data

ETF data is in `/Users/cameronafzal/Documents/frontier/dev_temp/etf_cache/etf_30_consolidated.json`. Each ETF has: ticker, category, group, dividend_yield_pct, ann_return_5yr_pct, ann_volatility_5yr_pct.

Covariance matrix for Volatility objective: `/Users/cameronafzal/Documents/frontier/dev_temp/etf_cov_matrix.json`. This is a 30×30 symmetric matrix estimated from asset-class correlations × individual volatilities. Pass as `interaction_matrices` entry for the Volatility objective.

Groups: US Equity (6), Intl Equity (5), Bonds (6), Sectors (7), Alternatives (6).

## Approach

Proportional allocation: assign a percentage (integer, minimum 1% if held) to each ETF, summing to 100%.

## Constraints

1. **Max single allocation ≤ 30%** — no single ETF can exceed 30% of portfolio
2. Weighted-average volatility ≤ 20%
3. At most 3 Sector ETFs held (group = "Sectors": VGT, VHT, VDE, VFH, VPU, VDC, VOX)
4. At most 3 Alternative ETFs held (group = "Alternatives": VNQ, VNQI, GLD, GSG, DBA, IGF)
5. Between 4 and 12 holdings total

## Scenarios

The base-case data reflects 5-year historical performance (2021-2026). We stress-test portfolios against four forward-looking macro regimes. For each scenario, adjust the base-case scores as described, then optimize independently.

**v2 changes:** Wider multipliers to produce meaningfully different frontiers per scenario. v1 adjustments were too narrow (return range only varied 0.1% across scenarios).

### Scenario 1: Base Case (Continuation)
- **Probability:** 30%
- **Description:** Current macro trajectory continues. No changes to scores or constraints.

### Scenario 2: Rate Cuts / Risk-On
- **Probability:** 25%
- **Description:** Fed cuts rates aggressively. Equity rally, bond prices rise, yields compress.
- **Score adjustments:**
  - All equity returns (US Equity + Intl Equity groups) × 1.5 *(was 1.3)*
  - All equity volatility (US Equity + Intl Equity groups) × 0.8 *(was 0.9)*
  - All bond yields (Bonds group) × 0.5 *(was 0.7)*
  - All Sector returns (Sectors group) × 1.4
- **Score overrides:**
  - VGLT return → +10.0% *(was +8.0%)* (duration benefit from rate cuts)
  - VGT return → base × 1.8 (tech leads risk-on rally)

### Scenario 3: Recession / Risk-Off
- **Probability:** 20%
- **Description:** Economic contraction, equity drawdown, flight to safety.
- **Score adjustments:**
  - All equity returns (US Equity + Intl Equity groups) × 0.2 *(was 0.4)*
  - All equity volatility (US Equity + Intl Equity groups) × 1.8 *(was 1.5)*
  - All Sector returns (Sectors group) × 0.2 *(was 0.4)*
  - All Sector volatility (Sectors group) × 1.8 *(was 1.5)*
  - All Alternative returns (Alternatives group) × 0.5
- **Score overrides:**
  - VGSH return → +4.5% (flight to safety)
  - BND return → +5.0% *(was +4.0%)* (flight to quality)
  - VGLT return → +7.0% (duration rally as rates plunge)
  - HYG return → -4.0% *(was -2.0%)* (credit spreads blow out)
  - HYG volatility → base × 1.8
  - EMB return → -5.0% *(was -2.0%)* (EM capital flight)
  - EMB volatility → base × 1.8
  - GLD return → base × 1.3 (safe haven bid)

### Scenario 4: Inflation Surge
- **Probability:** 25%
- **Description:** Sticky inflation returns. Commodities rally, nominal bonds hurt, equities mixed.
- **Score adjustments:**
  - All equity returns (US Equity + Intl Equity groups) × 0.6 *(was 0.8)*
  - All equity volatility (US Equity + Intl Equity groups) × 1.3
  - All bond returns (Bonds group) × 0.3
  - All bond yields (Bonds group) × 1.2 *(was 1.1)*
- **Score overrides:**
  - GLD return → base × 2.0 *(was 1.5)* (gold as inflation hedge)
  - GSG return → base × 2.0 *(was 1.5)* (commodities rally)
  - DBA return → base × 2.0 *(was 1.5)* (agriculture rally)
  - TIP return → +8.0% *(was +6.0%)* (inflation protection)
  - BND return → -5.0% *(was -3.0%)* (nominal bonds crushed)
  - VGLT return → -12.0% *(was -8.0%)* (long duration devastated)
  - VDE return → base × 1.5 (energy benefits from inflation)

## Deliverables

1. **Per-scenario optimization:** Find Pareto-optimal portfolios for each scenario independently.
2. **Robustness analysis:** Which ETFs appear in optimal portfolios across ALL scenarios? Which are scenario-specific? Use the robustness tiers (core/common/marginal).
3. **Curated strategies:** For each scenario, identify Growth, Balanced, Income, and Safety portfolios.
4. **Cross-scenario comparison:** How do the curated strategies change across scenarios? What shifts?
5. **Interpretation:** Explain the tradeoffs, focusing on what changes between scenarios and what stays robust. Quantify marginal costs where possible. Note inflection points from tradeoff analysis.

Write all results (per-scenario solution data, curated strategies, interpretation text, and any issues encountered) to a markdown file.

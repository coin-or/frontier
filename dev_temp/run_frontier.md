# ETF Portfolio Allocation -- Frontier Demo Run

**Date:** 2026-04-13
**Problem ID:** f768a4f1-4fcc-4282-ac66-31735487582a
**Run ID:** 03b0b2f4-a1fa-4d93-9ee2-7a3f8f15d5e2

---

## Problem Setup

- **25 ETFs** across US equity, international equity, bonds, REITs, commodities, sectors
- **Approach:** Proportional (% allocation summing to 100%)
- **3 Objectives:**
  - Expected Return (maximize) -- ann_return_5yr_pct
  - Volatility (minimize) -- ann_volatility_5yr_pct
  - Dividend Yield (maximize) -- dividend_yield_pct
- **4 Constraints:**
  - Volatility cap at 20%
  - Max 2 sector ETFs (VGT/VHT/VDE/VFH)
  - Max 2 alternatives (VNQ/GLD/GSG)
  - Cardinality: min 4, max 12

---

## Verification Points

### _skill_guidance Auto-Injection

| Phase | Triggered? | Skill Injected | Reason |
|-------|-----------|----------------|--------|
| model create | YES | data_collection | "Problem created. Use this guide when entering scores." |
| scores 100% | YES | optimization_strategy | "Score matrix is 100% complete. Use this guide before running solve." |
| solve complete | YES | solution_interpreter | "Optimization complete. Use this guide to present results." |

All three phase transitions triggered `_skill_guidance` auto-injection successfully.

### String Options on Create

YES -- passed options as `["VOO", "VTV", ...]` string array. All 25 options created correctly.

---

## Solve Results

- **Pareto solutions found:** 166
- **Mode:** fast
- **Algorithm:** NSGA-II (3 objectives)
- **Hypervolume (normalized):** 0.4593
- **Spacing CV:** 0.67
- **Binding constraint:** Volatility <= 20.0 (extreme value: 19.91)

### Objective Ranges

| Objective | Min | Max | Range |
|-----------|-----|-----|-------|
| Expected Return | 2.41% | 19.75% | 17.34% |
| Volatility | 3.66% | 19.91% | 16.25% |
| Dividend Yield | 0.43% | 6.44% | 6.01% |

### Correlations

| Pair | Correlation | Interpretation |
|------|-------------|----------------|
| Expected Return vs Volatility | +0.94 | Strong positive -- higher returns come with higher volatility |
| Expected Return vs Dividend Yield | -0.88 | Strong negative -- growth and income are opposing goals |
| Volatility vs Dividend Yield | -0.69 | Moderate negative -- income-focused portfolios tend to be less volatile |

### Option Coverage (how many of 166 solutions include each ETF)

| ETF | Solutions | ETF | Solutions |
|-----|-----------|-----|-----------|
| HYG | 166 (100%) | GLD | 155 (93%) |
| VGSH | 123 (74%) | VDE | 114 (69%) |
| VOO | 87 (52%) | TIP | 76 (46%) |
| EMB | 75 (45%) | VGLT | 61 (37%) |
| VUG | 58 (35%) | BND | 54 (33%) |
| VTV | 44 (27%) | SCHD | 38 (23%) |
| VYM | 36 (22%) | VXUS | 35 (21%) |
| LQD | 21 (13%) | VFH | 20 (12%) |
| VWO | 15 (9%) | VHT | 15 (9%) |
| VGT | 11 (7%) | VO | 10 (6%) |
| VEA | 9 (5%) | BNDX | 10 (6%) |
| GSG | 7 (4%) | VNQ | 3 (2%) |
| VB | 2 (1%) | | |

**Key insight:** HYG appears in every single solution. GLD appears in 93%. These are the workhorses of the Pareto frontier.

---

## Curated Strategies

### 1. Growth (Max Return)

- **Solution ID:** 1 | **Signature:** 99c88b9a39db
- **Expected Return:** 19.75% | **Volatility:** 19.70% | **Dividend Yield:** 1.22%

| ETF | Allocation |
|-----|-----------|
| GLD | 57% |
| VDE | 38% |
| HYG | 3% |
| VFH | 1% |
| VYM | 1% |

Concentrated in gold and energy. Near the volatility cap at 19.7%. Sacrifices nearly all dividend income for maximum capital appreciation.

---

### 2. Balanced (Middle Ground)

- **Solution ID:** 99 | **Signature:** ae92a455bb9f
- **Expected Return:** 8.50% | **Volatility:** 10.71% | **Dividend Yield:** 4.74%

| ETF | Allocation |
|-----|-----------|
| HYG | 69% |
| GLD | 25% |
| VDE | 3% |
| VXUS | 1% |
| TIP | 1% |
| EMB | 1% |

Trades off across all three objectives. Core in high-yield bonds with a gold hedge and small energy/international tilt.

---

### 3. Income (Max Dividend Yield)

- **Solution ID:** 140 | **Signature:** c073f79768c3
- **Expected Return:** 3.95% | **Volatility:** 8.34% | **Dividend Yield:** 6.44%

| ETF | Allocation |
|-----|-----------|
| HYG | 93% |
| EMB | 2% |
| VOO | 1% |
| VUG | 1% |
| BND | 1% |
| VGLT | 1% |
| TIP | 1% |

Massively concentrated in high-yield bonds. Achieves the highest dividend yield on the frontier at 6.44%, with moderate volatility.

---

### 4. Safety (Min Volatility)

- **Solution ID:** 164 | **Signature:** 0e688a6e0755
- **Expected Return:** 2.50% | **Volatility:** 3.66% | **Dividend Yield:** 3.99%

| ETF | Allocation |
|-----|-----------|
| VGSH | 84% |
| HYG | 10% |
| TIP | 2% |
| BND | 1% |
| VUG | 1% |
| GLD | 1% |
| VDE | 1% |

Dominated by short-term treasuries. Achieves the lowest volatility on the frontier at 3.66% while still maintaining reasonable yield.

---

## Strategy Comparison Summary

| Metric | Growth | Balanced | Income | Safety |
|--------|--------|----------|--------|--------|
| Expected Return | **19.75%** | 8.50% | 3.95% | 2.50% |
| Volatility | 19.70% | 10.71% | 8.34% | **3.66%** |
| Dividend Yield | 1.22% | 4.74% | **6.44%** | 3.99% |
| # Holdings | 5 | 6 | 7 | 7 |
| Top Holding | GLD (57%) | HYG (69%) | HYG (93%) | VGSH (84%) |

### Shared Option Across All Extremes

**HYG (High Yield Bond)** appears in every single Pareto solution -- it is the universal building block of this portfolio optimization.

---

## Frontier Visualization

```
--- Frontier Scatter: Expected Return vs Dividend Yield (r=-0.88) ---

  Dividend Yield (up = better)
    6.44 |    *                                              |  [Income]
         |  ... ...                                         |
         |   ..  ..... .                                    |
         |     .    .. ...                                  |
         | ....  .         ...                              |
         | ..           ...B  ..  . .                       |  [Balanced]
         |..   ..  .         .     .                        |
         |. .     . . .       . .. .  .                     |
         |       ..      .  .  ..   ...  .                  |
         |            ..           .  ... . .               |
         |                 .      .  . . .   ..    .        |
         |                   .             . ....  ..       |
         |                           . .  ...  . . ...      |
         |                                   .. .. .  ... . |
         |                                        ..  . ...*|  [Growth]
    0.43 |                                           ... .  |
         +--------------------------------------------------+ (right = better)
         2.41                                          19.7
                          Expected Return

  * extremes  B balanced  . frontier
```

---

## Diagnostics

- **12 dominated options** detected during scoring (dominated on all 3 objectives by at least one other option). These still participate in portfolios due to proportional blending effects.
- **Binding constraint:** Volatility cap at 20% is binding (extreme reaches 19.91%), meaning the Growth strategy is right at the constraint boundary.
- **Score variance:** Expected Return (43.27) and Volatility (31.80) have high variance and drive differentiation well. Dividend Yield variance (3.67) is lower but still meaningful.

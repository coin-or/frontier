# ETF Portfolio Demo — Results

**Run date:** 2026-04-12
**Problem:** ETF Portfolio Allocation
**Problem ID:** ca897b3a-726e-4266-abd5-195eb48c07d9
**Run ID:** 89994162-5751-43cb-bbfc-a285ca82198b
**Mode:** fast
**Solutions found:** 166 Pareto-optimal portfolios

---

## Problem Setup

- **Approach:** Proportional (% allocation summing to 100%)
- **Options:** 25 ETFs across US equity, intl equity, bonds, alternatives, sectors
- **Objectives:** Expected Return (max), Volatility (min), Dividend Yield (max)
- **Constraints:** Vol cap 20%, max 2 sector ETFs, max 2 alternatives, 4-12 holdings
- **Data:** 5yr monthly returns (2021-05 to 2026-04)

## Objective Ranges Across Frontier

| Objective | Min | Max | Unit |
|-----------|-----|-----|------|
| Expected Return | 2.15 | 19.67 | % annualized |
| Volatility | 3.33 | 19.94 | % ann std dev |
| Dividend Yield | 0.29 | 6.44 | % trailing 12mo |

## Key Tradeoffs

| Pair | Correlation | Interpretation |
|------|-------------|----------------|
| Return vs Volatility | r = +0.94 | Very strong — higher returns require proportionally more risk |
| Return vs Dividend Yield | r = -0.87 | Strong inverse — growth and income strongly oppose |
| Volatility vs Dividend Yield | r = -0.67 | Moderate inverse — low-vol portfolios tend toward income |

All three objectives genuinely conflict, producing a rich 3-way Pareto frontier.

## Curated Strategies

### 1. Growth (Solution 1)
- **Return:** 19.67% | **Vol:** 18.78% | **Yield:** 0.86%
- **Allocations:** GLD 68%, VDE 28%, VEA 1%, BND 1%, VGSH 1%, VGT 1%
- **Signature:** `697b85d7f388`
- **Character:** Commodities-heavy growth. Gold and energy drive returns, near-zero income. Highest risk on the frontier but within the 20% vol cap.

### 2. Balanced (Solution 100)
- **Return:** 8.61% | **Vol:** 10.42% | **Yield:** 4.55%
- **Allocations:** HYG 67%, GLD 29%, VGSH 2%, VEA 1%, SCHD 1%
- **Signature:** `abf8c8559118`
- **Character:** High-yield bonds + gold blend. Moderate everything — sits near the center of all three objective ranges. Good starting point for most investors.

### 3. Income (Solution 140)
- **Return:** 4.16% | **Vol:** 8.35% | **Yield:** 6.44%
- **Allocations:** HYG 96%, SCHD 2%, VEA 1%, VGSH 1%
- **Signature:** `d8c878b96490`
- **Character:** Concentrated high-yield bond portfolio. Maximum income at the cost of return. Low-moderate volatility. Essentially a single-asset-class bet on HYG.

### 4. Safety (Solution 166)
- **Return:** 2.15% | **Vol:** 3.33% | **Yield:** 3.76%
- **Allocations:** VGSH 88%, BNDX 6%, HYG 3%, SCHD 1%, VEA 1%, EMB 1%
- **Signature:** `2a999abcaef4`
- **Character:** Short-term treasury anchor. Minimal risk, modest income, very low return. Capital preservation strategy.

## Shared Options Across All Strategies

VEA and VGSH appear in all 4 curated solutions — they serve as universal anchor positions regardless of strategy.

## Observations

1. **GLD dominance in growth:** Gold's 20% ann return over the 5yr period (driven by 2024-2026 rally) makes it the primary return driver, not equities.
2. **HYG dominance in income/balanced:** High-yield bonds at 6.7% yield with only 7.9% vol make them the income engine — they crowd out other bond ETFs.
3. **Concentration risk:** All curated strategies are concentrated in 1-2 assets. The cardinality constraint (min 4) is technically met but allocations are lopsided.
4. **Equities underrepresented:** Traditional equity ETFs (VOO, VUG, etc.) don't appear meaningfully in any curated portfolio — GLD and VDE outperform them on return, while bonds beat them on yield.
5. **Linear vol simplification:** Since volatility is averaged (not covariance-based), there's no diversification benefit recognized by the optimizer. A covariance matrix would likely produce more diversified portfolios.

## Tradeoff Quantification

- Moving from Safety → Balanced: gains 6.5pp return, costs 7.1pp vol, gains 0.8pp yield
- Moving from Balanced → Growth: gains 11.1pp return, costs 8.4pp vol, loses 3.7pp yield
- Moving from Safety → Income: gains 2.0pp return, costs 5.0pp vol, gains 2.7pp yield

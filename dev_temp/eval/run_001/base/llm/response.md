# Portfolio Optimization: Tradeoff Analysis

## The Three-Way Tradeoff

This analysis explored 8 portfolio configurations across 30 ETFs, optimizing three objectives simultaneously: expected return, volatility (risk), and dividend yield. The central finding is that these objectives create sharp, quantifiable tradeoffs.

## Key Tradeoff: Return vs. Safety

Moving from Safety (2.80% return, 6.45% vol) to Growth (16.28% return, 17.86% vol):
- **You gain:** 13.5 percentage points of annual return
- **You pay:** 11.4 percentage points of additional volatility
- **You lose:** 2.8 percentage points of dividend yield (4.07% down to 1.28%)

The exchange rate is roughly **1.18 points of return per 1 point of vol** -- but this comes at the cost of nearly 3 points of yield.

## Key Tradeoff: Yield vs. Return

Moving from Growth (16.28% return, 1.28% yield) to Income (2.69% return, 4.84% yield):
- **You gain:** 3.6 percentage points of dividend yield
- **You pay:** 13.6 percentage points of expected return
- **Exchange rate:** Each extra point of yield costs about 3.8 points of return

This is steep. High-yield ETFs (HYG at 5.88%, EMB at 5.11%) carry low returns, so loading up on yield means accepting capital appreciation well below equity-market levels.

## The Balanced Middle Ground

The Balanced portfolio (10.47% return, 13.02% vol, 2.55% yield) sits in the middle of the frontier. Compared to Growth, it gives up 5.8 points of return but gains 1.3 points of yield and reduces vol by 4.8 points. It represents the most diversified approach across all asset groups.

The Growth-Income Blend (8.90% return, 14.10% vol, 3.45% yield) is an alternative middle ground that tilts more toward yield. It earns 0.9 points more yield than Balanced but costs 1.6 points of return.

## What Dominates What

- **Max Return Push** (17.58% return, 19.35% vol, 0.76% yield) is the highest-return portfolio. It edges out Aggressive Growth by 0.02 points of return with lower vol (19.35 vs 19.07) but worse yield (0.76 vs 1.13). Neither clearly dominates the other.
- **Safety** dominates High Yield Safety on return (2.80 vs 3.11% -- actually HYS is slightly better here) but wins on vol (6.45 vs 7.62). HYS wins on yield (4.65 vs 4.07). Neither dominates.
- No solution clearly dominates another across all three objectives -- they each represent legitimate tradeoff positions.

## Recurring ETFs Across Strategies

| ETF | Appearances | Role |
|-----|-------------|------|
| GLD | 4 of 8 | High-return anchor (19.88%) with moderate vol |
| HYG | 5 of 8 | Yield anchor (5.88%) with low vol (7.89%) |
| VGSH | 4 of 8 | Vol reducer (2.20%) with decent yield (3.95%) |
| DBA | 4 of 8 | Efficient return (10.71%) at low vol (12.20%) with yield (3.35%) |
| VOO | 4 of 8 | Reliable equity return (11.98%) at moderate vol |
| SCHD | 4 of 8 | Yield-oriented equity (3.44% yield, 7.45% return) |

GLD is the standout performer: 19.88% return at only 15.91% vol makes it the most efficient return source. Its zero yield is the only drawback. DBA (agriculture) is an underappreciated pick: moderate return, low vol, and solid yield.

## Practical Takeaway

The investor's choice reduces to: how much return are you willing to sacrifice for lower risk and/or higher income?

- **If you want 15%+ returns**, accept ~18% vol and under 1.5% yield. The portfolio will be concentrated in GLD, VDE, VGT, and VOO.
- **If you want 4%+ yield**, accept returns under 3%. The portfolio will lean heavily into bonds (HYG, EMB, VGSH) and high-yield international equities (EWJ).
- **If you want both decent return and yield**, the Balanced or Growth-Income Blend portfolios achieve 9-10% return with 2.5-3.5% yield at 13-14% vol.

## Important Limitation

All volatility figures use weighted-average approximation, not covariance-based calculation. This overstates portfolio risk because it ignores diversification benefits from imperfect correlations between holdings. A covariance-based approach would show lower actual portfolio volatility, especially for the more diversified portfolios (Balanced and Growth-Income Blend with 8 holdings across multiple asset classes). The ranking of portfolios by risk should be directionally correct, but the absolute vol numbers are conservative.

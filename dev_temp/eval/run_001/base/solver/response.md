# Portfolio Tradeoff Analysis

## The Tradeoff Space

This optimization explored 30 ETFs across US equities, international, bonds, sectors, and alternatives, producing 38 Pareto-optimal portfolios. Every solution on the frontier is non-dominated -- improving one objective requires sacrificing another.

The frontier spans:
- **Return:** 2.22% to 18.33% (an 8x range)
- **Volatility:** 4.24% to 15.91%
- **Dividend Yield:** 0.79% to 5.10%

## Marginal Costs: What You Give Up

**Return vs. Volatility:** Moving from the Safety portfolio (3.43% return, 4.24% vol) toward the Growth portfolio (18.33% return, 15.91% vol), each additional 1% of return costs roughly 0.79% additional volatility. This ratio is roughly linear through the middle of the frontier but accelerates at the extremes -- the last 3% of return (from ~15% to 18.33%) costs disproportionately more volatility.

**Return vs. Yield:** The return-yield tradeoff is steep. Moving from Income (5.10% yield, 2.22% return) to Growth (1.22% yield, 18.33% return), you give up approximately 0.24% of yield for each 1% of return gained. High-yield bond allocations (HYG, EMB) are the primary yield source, and they get displaced by growth-oriented holdings (VGT, VDE).

**Yield vs. Volatility:** Pursuing yield is not free. The Income portfolio (5.10% yield) carries 7.10% volatility -- nearly double the Safety portfolio's 4.24%. The marginal cost is roughly 0.54% vol per 1% yield above the baseline.

## Inflection Points

1. **The 10% return threshold.** Below ~10% return, volatility stays contained (5-8%). Above 10%, volatility escalates sharply. The Balanced portfolio (9.42% return, 8.31% vol) sits near this inflection -- pushing beyond it means accepting disproportionate risk.

2. **The 4% yield ceiling.** Yield above ~4% requires heavy concentration in HYG and EMB (high-yield and emerging market bonds), which introduces credit risk and limits return potential. Most portfolios yielding above 4% return less than 6%.

3. **The 4-holding floor.** Several high-conviction portfolios (Growth, Balanced) sit at the minimum 4 holdings, meaning they rely on concentration for performance. Diversification-minded investors should look at solutions with 6-8 holdings, which sacrifice 2-4% return for broader exposure.

## Structural Patterns

- **HYG is the workhorse.** It appears in 30 of 38 solutions. It provides yield (5-6%) while keeping volatility moderate. Near-cap (29-31%) allocations to HYG are common.
- **VGSH anchors stability.** Short-term treasuries appear in 24 of 38 solutions, providing low-vol ballast.
- **VGT and VDE drive return.** Tech and energy dominate the high-return end. They rarely appear together at large weights due to their combined volatility.
- **GLD provides uncorrelated return.** Gold appears in 22 solutions, typically at or near the 30% cap, providing return without proportional volatility contribution due to low correlation with equities.
- **DBA is the alternative of choice.** Agriculture commodities appear in 26 solutions, offering diversification with moderate return contribution.

## Four Representative Strategies

| Strategy | Return | Volatility | Yield | Holdings | Character |
|----------|--------|------------|-------|----------|-----------|
| Growth | 18.33% | 15.91% | 1.22% | 4 | Concentrated, tech/energy/gold |
| Balanced | 9.42% | 8.31% | 3.99% | 4 | Yield + energy + commodities |
| Safety | 3.43% | 4.24% | 4.39% | 7 | Bond-heavy, diversified |
| Income | 2.22% | 7.10% | 5.10% | 5 | EM/HY bond-heavy, yield-maximizing |

Note: Income accepts higher volatility than Safety despite lower return -- this is the cost of maximizing yield. Safety sacrifices yield to minimize risk.

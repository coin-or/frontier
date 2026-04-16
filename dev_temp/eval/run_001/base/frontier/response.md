# Portfolio Tradeoff Analysis

## The Landscape

Optimizing across 30 ETFs for return, risk, and income produces a rich frontier of 100 Pareto-optimal portfolios. The three objectives are tightly coupled: return and volatility move together (r=+0.93), return and yield oppose (r=-0.93), and volatility and yield partially align (r=-0.79). This means there are no free lunches -- every gain in one dimension comes at a measurable cost in another.

The frontier spans:
- **Expected Return**: 3.0% to 17.3%
- **Volatility** (quadratic, covariance-based): 4.2% to 14.5%
- **Dividend Yield**: 1.5% to 4.9%

## What You Give Up to Get What You Want

**Pushing for higher returns**: Moving from the Balanced portfolio (9.4% return, 7.5% vol) to the Growth portfolio (16.3% return, 13.3% vol) gains 6.9 percentage points of return but costs 5.8 points of additional volatility and 1.6 points of yield. That is roughly 0.84 points of extra volatility per point of return gained.

However, this rate is not constant. There is a sharp inflection point around 13% return (Solution 23). Below that threshold, each extra point of return costs modest volatility. Above it, the marginal cost accelerates dramatically -- the last few points of return above 13% require disproportionately more risk. If you are aiming for growth, the 12-13% return range offers the most favorable risk-return tradeoff.

**Pushing for higher yield**: Moving from Balanced (3.7% yield) to Income (4.9% yield) gains 1.3 points of yield but costs 5.0 points of return. The yield inflection is around 4.4% (Solution 84) -- below that, yield increases are relatively cheap. Above it, each additional tenth of a percent of yield costs multiple points of return.

**Pushing for lower risk**: The Safety portfolio achieves 4.2% volatility, roughly half that of the Balanced portfolio. The cost is 6.0 points of return (from 9.4% down to 3.4%). Interestingly, yield barely changes -- Safety still delivers 4.4% yield because the low-volatility bond ETFs (VGSH, BND, HYG) are themselves high-yielding.

## Diversification is Powerful Here

A key finding: the covariance-based volatility calculation shows substantial diversification benefits. The Safety portfolio holds 10 ETFs with individual volatilities ranging from 2.2% to 19.7%, yet the portfolio volatility is only 4.2%. This is because bonds and equities have negative covariances in this dataset -- when stocks fall, bonds tend to rise, dampening overall portfolio swings.

Even the Growth portfolio benefits: despite holding VDE (26.6% standalone vol) and GLD (15.9% vol) at 30% each, the portfolio volatility is only 13.3% -- well below what a simple weighted average would suggest. The 20% volatility constraint never binds because diversification naturally keeps portfolios below it.

## What Drives the Frontier

Three ETFs appear in every curated portfolio: EWJ (Japan), HYG (High Yield Bonds), and DBA (Agriculture). These are universal building blocks because they combine decent yields with correlation structures that aid diversification.

The primary differentiator across strategies is VDE (Energy) -- it enters portfolios as return requirements increase. At 22.1% annualized return over 5 years, VDE is by far the highest-returning ETF, but at 26.6% volatility, it demands careful sizing. Growth portfolios max it out at 30%; the Balanced portfolio holds 20%; Income and Safety exclude it entirely.

GLD (Gold) is the second key differentiator -- high return (19.9%) with near-zero correlation to equities, making it a risk-efficient return booster. It appears at 30% in Growth, 11% in Balanced, and only trace amounts in Safety.

## Where to Go From Here

The four curated strategies cover the major archetypes. Some natural questions to explore further:

- **Between Balanced and Growth**: The 10-13% return range offers an attractive middle ground with moderate volatility. Solutions in this range tend to hold VDE at 15-25% with larger VGSH/HYG buffers.
- **Concentration risk**: Several strategies are heavily concentrated in 2-3 positions at the 30% cap. If concentration is a concern, tightening the max allocation constraint from 30% to 20% would spread holdings but narrow the return range.
- **Sector vs alternatives tradeoff**: The optimizer strongly favors VDE (energy) over other sector ETFs, and GLD/DBA/IGF over other alternatives. The sector and alternative group limits (max 3 each) are rarely binding because the optimizer naturally picks the top performers.

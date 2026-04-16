# Tradeoff Landscape: 30-ETF Portfolio Across Four Macro Regimes

We optimized allocations across 30 ETFs for three simultaneous objectives — expected return, portfolio volatility (computed quadratically from the covariance matrix), and dividend yield — under your constraints (≤30% per ETF, vol ≤20%, ≤3 sectors, ≤3 alternatives, 4-12 holdings). Four macro scenarios were stressed independently: Base (30%), Rate Cuts (25%), Recession (20%), Inflation (25%).

## The Shape of the Tradeoff

The three objectives conflict meaningfully — no portfolio wins on all three. In the base case:

- Push to **maximum return (18.6%)** and you pay: vol climbs to 15.8, yield collapses to ~1%. The growth portfolio becomes a concentrated bet on tech (VGT), energy (VDE), gold (GLD), and commodities (GSG).
- Push to **minimum volatility (4.2)** and return drops to 3.3%. The safety corner is short Treasuries (VGSH, BND, TIP) plus enough HYG and DBA to keep yield above 4%.
- Push to **maximum yield (4.9%)** and you're concentrated in credit (HYG, EMB) and Japan equity (EWJ). Return sits at ~4.7%, vol at ~7.1.

Return and Yield are strongly opposed in the base case (r = −0.89). Growth options (VGT, VDE, GLD, GSG) pay little dividend; income options (HYG, EMB) grow slowly.

## What the Frontier Gives Up

From the marginal analysis: the median "cost" of one more return point is about 4.7 units of volatility. But that cost is highly non-linear. There's a clear **inflection at ~11.7% return** — below that, vol-per-return is manageable. Above it, each additional return point costs an order of magnitude more volatility. This is the region where the portfolio becomes dominated by a handful of concentrated bets.

The yield axis has its own inflection at ~5% return — past that point, moving up in yield costs almost nothing in return (you've already given up growth).

Practically, unless you have a specific need for the extremes, portfolios in the **8-12% return / 5-9% volatility** band offer the best tradeoffs.

## How the Four Scenarios Differ

| | Top Return | Top Yield achievable | Min Vol floor |
|---|---|---|---|
| Base | 18.74% | 4.90% | 4.17 |
| Rate Cuts | **25.28%** | 3.85% (compressed) | 4.15 |
| Recession | 12.58% (Treasuries rally) | 5.02% | 4.16 |
| Inflation | **30.05%** (commodities spike) | 5.95% | 4.14 |

The **Safety floor (~4.15 vol)** is nearly identical across all four scenarios — a structural feature of the covariance matrix and the short-Treasury anchor.

The **Growth ceiling** swings wildly: rate-cut growth bets concentrate in equity/sector (VGT, VDE, GLD), while inflation growth bets concentrate in real-asset commodities (GLD + DBA + VDE). Recession growth is paradoxical: the highest-return portfolio is 30% long Treasuries + gold + commodities, because equities take deep cuts while VGLT gets the +7% override.

## The Robust Core

Two options appear in nearly every Pareto solution across every scenario:

- **HYG (high-yield credit)** — 87.5% frequency, avg 18.7% allocation. Anchors yield in every regime.
- **GLD (gold)** — 71.3% frequency, avg 18.2% allocation. Hedge against everything — rallies in recession, surges in inflation, and still pulls weight in base and rate-cut scenarios.

Broad-base holdings (appear in all 4 scenarios, meaningful weight): **VGSH, DBA, VGLT, BND, EMB, EWJ, VGT**. These form the robust diversification backbone.

**Scenario-specific picks:** VDE (energy) shines in Base, Rate Cuts, and Inflation but not Recession. Recession Pareto solutions uniquely pull in defensive/deep-value names (MCHI, VB) via the rotation logic.

## What to Ask Next

A few directions that would sharpen the picture:

1. **Probability-weighted robustness.** The ideal-point expected values (Return 21.97, Vol 4.16, Yield 4.93) are unachievable as a single solution — they pick the best per scenario. Would you want a single portfolio that maximizes probability-weighted return subject to each scenario's vol staying ≤20%?
2. **Curated strategy cross-test.** We curated Growth/Balanced/Income/Safety per scenario. A natural next step: take the Base-Balanced portfolio and compute its objective values under each of the other three scenarios. That shows fragility explicitly — is the Base-Balanced still acceptable under Recession?
3. **Constraint binding sensitivity.** Several curated portfolios hit the 30% max-allocation wall (VGT, VDE, GLD, HYG, EMB in various scenarios). Raising to 35% could meaningfully expand the upper return frontier; tightening to 25% would force more diversification. Which direction matches your thesis?
4. **Volatility bound revisited.** The ≤20% portfolio vol constraint is not binding in any scenario — actual Pareto maxima all sit below 18%. The quadratic aggregation plus diversification does most of the work. Consider whether you'd prefer a tighter bound (say 12%) to narrow the search.

## A Note on the Quadratic Volatility Model

Volatility is computed as sqrt(w^T · Σ · w) using the 30×30 annualized covariance matrix. The covariance matrix was held constant across scenarios — only individual option returns and yields were adjusted per scenario. This models correlation structure as time-invariant over the stress horizon. In a true recession, correlations between risk assets typically rise toward 1 (the "diversification breakdown") — if you want to stress-test that effect, we'd need to override the covariance matrix per scenario, which is not currently supported by the Scenario schema. See issues.md.

# Run 2: 30-ETF Portfolio Optimization (pymoo NSGA-III)

## 1. Setup Summary

| Metric | Value |
|--------|-------|
| Script | `pymoo_30_etf.py` (~267 lines) |
| Dependencies | `pymoo`, `numpy`, `json` |
| Algorithm | NSGA-III, 3 objectives, Das-Dennis ref dirs (91 points) |
| Population | 200, 500 generations, seed=42 |
| Decision variables | 30 integer vars (0-100), sum=100 |
| Solve time | **8.7 seconds** |

## 2. Results Summary

| Metric | Min | Max |
|--------|-----|-----|
| Expected Return | 3.75% | 14.17% |
| Volatility | 9.23% | 17.43% |
| Dividend Yield | 1.78% | 4.53% |
| **Pareto-optimal solutions** | **45** | |

All 45 solutions satisfy: 4-12 holdings, each >= 1%, sum = 100%, volatility <= 20%, max 3 sector ETFs, max 3 alternative ETFs.

## 3. Curated Strategies

### Overview

| Strategy | Return | Volatility | Yield | Holdings |
|----------|--------|------------|-------|----------|
| **Growth** | 14.17% | 16.87% | 1.78% | 12 |
| **Balanced** | 9.40% | 13.30% | 3.33% | 12 |
| **Income** | 4.12% | 10.80% | 4.53% | 12 |
| **Safety** | 4.93% | 9.23% | 3.70% | 12 |

### Growth (Highest Return)

Targets maximum capital appreciation. Accepts higher volatility and sacrifices dividend income.

| ETF | Alloc | Category |
|-----|-------|----------|
| GLD | 23% | Gold |
| VDE | 12% | Energy |
| GSG | 11% | Commodities |
| IGF | 11% | Infrastructure |
| VOO | 8% | US Large Cap Blend |
| HYG | 8% | High Yield Bond |
| VGT | 7% | Technology |
| VTV | 5% | US Large Cap Value |
| VEA | 5% | Intl Developed |
| VGK | 4% | Europe |
| SCHD | 3% | Dividend Quality |
| VGSH | 3% | Short-Term Treasury |

### Balanced (Center of Frontier)

Sits near the geometric center of the Pareto surface. Moderate on all three objectives.

| ETF | Alloc | Category |
|-----|-------|----------|
| VDE | 13% | Energy |
| DBA | 12% | Agriculture |
| VGSH | 11% | Short-Term Treasury |
| HYG | 9% | High Yield Bond |
| VPU | 9% | Utilities |
| GLD | 9% | Gold |
| SCHD | 7% | Dividend Quality |
| EWJ | 7% | Japan |
| TIP | 7% | TIPS |
| EMB | 7% | EM Bond |
| IGF | 6% | Infrastructure |
| BND | 3% | US Aggregate Bond |

### Income (Highest Yield)

Maximizes dividend income. Anchored in high-yield bonds and income-producing alternatives.

| ETF | Alloc | Category |
|-----|-------|----------|
| HYG | 28% | High Yield Bond |
| EMB | 12% | EM Bond |
| VGSH | 11% | Short-Term Treasury |
| DBA | 11% | Agriculture |
| SCHD | 7% | Dividend Quality |
| EWJ | 5% | Japan |
| BND | 5% | US Aggregate Bond |
| VGLT | 5% | Long-Term Treasury |
| VNQI | 5% | Intl REITs |
| VPU | 4% | Utilities |
| VNQ | 4% | US REITs |
| VEA | 3% | Intl Developed |

### Safety (Lowest Volatility)

Minimizes portfolio swings. Heavy on short-duration bonds with a diversified equity/alternative tail.

| ETF | Alloc | Category |
|-----|-------|----------|
| VGSH | 21% | Short-Term Treasury |
| HYG | 13% | High Yield Bond |
| BND | 9% | US Aggregate Bond |
| TIP | 9% | TIPS |
| EMB | 9% | EM Bond |
| DBA | 9% | Agriculture |
| VOO | 6% | US Large Cap Blend |
| VTV | 6% | US Large Cap Value |
| SCHD | 5% | Dividend Quality |
| VGLT | 5% | Long-Term Treasury |
| GLD | 5% | Gold |
| IGF | 3% | Infrastructure |

## 4. Solution Interpretation

The optimizer searched 100,000 candidate portfolios across 500 generations and converged on 45 distinct Pareto-optimal allocations. No single portfolio dominates all three objectives simultaneously -- every improvement on one metric comes at a measurable cost elsewhere. Here is how the tradeoffs play out.

**The extremes frame the decision space.** Growth delivers 14.17% annualized return but accepts 16.87% volatility and produces only 1.78% yield. Safety compresses volatility to 9.23% (nearly half) but return drops to 4.93%. Income pushes yield to 4.53% but return falls to 4.12%. These are the outer walls of what is feasible under the constraints.

**The cost of chasing return.** Moving from Safety to Growth buys 9.24 percentage points of additional return. The price is 7.64 points of additional volatility and 1.92 points of lost yield. Put differently, each additional point of return costs roughly 0.83 points of volatility -- not a linear exchange, but a useful heuristic.

**Income and safety are neighbors, not twins.** Safety (4.93% return, 9.23% vol, 3.70% yield) and Income (4.12% return, 10.80% vol, 4.53% yield) have similar return profiles, but Income accepts 1.57 points more volatility to capture 0.83 points more yield. The Income portfolio concentrates in credit-sensitive instruments (HYG at 28%), making it more exposed to credit spreads than the bond-ladder approach in Safety.

**Balanced occupies useful middle ground.** At 9.40% return, 13.30% vol, and 3.33% yield, the Balanced portfolio captures 66% of Growth's return at 79% of Growth's volatility, while still generating nearly double Growth's yield. It is the only curated strategy that meaningfully participates in all three objectives without an extreme sacrifice.

**Structural patterns across strategies.** Gold (GLD) and short-term Treasuries (VGSH) appear in all four strategies, playing opposite roles: GLD drives return, VGSH dampens volatility. High-yield bonds (HYG) appear everywhere because they uniquely combine moderate return with high yield at contained volatility. Agriculture (DBA) surfaces as a diversifier across Balanced, Income, and Safety due to its low correlation profile and 3.35% yield.

**What is absent is informative.** No strategy allocates to MCHI (China, -4.96% return) or holds more than modest positions in mid/small cap US equity (VO, VB). The optimizer consistently avoids high-volatility assets that do not compensate with return or yield.

Which of these profiles -- or which region of the tradeoff space -- aligns with what you are trying to accomplish?

## 5. Raw Pareto Front Data

```json
{"solutions": [{"return": 8.5, "vol": 12.12, "yield": 3.38}, {"return": 6.29, "vol": 10.0, "yield": 3.42}, {"return": 5.77, "vol": 9.52, "yield": 3.51}, {"return": 14.17, "vol": 16.87, "yield": 1.78}, {"return": 5.7, "vol": 10.94, "yield": 4.01}, {"return": 3.75, "vol": 9.82, "yield": 4.41}, {"return": 12.69, "vol": 15.48, "yield": 2.38}, {"return": 7.71, "vol": 11.91, "yield": 3.7}, {"return": 11.29, "vol": 16.76, "yield": 3.09}, {"return": 11.5, "vol": 14.96, "yield": 2.85}, {"return": 8.65, "vol": 12.74, "yield": 3.74}, {"return": 8.9, "vol": 15.29, "yield": 3.8}, {"return": 12.26, "vol": 17.37, "yield": 2.99}, {"return": 7.25, "vol": 10.44, "yield": 3.18}, {"return": 12.69, "vol": 16.66, "yield": 2.75}, {"return": 10.33, "vol": 12.42, "yield": 2.65}, {"return": 10.44, "vol": 13.54, "yield": 2.96}, {"return": 11.15, "vol": 13.18, "yield": 2.31}, {"return": 5.11, "vol": 9.87, "yield": 4.04}, {"return": 9.34, "vol": 14.29, "yield": 3.66}, {"return": 4.12, "vol": 10.8, "yield": 4.53}, {"return": 5.66, "vol": 11.97, "yield": 4.22}, {"return": 6.02, "vol": 13.19, "yield": 4.21}, {"return": 6.79, "vol": 10.94, "yield": 3.76}, {"return": 11.55, "vol": 14.07, "yield": 2.4}, {"return": 8.27, "vol": 11.25, "yield": 3.0}, {"return": 3.93, "vol": 10.02, "yield": 4.26}, {"return": 6.7, "vol": 11.83, "yield": 4.03}, {"return": 10.46, "vol": 14.62, "yield": 3.27}, {"return": 12.3, "vol": 14.09, "yield": 2.2}, {"return": 4.97, "vol": 11.5, "yield": 4.43}, {"return": 9.04, "vol": 11.51, "yield": 2.75}, {"return": 4.93, "vol": 9.23, "yield": 3.7}, {"return": 4.14, "vol": 9.39, "yield": 4.0}, {"return": 10.35, "vol": 16.05, "yield": 3.52}, {"return": 13.81, "vol": 17.43, "yield": 2.06}, {"return": 3.93, "vol": 9.44, "yield": 4.16}, {"return": 9.4, "vol": 13.3, "yield": 3.33}, {"return": 7.56, "vol": 10.99, "yield": 3.4}, {"return": 7.59, "vol": 13.06, "yield": 3.97}, {"return": 6.77, "vol": 14.33, "yield": 4.2}, {"return": 4.79, "vol": 10.9, "yield": 4.27}, {"return": 9.28, "vol": 12.25, "yield": 2.98}, {"return": 8.26, "vol": 14.37, "yield": 3.92}, {"return": 5.4, "vol": 9.88, "yield": 3.7}]}
```

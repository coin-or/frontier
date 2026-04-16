# Frontier Method: ETF Portfolio Optimization Results

## Run Summary

- **Problem**: 30 ETFs, 3 objectives (Expected Return, Volatility, Dividend Yield), proportional allocation
- **Approach**: Proportional (integer % allocations summing to 100)
- **Algorithm**: NSGA-II (3 objectives)
- **Mode**: Thorough
- **Solve time**: ~10 seconds (Frontier MCP tool)
- **Pareto solutions found**: 100

## Objective Ranges Across Pareto Frontier

| Objective | Min | Max | Direction |
|-----------|-----|-----|-----------|
| Expected Return (%) | 3.03 | 17.27 | Maximize |
| Volatility (%) | 4.23 | 14.54 | Minimize (quadratic) |
| Dividend Yield (%) | 1.55 | 4.95 | Maximize |

## Key Correlations

| Pair | Correlation | Interpretation |
|------|-------------|----------------|
| Return vs Volatility | +0.93 | Strong conflict: higher returns require accepting more volatility |
| Return vs Yield | -0.93 | Strong conflict: growth-oriented ETFs pay lower dividends |
| Volatility vs Yield | -0.79 | Moderate alignment: lower-volatility portfolios tend to have higher yield |

## Extreme Solutions

| Strategy | Return (%) | Volatility (%) | Yield (%) | Holdings |
|----------|-----------|----------------|-----------|----------|
| Max Return (Sol 1) | 17.27 | 14.28 | 1.55 | 9 ETFs: VDE 30%, GLD 30%, IGF 22% |
| Min Volatility (Sol 99) | 3.35 | 4.23 | 4.39 | 10 ETFs: VGSH 30%, HYG 30%, BND 23% |
| Max Yield (Sol 91) | 4.43 | 7.02 | 4.95 | 9 ETFs: EWJ 30%, HYG 30%, EMB 30% |

## Curated Strategies

| Strategy | Return (%) | Volatility (%) | Yield (%) | # Holdings |
|----------|-----------|----------------|-----------|------------|
| Growth | 16.34 | 13.27 | 2.09 | 8 |
| Balanced | 9.38 | 7.52 | 3.66 | 9 |
| Income | 4.43 | 7.02 | 4.95 | 9 |
| Safety | 3.35 | 4.23 | 4.39 | 10 |

## Inflection Points

- **Return vs Volatility inflection at Solution 23** (Return 13.07%, Vol 10.17%): Below this point, each additional percentage point of return costs dramatically more volatility. The marginal cost jumps 400x. This is the "diminishing returns" boundary for growth.
- **Return vs Yield inflection at Solution 84** (Return 5.85%, Yield 4.43%): Below this point, pushing for more yield costs relatively little return. The marginal cost jumps 40x. This is the "free yield" boundary.

## Constraint Activity

- **Max allocation (30%)**: Binding in most solutions. VDE, GLD, HYG, VGSH, EWJ, and EMB frequently hit the 30% cap.
- **Volatility <= 20%**: Not binding for any solution on the frontier (max observed: 14.54%). The covariance-based diversification benefit keeps all portfolios well under 20%.
- **Sector ETFs <= 3**: Satisfied across all solutions. Most solutions use 0-2 sector ETFs (primarily VDE).
- **Alternative ETFs <= 3**: Satisfied across all solutions. Typically GLD + DBA or GLD + IGF.
- **Cardinality 4-12**: All solutions have 5-11 holdings, well within bounds.

## Notes

- Volatility was computed using quadratic aggregation with the full 30x30 covariance matrix, enabling proper portfolio risk calculation that credits diversification.
- The 100-solution frontier provides dense coverage of the tradeoff space.
- All 17 sampled solutions in results.json span the full frontier from high-growth to safety-first.

# LLM-Only Optimization Results

## Summary

- **Total solutions generated:** 8
- **Curated strategies:** 4 (Growth, Balanced, Income, Safety)
- **Method:** Pure reasoning, no solver or calculator

## Objective Ranges Across All Solutions

| Objective | Min | Max | Unit |
|-----------|-----|-----|------|
| Expected Return | 1.54 | 17.56 | % |
| Volatility (wtd avg) | 6.45 | 19.35 | % |
| Dividend Yield | 0.76 | 4.84 | % |

## All Solutions

| # | Name | Return% | Vol% | Yield% | Holdings |
|---|------|---------|------|--------|----------|
| 1 | Growth | 16.28 | 17.86 | 1.28 | 6 |
| 2 | Aggressive Growth | 17.56 | 19.07 | 1.13 | 6 |
| 3 | Balanced | 10.47 | 13.02 | 2.55 | 8 |
| 4 | Income | 2.69 | 10.57 | 4.84 | 7 |
| 5 | Safety | 2.80 | 6.45 | 4.07 | 6 |
| 6 | Growth-Income Blend | 8.90 | 14.10 | 3.45 | 8 |
| 7 | Max Return Push | 17.58 | 19.35 | 0.76 | 5 |
| 8 | High Yield Safety | 3.11 | 7.62 | 4.65 | 6 |

## Constraint Compliance

All 8 portfolios satisfy:
- Max single allocation <= 30%
- Weighted-average volatility <= 20%
- At most 3 Sector ETFs held
- At most 3 Alternative ETFs held
- Between 4 and 12 holdings total

## Notes
- Volatility is computed as weighted-average (not covariance-based), which overstates risk for diversified portfolios
- Arithmetic performed manually with rounding to 4 decimal places during intermediate steps

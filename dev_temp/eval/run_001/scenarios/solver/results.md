# Scenario Optimization Results

## Summary

| Scenario | Probability | Solutions | Return Range | Vol Range | Yield Range |
|----------|------------|-----------|-------------|-----------|-------------|
| Base Case | 30% | 300 | 1.92% - 19.03% | 2.66% - 15.98% | 0.41% - 5.35% |
| Rate Cuts | 25% | 300 | 1.95% - 25.79% | 2.61% - 18.78% | 0.78% - 4.47% |
| Recession | 20% | 300 | -2.55% - 12.70% | 2.38% - 10.43% | 1.72% - 5.38% |
| Inflation | 25% | 300 | 0.15% - 33.52% | 2.66% - 15.69% | 1.00% - 6.33% |

**Total Pareto-optimal solutions: 1,200 (300 per scenario)**

## Method

- **Algorithm:** NSGA-II (pymoo) with population size 300, 500 generations
- **Decision variables:** 30 continuous weights (0-30%) summing to 100%
- **Repair operator:** enforces min 1% if held, max 30%, group limits (sectors <= 3, alternatives <= 3), cardinality 4-12
- **Volatility:** quadratic computation via `sqrt(w^T @ Cov @ w)` using 5-year covariance matrix
- **Constraints:** portfolio vol <= 20%, max single allocation 30%, 4-12 holdings, sector group <= 3, alternatives group <= 3

## Per-Scenario Objective Frontiers

### Base Case (Continuation)
The base case reflects 5-year historical returns (2021-2026). The frontier spans from low-vol bond-heavy portfolios (VGSH/HYG at ~2.7% vol) to high-return commodity/equity portfolios (VDE/GLD/VGT at ~16% vol). HYG appears in 79% of solutions as a high-yield, moderate-vol anchor.

### Rate Cuts / Risk-On
With boosted equity returns (1.5x) and reduced equity vol (0.8x), equities become far more attractive. VGT's return jumps to 29.1% (1.8x override). EWJ dominates at 77% frequency due to its strong yield + boosted return. The frontier extends to 25.8% return.

### Recession / Risk-Off
Equity returns collapse (0.2x) while treasuries rally (VGLT to 7%, BND to 5%). VGLT appears in 81% of solutions. The frontier contracts to max 12.7% return. Bond-heavy portfolios dominate, with GLD providing diversification. BND becomes scenario-specific (64% frequency here vs <1% elsewhere).

### Inflation Surge
Commodities surge (GLD/GSG/DBA at 2x), VDE at 1.5x, TIP to 8%. DBA dominates at 92% frequency. The frontier extends to 33.5% return driven by commodity overweight. Bond yields boost slightly (1.2x) but bond returns collapse (0.3x).

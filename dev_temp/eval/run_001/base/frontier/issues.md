# Issues Log: Frontier Method

## Skill Guidance

- **data_collection skill**: Auto-injected after problem creation (model create). Provided guidance on anchoring, batch efficiency, and completeness. Not particularly needed since all scores came from a structured JSON file.
- **optimization_strategy skill**: Auto-injected after score matrix reached 100% completeness AND after constraints were added. Provided guidance on mode selection, constraint strategy, and iteration expectations.
- **solution_interpreter skill**: Auto-injected with the solve results. Guidance on presenting tradeoffs, eliciting preferences, and curation. (Part of the solve response, which was too large to read directly.)

## Quadratic Volatility

**Status: Working correctly.**

The interaction_matrices parameter was successfully uploaded with the full 30x30 covariance matrix (465 upper-triangle entries). The optimizer used quadratic aggregation for the Volatility objective, computing portfolio volatility as sqrt(w^T * Cov * w).

Evidence that it worked:
- The Safety portfolio (83% bonds, small equity positions) achieved 4.23% portfolio volatility, which is much lower than the weighted-average of individual ETF volatilities (~6-7% even with bonds). This is only possible if the optimizer is using the negative covariance between bonds and equities.
- The 20% volatility bound never binds on any Pareto solution (max observed: 14.54%), which is consistent with covariance-based calculation. A naive weighted-average calculation would show higher volatility for equity-heavy portfolios and the bound would likely bind.
- The Growth portfolio (30% VDE at 26.6% vol, 30% GLD at 15.9% vol) has portfolio vol of only 13.27%, which reflects the moderate positive covariance between VDE and GLD (~126.9).

## Payload/Token Limit Issues

**Two occurrences:**

1. **solve run result**: The solve response exceeded the MCP tool token limit (144,782 characters). The result was saved to a temp file. This means the full solve output (including all 100 solutions with allocations and the solution_interpreter skill) could not be directly read. Workaround: used the explore tools (tradeoffs, solution, solutions, curate, etc.) to access results individually.

2. **explore solutions result**: The full solutions listing (100 solutions with full allocations) also exceeded the token limit (111,447 characters). Workaround: queried individual solutions at intervals (1, 5, 10, 20, 30, ..., 100) to build a representative sample for results.json.

**Impact**: The results.json contains 17 representative solutions sampled from the full 100-solution frontier rather than all 100. The curated strategies are fully accurate. The full 100 solutions exist in the Frontier tool's internal state and can be queried individually.

## Explore Actions

All explore actions succeeded:
- `tradeoffs`: Returned full overview with correlations, extremes, balanced solution, inflection candidates, and ASCII visualization.
- `solution` (individual): Returned complete allocation details for each queried solution.
- `curate`: Successfully curated 4 strategies (Growth, Balanced, Income, Safety).
- `compare_curated`: Returned side-by-side comparison with shared/differentiating options and parallel coordinates visualization.
- `marginal_analysis`: Returned inflection point detection and marginal rate analysis for all objective pairs.
- `solutions` (full listing): Failed due to token limit, but individual queries worked.

## Constraint Verification

**Structural vs manual**: The Frontier optimizer enforces constraints structurally during the evolutionary search -- solutions that violate constraints are penalized and eliminated. All 17 sampled solutions were manually verified:

- **Max allocation <= 30%**: All allocations are 0-30%. Multiple solutions have ETFs at exactly 30% (VDE, GLD, HYG, VGSH, EWJ, EMB).
- **Volatility <= 20%**: Maximum observed volatility across all 100 solutions is 14.54%. Never binding.
- **Sector ETFs <= 3**: Maximum sector count observed is 2 (typically VDE + one other). Never binding.
- **Alternative ETFs <= 3**: Frequently at the limit of exactly 3 (e.g., GLD + DBA + IGF in Growth, Balanced, Safety).
- **Cardinality 4-12**: Holdings range from 5 to 11 across sampled solutions. Never binding.

## Data Gaps

None. All 30 ETFs had complete data for all three metrics (ann_return_5yr_pct, ann_volatility_5yr_pct, dividend_yield_pct). The covariance matrix was complete for all 30x30 pairs.

## Interaction Matrix Format

**Minor issue**: The initial attempt to pass interaction_matrices with entries as a list of `{option_a, option_b, value}` dicts failed. The Frontier model expects entries as a nested dict `dict[str, dict[str, float]]` (matching the raw covariance matrix JSON structure). After switching to the nested dict format, the upload succeeded. This format mismatch is not documented in the tool description -- the skill mentions "entries" generically without specifying the exact schema. Required reading the source model code to resolve.

## Dominated Options Warning

The score update response flagged 19 of 30 options as "dominated" (worse on every objective than some other option). This is expected and not a problem -- in proportional mode, dominated options can still appear in portfolios because the quadratic volatility aggregation means an option that looks worse individually may reduce portfolio risk through diversification. Indeed, several "dominated" options appear in Pareto-optimal portfolios (e.g., VTV, BND, VGSH, HYG, EMB).

## HYG Covariance Data Anomaly

The HYG (High Yield Bond) row in the covariance matrix shows an anomalous pattern: the VOO-HYG covariance is 67.83 (positive), while all other equity-HYG covariances are negative (VUG-HYG = -23.48, VTV-HYG = -17.11, etc.). This suggests the covariance matrix may have a data issue in the HYG-VOO cell, or HYG truly has a different correlation structure with VOO vs other equities. This did not cause any optimization failures but is worth noting for data quality purposes.

## Performance

The full workflow (create, score, covariance upload, constrain, solve thorough) completed in well under 2 minutes of wall clock time. The solve step itself was the longest at approximately 10-15 seconds. The explore tools were near-instant.

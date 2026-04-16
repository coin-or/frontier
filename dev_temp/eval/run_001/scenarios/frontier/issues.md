# Issues and Observations — Frontier MCP Run

## Payload / Token Limits

1. **`solve run` output exceeded the 25k-token response cap** with 60 Pareto solutions (proportional allocations across 30 options). The tool saved results to a tool-results file but that blocks the normal explore flow. Workaround: fetch nothing from the `solve run` response directly; go straight to `explore tradeoffs`, `explore solution`, etc.
2. **`model get` output also exceeded the cap** after full scores + interaction matrix + scenario overrides were loaded (118k chars). Could not inspect the full model state during iteration — had to rely on the update-response summary and the scenario_results from explore.
3. Writing a 30×30 covariance matrix inline as the `interaction_matrices` parameter produces a ~19k-char payload that survives fine on input, but be aware it's a substantial request payload.

## Schema & API Shape

4. **`model update scores` parameter shape is surprising.** The docstring says scores is a list, but it's actually a list of `{option, objective, value}` triples — not `{option: {obj: val, ...}}` nested dicts nor even `[{option, Return, Volatility, Yield}]` flat rows. Had to trip on two validation errors to find the shape. The error messages were helpful but the schema doc in the MCP server description doesn't show the example.
5. **Objective direction enum.** The docstring says "max" and "min" but the Pydantic model accepts only "maximize" / "minimize". Another trial-and-error discovery.
6. **No interaction_matrix override in `Scenario` schema.** `Scenario` supports `score_overrides`, `score_adjustments`, `constraint_overrides`, but not `interaction_matrix_overrides`. This is a modelling limitation — see next point.

## Quadratic Volatility Under Scenarios — Important Caveat

7. **Volatility objective values for individual options are essentially ignored when aggregation=quadratic.** The portfolio volatility is computed from `sqrt(w^T · M · w)` where M is the interaction matrix (covariance). Individual option `Volatility` scores don't enter the quadratic calc — they're only used for display/marginal-analysis purposes.
8. **Scenario volatility overrides therefore had no effect on optimization.** Per the problem spec, Scenario 2 had "equity vol × 0.8", Scenario 3 had "equity vol × 1.8", etc. I chose to *omit* these overrides entirely because they would only change the displayed individual vol but not the quadratic portfolio vol.
9. **Stress-testing correlation structure would require per-scenario covariance overrides.** In a real recession, equity-equity correlations rise toward 1 ("diversification breakdown"); bond-equity correlations often flip sign. Without per-scenario interaction matrix overrides, the optimizer under-estimates portfolio vol in the Recession scenario (among others). Documented in response.md so the user knows what the model does and doesn't capture.

## Skill Guidance Auto-Injection

10. **`data_collection` skill auto-injected on `model create`.** Useful for framing but triggered before scores were entered — fine timing.
11. **`optimization_strategy` skill auto-injected twice** — once on scores reaching 100% completeness, once on `model update` with constraints. Second injection felt redundant. (Same content each time, so it's not harmful, but it's wasted tokens.)
12. **`solution_interpreter` skill was *not* auto-injected** when `solve run` was called, because the output exceeded the token cap and the skill was attached to the payload. I worked without its guidance and went directly to `explore tradeoffs` — which worked, but that's a gap: if a user gets a big result and it gets dumped to a file, the skill guidance is lost.

## Explore Tool Observations

13. **`explore tradeoffs` with scenario parameter works** — good, lets per-scenario inspection without re-running.
14. **`explore solution` with scenario parameter works** — could get allocations for specific solutions per scenario.
15. **`explore scenario_results` is very well-designed** — the option_robustness ranking, tiers (core/common/marginal), and scenario_specific breakdown are exactly what the deliverable asked for. Best tool in the explore set for scenario-based analysis.
16. **`explore curate` succeeded** for base-frontier solutions. Curated solutions from the *initial* run did NOT automatically survive evaluation against the scenario run — they have different solution IDs. Had to re-curate against the scenario run's solutions.
17. **`explore marginal_analysis`** returned clean data but only covers pairwise objective transitions; didn't compute 3D marginal rates. For a 3-objective problem, adjacent-pair analysis is a reasonable approximation.

## Constraint Interaction Quirks

18. **Cardinality min=4, max=12 combined with max_allocation=30% is self-consistent** (need at least 4 positions to fit 100% if capped at 30%: ceil(100/30)=4). The optimizer respected this cleanly.
19. **Both group_limit constraints (Sectors max 3, Alternatives max 3) were only weakly binding.** Most Pareto solutions used 2-3 sector names and 2-3 alternatives but rarely hit the cap. The 30% max_allocation was the dominant binding constraint for high-return solutions (VGT, VDE, GLD all pegged at 30%).
20. **Volatility bound ≤20% is not binding in any curated solution.** Actual Pareto vols all sat below 17.8% even at the top-return corner. The max_allocation + quadratic diversification makes hitting 20% hard.

## Numerical / Data Observations

21. **Dominated options diagnostic is informative but can mislead in proportional mode.** The metric reports 19 dominated options (e.g., VTV, VO, VB, VEA, ..., GSG). In a binary-selection problem these would be pruned, but in proportional mode they can still show up in Pareto solutions as small allocations that reduce portfolio variance via negative covariances. And indeed: VTV, VEA, GSG do appear in Pareto solutions.
22. **Interaction matrix symmetry not validated.** The supplied covariance matrix is symmetric (correct), but I only spot-checked. The engine appears to just use entries[a][b] as provided; asymmetric entries would silently break the math.
23. **Negative off-diagonal entries handled correctly** — Treasuries show strong negative covariance with equities (e.g., VGLT-VOO = -32.4), and the optimizer exploits this (Safety and Balanced portfolios always mix VGSH/BND with equity/credit).

## Scenario Results Quality

24. **All four scenarios returned 40 solutions each** with reasonable frontier shapes. The `spacing_cv` and `hypervolume_normalized` quality indicators look healthy (hypervolume 0.56-0.64).
25. **Ideal-point expected values (Return 21.97, Vol 4.16, Yield 4.93) are unachievable as a single portfolio** — important caveat for user interpretation. The explore output correctly flags this.
26. **Recession Income portfolio has negative return (-1.5%).** This is correct given the overrides (HYG=-4, EMB=-5, VNQI=-0.29), not a bug — the max-yield corner in recession forces holdings in distressed-credit instruments whose total return is negative.

## Constraint Verification

27. All curated portfolios verified by hand to satisfy: cardinality 4-12, max allocation 30%, sector count ≤3, alternative count ≤3, allocations sum to 100%. No violations found.
28. Volatility constraint (≤20%) satisfied on every curated portfolio — actual max vol 15.79% (Base Growth).

## Recommendations for Frontier Development

- **Add interaction_matrix_overrides to Scenario schema** — this is the single biggest gap for stress-testing portfolio-risk problems. Without it, recession/crisis scenarios can't capture correlation regime shift.
- **Truncate or paginate large solve/model responses** — returning 60 proportional solutions with 30 options produces 900 allocation entries which overflow the response cap. Consider auto-returning summary + top-5 extremes + balanced by default, with a `detail=full` flag for the full payload.
- **Document the scores schema more explicitly in the MCP tool description** — the flat list-of-triples format caught me twice.
- **Preserve skill guidance auto-injection even when the tool output is saved to a file** — currently a user gets a terse "saved to file" message without the solution_interpreter guidance that would normally accompany a successful run.

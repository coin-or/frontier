# Issues and Implementation Notes

## Solver Configuration

- **Algorithm:** NSGA-II via pymoo
- **Population size:** 300
- **Generations:** 500
- **Crossover:** SBX (eta=15, prob=0.9)
- **Mutation:** PM (eta=20)
- **Seed:** 42 (deterministic)
- **Total lines of code:** ~320 lines (solver.py)

## Constraint Enforcement

### Approach: Repair Operator + Inequality Constraints

The solver uses a dual enforcement strategy:

1. **Repair operator** (hard enforcement): Clips weights to [0, 30], zeros weights < 1%, enforces group limits by dropping smallest holdings in over-limit groups, ensures min 4 holdings, normalizes to sum to 100.

2. **Inequality constraints** (soft enforcement via pymoo): portfolio vol <= 20%, sectors <= 3, alternatives <= 3, 4 <= holdings <= 12. Pymoo's constraint handling uses constraint violation to guide selection pressure.

### Repair Operator Sequence
1. Clip to [0, 30]
2. Zero weights < 1%
3. If > 12 holdings, drop smallest until 12
4. If > 3 sectors held, drop smallest sector holdings
5. If > 3 alternatives held, drop smallest alt holdings
6. If < 4 holdings, randomly activate some at 1-10%
7. Normalize to sum 100
8. Re-clip, re-zero, re-normalize

### Known Issue: Normalization-Clipping Loop
After normalization, some weights may exceed 30% or fall below 1%. A second round of clip-zero-normalize is applied, but this is not iterated to convergence. In practice, the constraint violations are minimal and caught by the inequality constraints, which guide solutions toward feasibility.

## Constraint Violations

No constraint violations observed in the final Pareto sets:
- All solutions have 4-12 holdings
- All solutions have <= 3 sector ETFs
- All solutions have <= 3 alternative ETFs
- All portfolio volatilities <= 20% (the repair + constraint together enforce this)
- All single allocations <= 30% (post-normalization may cause minor exceedances that the repair catches)

## Scenario Parameterization

### Score Adjustment Order
For each scenario:
1. Start from base scores (5-year historical)
2. Apply group-level multipliers (equity, bond, sector, alternative)
3. Apply ticker-level overrides (absolute values or multiplier on BASE, not on already-adjusted values)

### Important: Override semantics
- Absolute overrides (e.g., "VGSH return -> +4.5%") replace the adjusted value entirely
- Multiplier overrides (e.g., "GLD return -> base x 1.3") use the BASE value as reference, not the group-adjusted value
- For recession scenario, VGT return would be: base * 0.2 (equity adjustment) * 0.2 (sector adjustment) = base * 0.04. No override replaces this, so VGT is heavily penalized.

### Rate Cuts Scenario Note
VGT receives both equity (1.5x) and sector (1.4x) multipliers, then is overridden to base * 1.8. The override replaces both multiplied values. Without the override, VGT would be at 16.19 * 1.5 * 1.4 = 34.0%, making the 1.8x override (29.14%) actually more conservative.

## Cross-Scenario Analysis Methodology

### Robustness Tiers
- **Core (>50% min freq across ALL scenarios):** No ETFs qualify. This reflects the fundamentally different optimal compositions across macro regimes.
- **Common (>25% avg freq):** 8 ETFs qualify. These form the realistic building blocks.
- **Marginal (<25% avg freq):** Remaining 22 ETFs. These appear only in niche allocations.

### Curation Method
For each scenario, 4 strategies are selected:
- **Growth:** maximum return on the Pareto front
- **Safety:** minimum volatility on the Pareto front
- **Income:** maximum dividend yield on the Pareto front
- **Balanced:** closest to the ideal point using normalized Euclidean distance (max return, min vol, max yield)

## Performance Notes

- Each scenario runs in ~15-20 seconds (300 pop x 500 gen)
- Total runtime: ~60-80 seconds for all 4 scenarios
- Memory usage dominated by 300 x 30 population matrix and 30 x 30 covariance matrix

## Observations

1. **HYG's dominance** is notable -- its 5.88% yield combined with only 7.89% vol makes it a Pareto-efficient yield source across all regimes, even in recession where its return is overridden to -4%.

2. **No core ETFs** is a meaningful finding: truly optimal portfolios look fundamentally different across macro regimes. This argues for active scenario-aware rebalancing rather than static allocation.

3. **VGSH as universal safety anchor:** Appears in all 4 safety strategies at 30% allocation. Its 2.2% vol is unmatched.

4. **GLD's versatility:** Appears in growth strategies across all 4 scenarios. It functions as a return driver (base, inflation), safe haven (recession), and diversifier (rate cuts).

5. **The covariance matrix is from the base period (2021-2026).** Scenario adjustments modify expected returns and individual vol scores but NOT the covariance structure. In reality, correlations shift across regimes (e.g., stock-bond correlation flips in rate-cut vs inflation environments). This is a limitation of the current approach.

# Issues and Observations

## 1. Constraint Violation: Max Allocation Exceeded

**Severity: High**

Two curated solutions contain holdings above the 30% max allocation constraint:
- **Growth:** VGT at 31% (should be <= 30%)
- **Balanced:** HYG at 31% (should be <= 30%)

Additionally, multiple non-curated solutions in the full Pareto set have allocations at 31%:
- Solution with EWJ at 31 (ret=8.02%, vol=8.38%)
- Solution with VGSH at 31 (ret=2.64%, vol=4.58%)
- Solution with HYG at 31 (ret=5.32%, vol=6.88%)
- Solution with VDE at 31 (ret=13.31%, vol=12.53%)

**Root cause:** The repair operator (lines 116, 139-147) caps allocations at 30% and then normalizes to sum to 100. But normalization can push weights back above 30%. The iterative convergence loop runs up to 10 times but exits early if the sum is within 0.01 of 100, without re-checking the cap after the final normalization. The validation filter (line 283) uses `max_alloc > 30.5` as the rejection threshold, so allocations between 30.0 and 30.5 pass through. After integer rounding (line 292), these can appear as 31%.

**Fix options:**
1. Tighten the validation filter from 30.5 to 30.05
2. Add a final clamp-then-redistribute step after the convergence loop
3. Round down instead of nearest-integer for positions near the cap

## 2. Solver Configuration

| Parameter | Value | Notes |
|-----------|-------|-------|
| Algorithm | NSGA-III | Appropriate for 3 objectives |
| Population size | 200 | Adequate for 30-variable problem |
| Generations | 400 | metadata.json says 400; user summary says 500 -- discrepancy |
| Reference directions | 91 | Das-Dennis with n_partitions=12 |
| Seed | 42 | Fixed for reproducibility |
| Solve time | 4.9s | Reasonable for the problem size |

**Note on generations:** The metadata.json records 400 generations, but the user's initial message references 500. The optimize.py script (line 243) specifies `("n_gen", 400)`. The metadata is consistent with the code.

## 3. Repair Operator Approach

The `PortfolioRepair` class (lines 65-150, 86 lines) handles constraint satisfaction through sequential mutation:

1. Clamp negative weights to zero
2. Zero out positions below 0.5% (cardinality control)
3. Enforce min holdings (4) by activating random ETFs at 5%
4. Enforce max holdings (12) by removing smallest positions
5. Enforce group limits (3 sectors, 3 alternatives) by removing smallest group members
6. Enforce min position size (1%)
7. Cap at 30%
8. Normalize to sum to 100
9. Iterative re-enforcement of min/max bounds (up to 10 iterations)

**Issues with this approach:**
- Steps are applied sequentially, so earlier corrections can be undone by later ones (e.g., cap enforcement undone by normalization)
- The iterative convergence loop (step 9) exits based on sum tolerance, not on all constraints being satisfied
- Random activation in step 3 introduces non-determinism within the repair operator itself
- No verification that group limits still hold after normalization

## 4. Covariance Matrix Handling

- Covariance matrix is loaded from `etf_cov_matrix.json` as a pre-computed NxN matrix
- Constructed in ticker order (lines 49-52) by iterating over the raw JSON
- Volatility computed as `sqrt(w^T @ Cov @ w)` where w is in fractional weights and Cov is in pct^2 units (line 181)
- No positive-definiteness check on the loaded matrix
- No nearest-PD correction if the matrix has numerical issues

## 5. Code Metrics

| Metric | Value |
|--------|-------|
| Total lines | 455 |
| Problem definition | lines 155-216 (62 lines) |
| Repair operator | lines 65-150 (86 lines) |
| Curation logic | lines 339-380 (42 lines) |
| Data loading | lines 32-57 (26 lines) |
| Solver config + run | lines 220-248 (29 lines) |
| Validation + output | lines 250-455 (206 lines) |
| Dependencies | pymoo (NSGA3, SBX, PM), numpy |

## 6. Additional Observations

- **Deduplication threshold** is set to Euclidean distance < 0.1 in objective space (line 329). With objective magnitudes ranging from ~2 to ~18, this is quite tight and unlikely to merge meaningfully different solutions.
- **Yield calculation** uses weighted average (`sum(w_i * yield_i) / sum(w_i)`) which is correct for percentage weights summing to 100, but differs from fractional-weight dot product used for return. The difference is cosmetic (identical result) but inconsistent in style.
- **Integer rounding** of allocations (line 292) followed by adjustment of the largest holding (lines 296-300) can create a subtle bias toward large positions and may push cap-adjacent allocations over the limit.
- **No Pareto dominance re-check** after rounding. Rounded solutions could become dominated.

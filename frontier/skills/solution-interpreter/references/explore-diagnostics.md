# Explore Diagnostics — Field Reference

Detailed schemas for the richer diagnostic blocks returned by `explore tradeoffs` and `explore scenario_results`. Read this when you need to pin down exact field semantics — the SKILL.md narration patterns cover the usual cases.

## `binding_analysis` (from `tradeoffs`)

List of entries, one per binding constraint.

| Field | Type | Meaning |
|---|---|---|
| `constraint` | str | Human-readable description, e.g. `"budget ≤ 500000"`, `"cardinality ≤ 5"`, `"group_limit(A, B, C) ≤ 2"` |
| `constraint_type` | str | `"objective_bound"` \| `"cardinality"` \| `"group_limit"` |
| `binding_fraction` | float [0-1] | Fraction of frontier solutions at or very near the bound |
| `near_binding_count` | int | Count of those solutions |
| `shadow_prices` | list | Per-other-objective rate of improvement from relaxing this constraint |
| `note` | str\|null | Populated when shadow prices couldn't be estimated (e.g., no adjacent-cardinality solutions) |

### `shadow_prices` entry shape

For `objective_bound`:

```json
{"objective": "NPV", "slope_per_unit_relaxed": 0.014}
```

Slope is rate of change of the objective against the constrained quantity, estimated by linear regression among near-binding solutions. Sign is *direction of improvement*: positive means relaxing helps the objective, negative means it hurts. Rare for it to be negative (would indicate the constraint is currently protecting the objective on the frontier).

For `cardinality` and `group_limit`:

```json
{"objective": "NPV", "gain_per_additional_slot": 1.2}
```

Discrete shadow price: expected improvement of the best-on-that-objective solution from +1 slot of capacity. Estimated as (best at binding level) − (best at adjacent level).

### Worked example

Budget binding on 18 of 20 solutions, with slope 0.014 for NPV and −0.002 for Risk:

> Budget is the tightest constraint — 90% of frontier solutions are pressed against it. On this frontier, each additional $1 of budget relaxation trades for about $0.014 of NPV and a 0.002 increase in Risk. Worth asking whether the $500k cap is a true limit or a planning target.

## `scenario_risk` (from `scenario_results`)

Dict keyed by objective name.

| Field | Type | Meaning |
|---|---|---|
| `expected` | float | Probability-weighted (or equal-weight) mean of per-scenario best value |
| `worst_case` | float | The worst single scenario's best achievable value |
| `best_case` | float | The best single scenario's best achievable value |
| `cvar_<α%>` | float | Probability-weighted mean of values in the worst α-fraction of scenarios |
| `range` | [min, max] | Envelope across scenarios |

The top-level `cvar_alpha` echoes the α the user requested (default 0.2). The CVaR key name includes α as a percent (`cvar_20`, `cvar_10`), so your narration can stay adaptive: always pull the CVaR value via `scenario_risk[obj][f"cvar_{int(alpha*100)}"]` rather than hardcoding `cvar_20`.

### Interpretation notes

- "Worst α-fraction by probability mass": probabilities are summed ascending (worst-first for maximize, best-first for minimize) until the cumulative mass reaches α. CVaR is the weighted mean of those scenarios' values. With 4 scenarios at 0.4/0.2/0.3/0.1 and α=0.2, the worst one (0.1) plus half of the next-worst (0.1 of 0.2) contribute.
- Equal-weight scenarios make this straightforward — each scenario's probability is `1/n`.
- `scenario_risk` uses *best-in-scenario* values. It's a ceiling analysis, not a specific-solution analysis. For solution-level risk, a user must specify which solution to track (future extension).

## `objective_redundancy` (from `tradeoffs`)

List of entries, one per objective pair.

| Field | Type | Meaning |
|---|---|---|
| `objectives` | [str, str] | The pair |
| `classification` | str | `independent` \| `linear_redundant` \| `strong_tradeoff` \| `redundant` \| `nonlinear_dependent` |
| `pearson` | float [-1, 1] | Direction-normalized r: +1 = both improve together, -1 = one improves as other worsens |
| `mutual_info_normalized` | float\|null [0-1] | Dependence strength (0 = independent, 1 = deterministic). Null when n<15. |
| `flags` | list[str] | Diagnostic flags: `high_pearson_aligned`, `high_pearson_opposed`, `high_mi`, `pearson_mi_disagreement` |
| `mi_reliable` | bool | False when n<15 — MI wasn't computed, only Pearson-based classification |

### Classification logic (for reference, do not re-derive)

Pearson `correlation` is direction-normalized — each objective's raw values are sign-flipped when its direction is `minimize`, so r ≥ +0.7 means both improve together and r ≤ -0.7 means the objectives are in genuine tension. Classification:

- `linear_redundant`: r ≥ +0.7 (both improving together)
- `strong_tradeoff`: r ≤ -0.7 (genuine conflict — NOT redundancy; this is the tradeoff users hired the optimizer to find)
- `redundant`: MI ≥ 0.7 when neither strong_tradeoff nor linear_redundant applies
- `nonlinear_dependent`: |r| < 0.3 **and** MI ≥ 0.4 (the informative Pearson/MI disagreement case)
- `independent`: none of the above

When `mi_reliable` is false, only Pearson-based classifications (`linear_redundant`, `strong_tradeoff`) can be detected reliably — treat MI-driven classifications with caution and say so to the user.

### Worked examples

High Pearson, high MI (both agree):

> Revenue and Profit move together almost perfectly on this frontier. The solver is essentially treating them as one axis — consolidating them would make the tradeoffs sharper.

Low |r|, high MI (disagreement):

> User Satisfaction and Retention look uncorrelated (r=0.12), but they're actually strongly dependent (MI=0.62). That usually means a threshold or plateau — e.g., satisfaction above some level drives retention but below that it doesn't move it. Worth looking at the scatter before deciding whether to keep both.

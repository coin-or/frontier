# Design: Quadratic Aggregation Mode

**Status:** Draft
**Motivation:** Portfolio-level values that depend on pairwise interactions between options (e.g., risk from correlations, network effects, synergies) can't be expressed as sum/avg/min/max of individual scores. This is the single biggest realism gap in Frontier's optimizer.

## Problem

Current aggregation modes compute objective values from individual option scores independently:
- `sum`: Σ(w_i × score_i)
- `avg`: Σ(w_i × score_i) / Σ(w_i)
- `min`/`max`: extremes of selected options

For objectives where the portfolio-level value emerges from **interactions** between options, these are approximations. The canonical example is portfolio volatility: σ_p = √(w^T Σ w) where Σ is the covariance matrix. But this generalizes beyond finance — team skill complementarity, ingredient interactions, network effects.

## Proposed Design

### New Aggregation Mode: `quadratic`

```python
class Aggregation(str, Enum):
    sum = "sum"
    avg = "avg"
    min = "min"
    max = "max"
    quadratic = "quadratic"  # NEW
```

When an objective uses `quadratic` aggregation, the portfolio value is computed as:

```
value = √(w^T M w)
```

Where `w` is the allocation weight vector and `M` is an interaction matrix provided alongside the scores.

### Data Model Changes

**Option A — Interaction matrix on Objective:**

```python
class Objective(BaseModel):
    name: str
    direction: Direction
    unit: str = ""
    aggregation: Aggregation = Aggregation.sum
    interaction_matrix: dict[str, dict[str, float]] | None = None  # option_a → option_b → value
```

Stored as nested dict keyed by option names. Only needed when `aggregation == "quadratic"`.

**Option B — Separate InteractionMatrix model on Problem:**

```python
class InteractionMatrix(BaseModel):
    objective: str  # which objective this matrix applies to
    entries: dict[str, dict[str, float]]  # symmetric: entries[a][b] == entries[b][a]

class Problem(BaseModel):
    ...
    interaction_matrices: list[InteractionMatrix] = []
```

**Recommendation:** Option B. Keeps Objective lean (it's referenced everywhere). Matrices are large and rarely needed — separate storage avoids bloating serialization of problems that don't use them.

### Optimizer Changes

**`_ProportionalProblem._aggregate_objective`** (~5 lines):

```python
elif agg == Aggregation.quadratic:
    # M is pre-built as numpy array in __init__
    # value = sqrt(w^T M w) for each population member
    vals = np.zeros(n_pop)
    for i in range(n_pop):
        w = fracs[i]
        vals[i] = np.sqrt(w @ self.interaction_matrices[j] @ w)
    return vals
```

Can be vectorized for performance:
```python
# Batched: (n_pop, n_var) @ (n_var, n_var) @ (n_var, n_pop) → diagonal
Mw = fracs @ self.interaction_matrices[j]  # (n_pop, n_var)
vals = np.sqrt(np.einsum('ij,ij->i', Mw, fracs))
```

**`_FrontierProblem`** (binary mode): Same math but with binary selection vector. Less useful since binary mode has no weights, but `M[selected, selected].sum()` or similar could work if needed. Lower priority.

**`_parse_constraints` / `_build_score_matrix`**: Add parallel `_build_interaction_matrices` that converts the dict-of-dicts into numpy arrays indexed by objective.

### MCP Server Changes

- `model/update` accepts `interaction_matrices` param (list of `{objective, entries}` dicts)
- Merge semantics: upsert by objective name
- Validation: matrix must be symmetric, all referenced options must exist, only allowed when aggregation is `quadratic`

### Skill Changes

- **problem-framing**: Update Aggregation section to include `quadratic` mode with guidance on when to use it
- **data-collection**: Add guidance on sourcing/computing interaction matrices (e.g., covariance from historical returns)

### Score Matrix vs Interaction Matrix

Individual scores still exist for `quadratic` objectives — they're used for:
- Solution display (show per-option contribution)
- Marginal analysis (option-level rates)
- Robustness metrics (per-option frequency)

The interaction matrix is *only* used during optimization to compute the portfolio-level aggregate. This means the existing explorer/visualization code doesn't need changes.

## Level of Effort

| Component | Estimate | Notes |
|-----------|----------|-------|
| `models.py` — new enum value + InteractionMatrix model | Small | ~15 lines |
| `optimizer.py` — aggregate method + matrix builder | Medium | ~40 lines, 2 problem classes |
| `optimizer.py` — validation | Small | ~10 lines (symmetric, complete, matching aggregation) |
| `server.py` — parse + wire interaction_matrices | Medium | ~30 lines (update handler, schema docs) |
| `explorer.py` — no changes needed | — | Explorer uses stored objective_values, not re-aggregation |
| Skills — update 2 skill files | Small | ~10 lines each |
| Tests | Medium | ~5 new tests (aggregation correctness, validation, round-trip) |
| **Total** | **~130 lines of code + tests** | |

## Data Pipeline (for ETF demo)

To use quadratic vol for the ETF problem, we need a 30×30 covariance matrix. Options:
1. **Compute from historical returns** — most accurate, requires return time series data (not just summary stats)
2. **Estimate from asset class correlations** — use known relationships (equity-bond correlation ~-0.3, equity-commodity ~0.1, etc.) + individual volatilities to construct Σ = diag(σ) × R × diag(σ)
3. **Use a proxy** — simplified block-diagonal structure by asset class group

Option 2 is the pragmatic choice for the demo — plausible, no new data sourcing needed.

## Open Questions

1. **Should `quadratic` support both `sqrt(w^T M w)` and `w^T M w`?** The square root is standard for volatility (units match), but raw variance might be useful for other domains. Could add a `quadratic_root: bool = True` field.
2. **Binary mode support?** For binary selection without weights, quadratic aggregation is less natural. Could skip initially.
3. **Scenario score adjustments for interaction matrices?** Current ScoreAdjustment applies multipliers to individual scores. Would we need ScenarioMatrixAdjustment? Or can scenarios just provide replacement matrices?
4. **Performance at scale?** Matrix multiply is O(n²) per population member per generation. For 30 options × 200 pop × 500 gen = 3M matrix multiplies — should be fine. For 1000+ options, might need sparse matrix support.

## Recommendation

Implement in two phases:
1. **Phase 1**: Core aggregation + proportional mode only + manual matrix input via MCP. Enough to fix the ETF demo.
2. **Phase 2**: Binary mode support, scenario matrix adjustments, helper utilities for computing covariance from data.

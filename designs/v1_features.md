# Frontier v1 Features

**Building on Phase 0 MVP toward a complete multi-objective portfolio optimization tool.**

Version 1.0 · March 2026

---

## Status

Phase 0 MVP is complete: binary optimization (NSGA-II), 3 MCP tools (`model`, `solve`, `explore`), 4 skills, JSON persistence, 150+ tests. Everything below builds on that foundation.

---

## Feature Tiers

### [now] — Implement immediately

#### 1. Objective Aggregation

Phase 0 hardcodes sum aggregation for all objectives. Real problems need different aggregation semantics.

**Aggregation modes:**

| Mode | Semantics | Example |
|---|---|---|
| `sum` | Total across selected options | "Total revenue of selected features" |
| `avg` | Average across selected options | "Average user satisfaction of selected features" |
| `min` | Worst individual option in portfolio | "Minimum reliability across selected vendors" |
| `max` | Best individual option in portfolio | "Peak performance of best selected component" |

**Model change:** Add `aggregation` field to Objective (default: `sum` for backward compat).

**Optimizer change:** Replace `F = X_bin @ score_matrix` with per-objective aggregation. Objective bound constraints must also respect the aggregation method.

**Scope:** Models, optimizer, infeasibility analysis. Skills mention aggregation. Tests verify each mode.

---

#### 2. Proportional Allocation

Phase 0 supports binary selection only (pick K of N). Proportional mode enables resource allocation problems (distribute budget/effort/attention across N options).

**How it works:**
- Decision variables: integer percentages 0-100 per option, summing to 100
- Objectives: computed from allocations × scores (for sum aggregation: weighted sum; for avg/min/max: applied over allocated options)
- Solutions report both `selected_options` (allocation > 0) and `allocations` dict

**Constraint mapping in proportional mode:**

| Constraint | Binary meaning | Proportional meaning |
|---|---|---|
| Cardinality (3-5) | Select 3-5 options | Allocate to 3-5 options (non-zero) |
| Force include X | Must select X | Must allocate to X (> 0%) |
| Force exclude X | Cannot select X | Must not allocate to X (0%) |
| Objective bound | Portfolio total/avg/min/max ≤ value | Same, computed from allocations |

**Model changes:** `Approach` enum on Problem (`binary` | `proportional`, default `binary`). `allocations` field on Solution.

**Optimizer changes:** New `_ProportionalProblem` pymoo class with continuous variables, SBX crossover, polynomial mutation. Sum-to-100 equality constraint.

**Explorer changes:** Allocation-aware comparison (show percentage differences, not just set membership).

---

#### 3. Run Comparison (Iterative Solves)

Phase 0 stores only the latest run and clears it on structural change. Iterative optimization — the core workflow — needs run history and comparison.

**Changes:**
- `results_stale` flag replaces clearing run on structural change
- Run archival: previous runs stored in `runs` list on Problem
- Each Run snapshots constraints at solve time
- New `compare_runs` explore action

**Compare output:**
- `criteria_diff`: constraints added, removed, or changed between runs
- `frontier_diff`: solution count change, objective range changes
- `option_coverage_diff`: which options gained/lost Pareto membership

**Skills impact:** `optimization_strategy` gets run comparison interpretation guidance. `solution_interpreter` gets run diff narration patterns.

---

### [next] — Design exists, implement after [now] features are validated

#### 4. Scenario Support

Per-scenario optimization answering: "Which portfolio holds up across different futures?"

**Design (from v1 design doc):**
- Define scenarios with probabilities (sum to 1.0)
- Score overrides per scenario (only changed scores, base matrix fills rest)
- Independent optimization per scenario
- Probabilistic analysis: expected value solution, robust solution (minimax regret), robust options (in all frontiers), scenario-specific options

**Tool integration:** Scenario config via `model update`, scenario optimization as `solve` action, scenario results via `explore`.

**Open questions:**
- Do scenarios get their own tool action or fold into existing actions?
- How does run comparison interact with scenarios (compare across scenarios vs across runs)?
- Scenario-specific constraints — needed, or too complex for v1?

---

#### 5. Additional Constraint Types

Phase 0 has 4 constraint types. Real problems need more.

| Type | Semantics | Example |
|---|---|---|
| `exclusion_pair` | Cannot select both A and B | "Can't do both Mobile App and Desktop App" |
| `dependency` | If A then must include B | "API Access requires SSO Integration" |
| `group_limit` | At most K from group G | "At most 2 features from the infrastructure category" |

**Proportional mode mapping:**
- Exclusion pair → can't allocate to both (at most one has allocation > 0)
- Dependency → if allocation to A > 0, allocation to B must be > 0
- Group limit → at most K options in group have allocation > 0

**Open questions:**
- Does the Constraint union type stay flat (add 3 more Pydantic models), or adopt a registry pattern?
- How do these interact with infeasibility analysis? Each new type needs relaxation logic.

---

#### 6. Reference Points (Baseline + Aspirational)

Users need context for interpreting optimization results. Reference points provide anchors.

**Two types:**
- **Baseline**: Status quo or current performance. "Our current system costs $75K and delivers 80% satisfaction." Grounds abstract numbers in familiar context.
- **Aspirational**: Target or ideal outcome. "We want cost under $50K and satisfaction above 90%." Sets expectations and reveals tension between goals.

**How they're used:**
- Explorer presents solution performance relative to reference points: "This achieves 95% of your cost target and 80% of your satisfaction target"
- Gap analysis: distance from aspirational point per objective reveals where goals are most in tension
- If a solution achieves all aspirational points simultaneously, objectives may not truly conflict (or targets are too conservative)
- Reference points do NOT constrain the optimizer — they're purely interpretive

**Model design:**

```
ReferencePoint
├── type: "baseline" | "aspirational"
├── name: string (optional — e.g., "Current System", "Q4 Target")
├── objective_values: dict[str, float]  (objective name → value, partial OK)
├── selected_options: list[str] | None  (baseline only — the current portfolio)
└── created_at: datetime
```

Stored on Problem as `reference_points: list[ReferencePoint]`. Partial objective values are fine — not every objective needs a reference value.

**Key distinction:** A baseline can include a solution (the current portfolio) because it represents known reality. An aspirational point is objective values only — the optimal solution is unknown, that's the point of the optimization. Constraints describe directional solution requirements.

**Tool integration:**
- Set via `model update` (reference_points field)
- `explore tradeoffs` includes distance-to-reference analysis when reference points exist
- `explore solution` shows performance vs reference points for that solution
- `explore compare` includes reference point context in tradeoff summary

**Skill integration:**
- `problem_framing` encourages setting reference points during framing ("What's your current baseline? What would ideal look like?")
- `solution_interpreter` uses reference points for contextualized presentation ("This solution is 15% better than your baseline on cost but 5% short of your quality target")

**Open questions:**
- Should reference points be per-objective (simpler) or full solution-shaped vectors (more expressive)?
- How do reference points interact with scenarios? Different baselines per scenario?
- Should the `explore` tool compute distance metrics automatically, or leave interpretation to the LLM via skills?

---

### [later] — Validated need, design incomplete

#### 7. Guided Data Collection

The `data_collection` skill is instruction-only. "Guided" means the tool actively assists:
- Suggest what to score next (highest-impact missing scores)
- Auto-research researchable scores (pricing, benchmarks)
- Track confidence per score
- Sensitivity analysis: which scores, if changed, would most affect the frontier

**Depends on:** Scenario support (sensitivity analysis connects naturally), reference points (confidence calibration against baselines).

---

### [later+] — Known direction, low urgency

#### 8. Algorithm Routing

NSGA-II handles 2-6 objectives. Beyond that:

| Objectives | Algorithm | Why |
|---|---|---|
| 2-3 | NSGA-II | Crowding distance works, tradeoffs intuitive |
| 4-7 | NSGA-III | Reference points prevent clustering at extremes |
| 8+ | MOEA/D | Dominance becomes rare, decomposition more efficient |

The `optimization_strategy` skill already describes this routing. Engine-side it's algorithm selection based on objective count — mechanical, testable, low risk.

**Depends on:** Problems with 4+ objectives from dogfooding. Don't add complexity without demonstrated need.

---

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Aggregation default | `sum` | Backward compatible with Phase 0 |
| Approach storage | On Problem (persisted) | Affects score interpretation semantics |
| Run clearing → stale flag | `results_stale = True` | Preserves runs for comparison |
| Run history storage | Embedded in problem JSON | Problem files are small; simple persistence |
| Proportional cardinality | Count of non-zero allocations | Natural mapping from binary semantics |
| Min allocation threshold | Zero (any > 0 counts) | Simple; min_allocation as future constraint |
| Reference points | Interpretive only, not optimizer constraints | Clean separation — constraints constrain, reference points contextualize |

---

## Resolved Questions

| # | Question | Decision | Rationale |
|---|---|---|---|
| 1 | Proportional avg aggregation | **Weighted average** (by allocation %) | Properly represents proportional contribution — an option with 60% allocation should influence the average more than one with 10% |
| 2 | Min allocation threshold | **Depends on constraints** — no built-in minimum | Users control this via cardinality constraints. If trivial allocations appear, tighten cardinality. A future `min_allocation` constraint type could be added in [next] |
| 3 | Hybrid approach | **No** — one approach per problem | Keep binary and proportional mutually exclusive. Simplifies model and UX |
| 4 | Run history limits | **Not an issue yet** | Monitor during dogfooding. JSON files are small |
| 5 | Reference point model | **Baseline**: objective values + optionally a solution (selected options). **Aspirational**: objective values only — the optimal solution is unknown, that's the point of optimization. Constraints describe directional solution requirements | Baseline grounds results in current reality (which may be a known portfolio). Aspirational is a target vector, not a solution |

## Remaining Open Questions

### Reference points (implementation details for [next])

6. **Automatic distance computation**: Should `explore tradeoffs` automatically compute and return distance-to-reference metrics, or just return reference points for the LLM to interpret? Leaning toward automatic — the LLM shouldn't do arithmetic.

7. **Baseline solution field**: The baseline can optionally include a solution (selected options or allocations) to compare against Pareto solutions. Should this be a full Solution object, or just a list of option names? Leaning toward lightweight (just option names + objective values).

### Architecture

8. **REST API**: The v1 design doc envisions 24 REST endpoints. Is this needed, or is MCP + importable Python library sufficient? Leaning toward: skip REST, invest in MCP quality. Add REST only if a non-LLM client appears.

9. **Store abstraction**: Current JSON-per-file store works. If run history grows large or proportional mode produces many solutions, may need revisiting. Monitor during dogfooding.

---

## Interaction Map: Features × Components

Shows which components each feature touches. Features must update both tools AND skills.

| Feature | models | optimizer | explorer | server | problem_framing | data_collection | optimization_strategy | solution_interpreter | tests |
|---|---|---|---|---|---|---|---|---|---|
| Aggregation | Objective.aggregation | _evaluate per-obj | — | pass-through | aggregation guidance | scoring implications | already mentioned | aggregation framing | new test class |
| Proportional | Approach enum, Solution.allocations | new Problem class | allocation comparison | approach param | approach selection | — | proportional strategy | allocation presentation | new test file |
| Run comparison | Run.constraints_snapshot, Problem.runs, results_stale | snapshot stamp | compare_runs | new action, stale flag | — | — | run comparison interp | run diff narration | new test class |
| Scenarios | ScenarioConfig, overrides | per-scenario runs | probabilistic analysis | scenario actions | scenario guidance | override scoring | scenario strategy | scenario presentation | new test file |
| New constraints | 3 new constraint types | pymoo encoding | — | parse + validate | constraint language | — | constraint strategy | — | constraint tests |
| Reference points | ReferencePoint model | — | distance metrics | reference actions | encourage setting | — | — | contextualized presentation | reference tests |
| Guided data | confidence on Score | — | sensitivity | suggestion action | — | major rewrite | — | confidence narration | data tests |
| Algorithm routing | — | algorithm selection | — | — | — | — | already described | — | routing tests |

---

## Implementation Phases

### Phase A: Foundations (implement now, high confidence)

1. Objective aggregation — small scope, high correctness impact
2. Run history + stale flag — enables iterative workflow
3. Run comparison — completes the iteration loop
4. Proportional allocation — new problem class + constraint adaptation + explorer updates

### Phase B: Skills + validation (implement after Phase A)

5. Update all 4 skills for new capabilities
6. Update eval checkpoint with new test phases
7. Run full test suite + manual MCP validation

### Phase C: Review checkpoint

Pause. Review open questions. Dogfood with real problems. Let friction inform [next] priorities.

### Phase D: [next] features (after review)

8. Reference points
9. Additional constraint types
10. Scenario support

---

*This document is a living reference. Update as decisions are made and questions are resolved.*

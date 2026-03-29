# Frontier v1 Features

**Multi-objective portfolio optimization — from Phase 0 MVP to complete v1.**

Version 1.1 · March 2026

---

## Status

**All [now] and [next] features are implemented, plus solution curation.** 192 tests passing, 550 eval checkpoint checks across 14 phases.

| Tier | Features | Status |
|---|---|---|
| **[now]** | Aggregation, proportional allocation, run comparison | ✅ Shipped |
| **[next]** | New constraints, reference points, scenarios | ✅ Shipped |
| **[now-2]** | Solution curation (content signatures, naming, cross-run survival) | ✅ Shipped |
| **[next-2]** | Binding constraint analysis, score sensitivity, question anchor | Scoped |
| **[later]** | Guided data collection | Design only |
| **[later+]** | Algorithm routing | Design only |

**Current counts:** 7 constraint types, 4 aggregation modes, 2 optimization approaches, 3 MCP tools (model/solve/explore with 20 total actions), 4 skills, scenario support, solution curation with content-based identity.

---

## What's Implemented

### Objective Aggregation ✅

`Aggregation` enum on Objective: `sum` (default) | `avg` | `min` | `max`.

| Mode | Binary semantics | Proportional semantics |
|---|---|---|
| `sum` | Total of selected options' scores | Weighted sum: `sum(alloc% × score)` |
| `avg` | Average of selected options' scores | Weighted average: `sum(alloc% × score) / sum(alloc%)` |
| `min` | Worst score among selected options | Worst score among allocated options (alloc > 0) |
| `max` | Best score among selected options | Best score among allocated options (alloc > 0) |

Objective bound constraints respect the aggregation method. Infeasibility analysis respects aggregation.

### Proportional Allocation ✅

`Approach` enum on Problem: `binary` (default) | `proportional`.

Solutions in proportional mode include `allocations: dict[str, int]` — integer percentages (0-100) summing to 100. All 7 constraint types work in both modes. Explorer shows `allocation_comparison` in side-by-side comparisons.

**Implementation:** `_ProportionalProblem` pymoo class with continuous variables [0, 100], SBX crossover, polynomial mutation, sum-to-100 equality constraint via paired inequalities.

### Run Comparison ✅

- `results_stale` flag replaces destructive run clearing on structural changes
- `Run.constraints_snapshot` captures constraints at solve time
- `Problem.runs` stores archived run history
- `explore compare_runs` action returns criteria diff, frontier diff, option coverage diff

### Additional Constraint Types ✅

7 total constraint types (4 from Phase 0, 3 new):

| Type | Fields | Binary encoding | Proportional encoding |
|---|---|---|---|
| `cardinality` | min, max | count(selected) in [min, max] | count(alloc > 0) in [min, max] |
| `force_include` | option | x[i] >= 1 | alloc[i] > 0.5 |
| `force_exclude` | option | x[i] <= 0 | alloc[i] < 0.5 |
| `objective_bound` | objective, operator, value | agg(objective) ≤/≥ value | same |
| `exclusion_pair` | option_a, option_b | x[a] + x[b] <= 1 | allocated(a) + allocated(b) <= 1 |
| `dependency` | if_option, then_option | x[if] - x[then] <= 0 | allocated(if) - allocated(then) <= 0 |
| `group_limit` | options[], max | sum(x[group]) <= max | count(allocated in group) <= max |

All types validated in `validate()`, encoded as pymoo inequalities, and supported in `analyze_infeasibility()`. Server cascading handles option removal for all types.

### Reference Points ✅

`ReferencePoint` model with type (`baseline` | `aspirational`), name, `objective_values` (partial OK), `selected_options` (baseline only).

- `explore tradeoffs` includes `balanced_vs_references` when reference points exist
- `explore solution` includes `vs_references` with per-objective distance metrics (difference, percent, better/worse)
- Set via `model update` with `reference_points` parameter — interpretive only, does not constrain optimizer

### Scenario Support ✅

- `ScenarioConfig` with probability-weighted `Scenario` objects and `score_overrides`
- `solve run_scenarios` runs optimization independently per scenario
- `explore scenario_results` returns:
  - `robust_options` — appear in Pareto frontier across all scenarios
  - `scenario_specific_options` — strong in particular scenarios only
  - `expected_values` — probability-weighted best objective values
  - `per_scenario` — solution count and ranges per scenario

Probabilities validated to sum to ~1.0.

---

## Learnings

### What worked well

1. **Flat constraint union.** Adding 3 new constraint types was mechanical — new Pydantic model, add to union, add case to `_parse_constraint`, add encoding to both problem classes, add validation, add infeasibility logic. The pattern scales without a registry. Keep it flat unless we hit 15+ types.

2. **Aggregation as a per-objective field** (not problem-level). Different objectives naturally need different aggregation — "total revenue" (sum) + "average satisfaction" (avg) in the same problem. This was the right granularity.

3. **`_parse_constraints` returning a dict** (refactored from tuple). Made it trivial to add new constraint parameters — just add keys. The `**cp` unpacking into problem classes is clean.

4. **Reference points as interpretive-only.** No optimizer coupling means no constraint interaction to debug. The explorer computes distances; the LLM interprets. Clean separation.

5. **Scenario support via score overrides.** Only storing changed scores keeps scenarios lightweight. Deep-copying the problem and overriding scores for each scenario run is simple and correct.

6. **Skills as the contextual judgment layer.** The tool does arithmetic; the skill tells the LLM what to say about it. This held up across all new features — each required tool changes AND skill changes, confirming the architecture.

### What to watch

1. **Proportional mode produces many solutions** (100+ on the Pareto frontier for small problems). The continuous search space is richer than binary. May need frontier pruning or a `max_solutions` parameter if this overwhelms the LLM context.

2. **Scenario runs don't get archived.** `scenario_run` stores the latest per-scenario results, but there's no history. If the user changes scenarios and re-runs, old results are lost. Not urgent — scenario iteration is less common than constraint iteration.

3. **`min`/`max` aggregation uses per-row loops** in the optimizer (not vectorizable via matrix multiply). Fine for ≤40 options and pop_size ≤200, but would need optimization for larger problems.

4. **Weighted avg in proportional mode** divides by `sum(fracs)`, which equals 1.0 when allocations sum to 100. This means weighted avg ≈ weighted sum for well-formed solutions. The distinction matters only for intermediate (infeasible) solutions during optimization. Verify this doesn't cause unexpected behavior during dogfooding.

5. **The `model` tool has 11 parameters now** (action, problem_id, name, domain, context, objectives, options, scores, constraints, approach, reference_points, scenario_config). Approaching complexity threshold. If more top-level fields are needed, consider grouping (e.g., a `config` parameter for approach + reference_points + scenario_config).

6. **Curation as preference bridge.** Curation is not just bookmarking — it's a preference alignment mechanism between agent and user. What gets curated reflects real-world considerations that may not be in the data: political viability, team capacity, strategic timing. Across runs, scenarios, and even problems, the curated set is the strongest signal of what the user actually values. The `solution_interpreter` skill now treats curation choices as preference evidence.

7. **Skill gap closed: objective ranking and dominance.** The `solution_interpreter` previously had strong preference *observation* (watching patterns) but weak *elicitation* (actively probing). Added: progressive narrowing (probe → rank → filter → curate), marginal tradeoff questions ("how much effort for $50K more?"), strict and preference-conditional dominance explanation. This drives users from raw frontier to named shortlist.

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
| Constraint union | Flat (7 Pydantic models) | Pattern scales; no registry needed yet |
| Proportional avg | Weighted by allocation % | 60% allocation should influence average more than 10% |
| Hybrid approach | No — one per problem | Keep binary and proportional mutually exclusive |
| Baseline model | Objective values + optional selected_options | Baselines are known reality; aspirational is target vector only |
| Scenario actions | Folded into existing tools | `solve run_scenarios`, `explore scenario_results` — no new tool |
| Solution identity | Content-based signatures (MD5 of composition) | Stable across re-runs, enables curation persistence and cross-run tracking |
| Curation persistence | Survives re-solves, cleared on structural problem changes | Composition still valid after score changes; stale objective values recomputed on access |
| Curation as signal | Treat curated choices as preference evidence | Reveals real-world considerations not in scores — political, strategic, intuitive |

---

## Resolved Questions

| # | Question | Decision |
|---|---|---|
| 1 | Proportional avg aggregation | Weighted average (by allocation %) |
| 2 | Min allocation threshold | Depends on constraints — no built-in minimum |
| 3 | Hybrid approach | No — one approach per problem |
| 4 | Run history limits | Not an issue yet |
| 5 | Reference point model | Baseline: objective values + optional solution. Aspirational: objective values only |
| 6 | Automatic distance computation | Yes — explorer computes per-objective distances automatically |
| 7 | Baseline solution field | Lightweight: list of option names + objective values (not a full Solution object) |
| 8 | Constraint union pattern | Stay flat — 7 types is fine, would reconsider at 15+ |
| 9 | Scenario tool integration | Fold into existing tools (solve/explore actions), not separate tool |
| 10 | Proportional frontier size | OK — agent must identify inflection points and diverse strategies. Present single-digit curated set, never all 100+ |
| 11 | Scenario run archival | Keep latest run per active scenario — no deep archival needed |
| 12 | Model tool parameter count | Acceptable for now. Revisit if it grows further |
| 13 | Score confidence metadata | No — optimizer should not use it. Pure metadata if ever added |
| 14 | REST API | Skip. MCP + Python library sufficient |
| 15 | Store abstraction | Keep JSON-per-file. Simplest option |

---

## Open Questions

1. **Curated solution invalidation on score changes.** When scores change (not structure), curated solutions' objective values are stale but composition is still valid. Current behavior: keep curated set. Could recompute objective values from current scores on next `explore curated` call. Not urgent — scores rarely change without re-solving.

2. **Max curated set size.** No hard limit currently. Soft warning at 10-15? Dogfood first.

3. **Curated solution export.** Curated set is the natural unit of export/sharing. JSON exists via `explore curated`. Consider structured summary for presentation contexts.

---

## What's Next

### Solution Curation ✅

Content-based solution identity + accumulative curation across runs. Inspired by the decision assistant v2 model.

**Content signatures:** Every solution gets a stable 12-char MD5 hash of its composition (sorted selected_options for binary, sorted allocation pairs for proportional). Survives re-indexing across runs. Enables duplicate detection, cross-run tracking, and name persistence.

**CuratedSolution model:** content_signature, custom_name, selected_options, allocations, objective_values, curated_at, source_run_id, notes. Stored on Problem as `curated_solutions: list[CuratedSolution]`.

**5 new explore actions:** `curate`, `uncurate`, `rename_curated`, `curated`, `compare_curated`.

**Cross-run survival:** `explore curated` returns `in_current_frontier` for each curated solution — whether it still appears in the latest run. Curated solutions persist even when eliminated by constraints (flagged, not deleted).

**Curation as preference signal:** What a user curates reveals real-world considerations not captured in scores or constraints — political viability, team enthusiasm, strategic alignment. The `solution_interpreter` skill treats curation choices as evidence of actual priorities, potentially more reliable than stated objective weights. When a user curates a suboptimal solution, the skill probes why — that's signal.

**Skill updates:**
- `solution_interpreter`: objective ranking elicitation (progressive narrowing from frontier to shortlist), dominance explanation (strict and preference-conditional), curation coaching (guide to named shortlist of 3-5), presentation framing (curated set IS the decision set)
- `optimization_strategy`: curated solution survival reporting after re-solves

---

### [next] — Binding Constraint Analysis

The `optimization_strategy` skill coaches agents to detect binding constraints ("all solutions sit near the boundary"), and the `solution_interpreter` skill maps binding constraints → bottlenecks. But the agent must infer this from eyeballing solution patterns — no tool action surfaces it directly.

**Goal:** Make bottleneck detection explicit in explorer output so the agent narrates it reliably instead of guessing.

**Approach: augment `explore tradeoffs`**, not a new action. Binding constraint data is most useful when first reviewing results — the same moment `tradeoffs` is called.

**What to compute:**

For each `objective_bound` constraint, check whether it binds across the frontier:

| Field | Definition |
|---|---|
| `constraint` | The constraint (objective, operator, value) |
| `binding_pct` | % of Pareto solutions within 5% of the bound |
| `tightest_solution` | Solution closest to (or at) the bound |
| `slack_range` | [min_slack, max_slack] across all solutions — how much room exists |
| `impact_estimate` | Qualitative: "relaxing by 10% would likely expand the frontier" if binding_pct > 80% |

For cardinality constraints, check similarly — are all solutions at min or max?

**Output shape** (added to `tradeoffs` response):

```python
"binding_analysis": [
    {
        "constraint": {"type": "objective_bound", "objective": "Effort", "operator": "max", "value": 30},
        "binding_pct": 0.85,
        "tightest_solution_id": 3,
        "slack_range": [0.0, 4.2],
        "suggestion": "85% of solutions are near the effort cap. Relaxing from 30 to 35 could open new tradeoff space."
    }
]
```

**Scope:**
- Compute in `explorer.get_tradeoffs()` — iterate constraints × solutions
- Only for `objective_bound` and `cardinality` (the two types with measurable slack)
- Threshold: "binding" = within 5% of bound value (configurable later)
- No optimizer re-runs — pure analysis of existing frontier
- Agent narration via existing skill guidance (bottlenecks section)

**Not in scope:**
- Shadow prices / dual values (would require LP formulation, not applicable to evolutionary)
- Automatic constraint relaxation suggestions with re-runs
- Force_include/exclude binding analysis (binary — either active or not, no gradient)

**Skill update:** `optimization_strategy` Binding Constraint Detection section — add: "The `tradeoffs` response now includes `binding_analysis`. Use it to narrate bottlenecks with data instead of inference."

---

### [next] — Score Sensitivity Analysis

The `solution_interpreter` skill coaches agents to flag fragile solutions ("near the effort constraint — if estimates are off..."), but this is purely qualitative. The agent has no data on which scores actually matter.

**Goal:** Answer "which scores, if wrong, would change my answer?" — the most common unasked question in optimization.

**Approach: new `explore sensitivity` action.** Unlike binding analysis (which augments an existing view), sensitivity analysis is a deliberate investigative action — the user or agent asks for it.

**Method: perturbation-based.** For each score, perturb by ±10%, re-evaluate all current Pareto solutions, check which solutions gain or lose Pareto membership. No new optimization run — just re-evaluation of existing solutions against perturbed objective values.

**What to compute:**

For each score (option × objective pair):

| Field | Definition |
|---|---|
| `option` | Option name |
| `objective` | Objective name |
| `original_value` | Current score |
| `frontier_impact` | How many solutions change Pareto status when this score shifts ±10% |
| `sensitive` | Boolean — true if frontier_impact > 0 |

Aggregate to option-level and objective-level summaries:

```python
"sensitivity": {
    "most_sensitive_scores": [
        {"option": "Feature A", "objective": "Effort", "frontier_impact": 4},
        {"option": "Feature C", "objective": "Revenue", "frontier_impact": 3},
    ],
    "most_sensitive_options": ["Feature A", "Feature C"],  # ordered by total impact
    "most_sensitive_objectives": ["Effort", "Revenue"],     # ordered by total impact
    "robust_solutions": [1, 5, 7],    # solutions that survive all perturbations
    "fragile_solutions": [3, 12],     # solutions eliminated by any single perturbation
}
```

**Scope:**
- New `explore sensitivity` action in server + explorer
- Perturbation: ±10% per score (hardcoded; parameterize later if needed)
- Re-evaluate existing solutions only — no new optimization runs (fast)
- Top-N reporting (default 10 most sensitive scores) to avoid overwhelming output
- Works for both binary and proportional modes

**Not in scope:**
- Combined perturbations (changing multiple scores simultaneously) — combinatorial explosion
- Confidence-weighted sensitivity (requires score metadata we don't have)
- Automatic score improvement suggestions
- Integration with data collection ("go research this score more carefully")

**Skill update:** `solution_interpreter` Sensitivity Intuition section — add: "Use `explore sensitivity` to ground fragility claims in data. Lead with the most sensitive scores: 'If Feature A's effort estimate is off by 10%, 4 of your 12 solutions would change.'"

**Depends on:** Solving the Pareto re-evaluation efficiently. Current frontier sizes (5-50 solutions, 5-30 options, 2-5 objectives) make brute-force feasible — O(solutions × scores × objectives) per perturbation direction.

---

### [next] — Question Anchor in Problem Framing

The upstream translation maps **Question → Method**, but the skill jumps straight to objectives without coaching the agent to capture the user's question explicitly. The `model` tool stores `domain` and `context` but doesn't distinguish the driving question.

**Goal:** Make the user's "How should we...?" question a first-class element that grounds the entire formulation and gets reflected back throughout.

**Approach: skill-only change** — no model or tool changes needed. The existing `domain` and `context` fields are sufficient storage. The gap is in agent behavior, not data model.

**Skill update to `problem_framing`:**

Add a "Question First" section at the top of Core Judgment (before Translating User Language):

```markdown
### Question First

Before objectives, options, or constraints — capture the user's question. Every
optimization problem starts with a "How should we...?" that grounds the formulation:

- "How should we allocate marketing budget across channels?"
- "Which features should we build in the next quarter?"
- "How should we balance cost and reliability in our vendor selection?"

**Reflect it back immediately**: "So your core question is: *How should we allocate
budget to maximize ROI while staying under $500K?* Let me help structure that."

This anchors the entire session. When the user drifts or adds complexity, return
to the question: "Does this still serve your core question, or has the question
changed?"

**Store it**: Put the question in the `context` field via `model create` or
`model update`. It will be available to downstream skills for framing results
("To answer your question about budget allocation, here's what the optimization
found...").

**Approach selection flows from the question**:
- "Which ones should we pick?" → binary
- "How much should we put into each?" → proportional
- "How should we rank these?" → may not need optimization at all
```

**Why skill-only:** The question isn't a new data field — it's a framing discipline. Adding a `question` field to the Problem model would be overengineering. The `context` field already stores free-text problem context. The change is in how the agent uses it.

**Downstream connection:** The `solution_interpreter` should reference the question when presenting results. Add to the Downstream Translation section: "When presenting results, connect back to the user's original question: 'You asked how to allocate budget — here are the optimal allocations.'"

---

### [later] — Guided Data Collection

The `data_collection` skill is instruction-only. "Guided" means the tool actively assists:
- Suggest what to score next (highest-impact missing scores)
- Auto-research researchable scores (pricing, benchmarks)
- Track confidence per score
- Sensitivity analysis: which scores, if changed, would most affect the frontier

**Depends on:** Dogfooding to validate that score collection is actually the bottleneck. Score sensitivity analysis ([next-2]) would feed directly into this — "Feature A's effort score is the most sensitive; research it first."

### [later+] — Algorithm Routing

NSGA-II handles 2-6 objectives. NSGA-III for 4-7, MOEA/D for 8+. The `optimization_strategy` skill already describes this. Engine-side it's mechanical routing by objective count.

**Depends on:** Problems with 4+ objectives from dogfooding.

---

## Test Coverage

| Test file | Focus | Count |
|---|---|---|
| test_optimizer.py | Validation, NSGA-II, infeasibility, aggregation, new constraints | 38 |
| test_proportional.py | Proportional allocation, constraints, quality | 11 |
| test_server.py | MCP tool handlers, run history, reference points, scenarios, curation | 61 |
| test_explorer.py | Tradeoffs, comparisons, frontier navigation | ~20 |
| test_metrics.py | All metric layers, diagnostics | ~40 |
| test_models.py | Serialization round-trips | ~10 |
| test_store.py | JSON persistence | ~10 |
| eval_checkpoint.py | 14-phase end-to-end workflow | 550 checks |

**Total: 192 pytest tests, 550 eval checks, 0 failures.**

---

*Last updated: March 2026. Living document — update as decisions are made and dogfooding reveals friction.*

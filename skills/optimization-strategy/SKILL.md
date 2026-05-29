---
name: frontier-optimization-strategy
description: Read frontier://skills/optimization_strategy before running. Use when validating a problem, choosing solve mode, diagnosing infeasibility, interpreting solver diagnostics, or deciding whether to re-run after changes.
version: 1.0.0
---

# Optimization Strategy

*You are an operations researcher who knows which approach fits the problem. Your job is the contextual judgment that can't live in tool heuristics.*

## Expect Iteration

Frontier uses evolutionary (approximate) methods. Unlike exact solvers that prove optimality, evolutionary methods explore the solution space heuristically. This means:

- **The first run is exploration, not the answer.** It reveals the shape of the tradeoff space — where objectives conflict, which constraints bind, which options dominate. Use that insight to refine the formulation.
- **Effort shifts downstream.** The cognitive work isn't front-loaded in perfect formulation — it's in exploring and refining candidates. Working backwards from aspiration or forwards from baseline to discover what's feasible and preferred.
- **Few solutions on the first run is normal**, not failure. It usually means constraints are tight or objectives are correlated — both are useful signals that inform the next iteration.

Frame this for users: "The first run shows us the landscape. Now let's decide where to zoom in."

Iteration is also how Frontier closes the **partial optimization** and **silent relaxation** pitfalls (see `frontier://skills/problem_framing`). The frontier makes visible what a one-shot narrative would hide: whole regions of the decision space that weren't considered, and constraints that prose would have quietly routed around. Use the returned solutions, binding analysis, and correlations as the shared ground truth — don't reason about tradeoffs without first reading what the solver actually found.

## Solve Progression

The solve phase has its own sub-workflow:

| Step | What | Next step |
|---|---|---|
| **Validate** | Check readiness (≥2 objectives, ≥3 options, complete matrix, feasible constraints) | If issues → back to model to fix. If ready → run. |
| **Run** | Execute optimization, produce Pareto frontier | Examine results. |
| **Examine** | Assess solution count, diversity, constraint binding, diagnostic patterns | If healthy → move to explore. If problematic → back to model to adjust formulation, then re-run. |

The examine step is where most iteration happens. Few solutions? Constraints too tight — relax and re-run. Solutions clustered? Objectives may be correlated — consolidate and re-run. Key option never selected? Check its scores — adjust and re-run.

## Core Judgment

### Approach Selection

(See approach selection in `frontier://skills/problem_framing`.)

If the user describes ranking rather than selecting or allocating, they may not need optimization — suggest weighted scoring if there's a single dominant objective.

**Proportional mode solver differences:**
- Solutions assign integer percentages (0-100), summing to 100
- Cardinality constrains how many options receive non-zero allocation
- Uses continuous optimization (SBX crossover, polynomial mutation) — runs are slightly longer
- The optimizer may produce small allocations (1-2%). If this is undesirable, suggest tightening cardinality constraints

### Algorithm Awareness

The system selects the optimization algorithm based on objective count. Know the landscape so you can diagnose when results look wrong:

| Objectives | Algorithm | Why |
|---|---|---|
| 2-3 | NSGA-II | Crowding distance works; tradeoffs intuitive and solutions spread naturally |
| 4+ | NSGA-III | Reference points prevent clustering at extremes; handles constraints unlike decomposition methods |

**Implications**: With 7+ objectives, nearly everything appears "optimal" — probe whether all objectives genuinely conflict. With 2-3, expect a clean, intuitive frontier.

### Mode Selection

The `solve` tool accepts an optional `mode` parameter that controls how hard the optimizer works:

| Mode | When to use | What it does |
|---|---|---|
| **fast** (default) | Early iterations, exploring the tradeoff space, refining scores/constraints | Smaller populations, fewer generations — quick turnaround |
| **thorough** | Problem is finalized, locking in strategy, final run before presenting to stakeholders | Larger populations, more generations — better convergence and frontier coverage |

Parameters adapt automatically to problem complexity (option count, objective count, constraint density). Larger, more complex problems get proportionally more compute in both modes.

**When to suggest thorough**: The user has iterated on scores and constraints, scenarios are defined, and they're ready for a final answer. Say: *"The problem looks refined — shall I run in thorough mode for better convergence?"*

**When fast is fine**: The user is still exploring — adding options, adjusting scores, testing constraints. Fast mode gives quick feedback to inform the next iteration.

### Constraint Strategy

(See constraint types in `frontier://skills/problem_framing`.)

Classify user constraints by what they restrict: a bound on an objective value, inclusion/exclusion of a specific option, a relationship between options (mutual exclusion, dependency), or a limit on portfolio size or group composition. Don't over-constrain — fewer constraints produce a richer frontier and more useful tradeoffs.

### Infeasibility Response
When the solver returns no solutions:
- Check if cardinality is too tight given force_include/force_exclude.
- Check if objective bounds conflict with each other.
- Suggest relaxing the tightest constraint first.
- Ask the user: "Which of these constraints is most negotiable?"

### Status Literacy

A thin frontier is a diagnosis, not a result to hand over quietly. "Few solutions" has several distinct causes, and the solve response already carries the fields that separate them — read them and name the cause instead of returning a sparse set without comment.

- **No solutions at all** → infeasibility. See *Infeasibility Response* above: the constraints conflict, and the fix is to relax the tightest one.
- **Feasible but degenerate or uneven** → read `frontier_quality.status`. `POOR` means the front is empty or collapsed (fewer than 2 solutions, or every objective flat) — stop and treat it as a structural problem; don't present a single point as a choice set. `WARNING` means the front is real but uneven (clustered coverage, or one option taking nearly all allocation). Either way `frontier_quality.gates` names the check that failed (`frontier_returned` / `non_trivial` / `diverse`) and `issues[]` describes it in plain language — surface that rather than reinterpreting raw spacing or concentration numbers yourself.
- **Feasible but truncated** → check `frontier_complete`. When it's `False`, pruning cut the returned set below the full feasible frontier (`total_pareto_found > solutions_found`) — the user is seeing a representative sample, not everything. Say so before they reason about coverage or whether "nothing better exists."

This is the post-solve mirror of the *Formalization Checkpoint* (`frontier://skills/problem_framing`): there, confirm the model is right; here, confirm a small result is a real finding, not silence dressed as an answer. For translating these same fields when presenting to the user, see `frontier://skills/solution_interpreter` → *Frontier Quality and Completeness Signals*.

### Binding Constraint Detection

A binding constraint limits every (or nearly every) Pareto solution. Signs:
- All solutions sit at or near the constraint boundary
- Relaxing the constraint significantly changes the frontier
- The constraint prevents exploration of otherwise promising tradeoffs

When you detect a binding constraint, quantify the impact: *"Relaxing effort from ≤30 to ≤35 could dramatically expand the solution space. Is that limit truly non-negotiable?"* Suggest incremental relaxation, not removal.

For a richer view after solve, `explore tradeoffs` returns a `binding_analysis` block with shadow-price rates per binding constraint — how much each objective shifts per unit of slack relaxation, derived from the frontier's own slope. Use it to move the conversation from "this constraint is tight" to "it's costing you roughly $X per unit — worth negotiating?". See `frontier://skills/solution_interpreter` for presentation patterns.

### Reproducibility and Stability Checks

The `solve` tool accepts an optional `seed` for the optimizer's RNG. Either way, the response echoes `seed_used` so a run can be reproduced later even when the seed wasn't specified up front.

| Use | What to do |
|---|---|
| Share or revisit a specific frontier | Note the `seed_used` returned by the first run; pass it as `seed` on any re-run where you want the same result (same problem state + same seed → same frontier). |
| Check frontier stability | Re-run with different seeds on the same problem. Solutions shifting slightly is normal; the *shape* of the frontier (ranges, key tradeoffs) should be stable. If it isn't, the formulation is underspecified — objectives too correlated, constraints too loose, or not enough options. |
| Debug a "weird" result | Re-run with a different seed before assuming a modeling bug. Evolutionary search is stochastic; one run isn't the frontier, it's a sample of it. |

For `run_scenarios`, the parent `seed` is propagated deterministically to each scenario (per-scenario `seed_used` is derived from the parent + scenario name). So pinning the parent seed makes the whole multi-scenario run reproducible across processes — useful when sharing a scenario sweep or regression-testing.

Don't pin seeds by default — fresh seeds each run give you a free stability check as the user iterates. Pin only when reproducibility matters (handoff, regression, a specific frontier the user wants preserved).

### Stale Results

When the problem structure changes (objectives, options, scores, constraints, approach), results are marked stale rather than cleared. This preserves the previous run for comparison. The `results_stale` flag in the status tells you when re-running is recommended.

### Re-run Judgment
- User changed one score slightly → probably don't need to re-run, frontier won't change much. But mention it. Results are marked stale.
- User added/removed an option → re-run, portfolio space changed.
- User added/removed an objective → definitely re-run, the landscape is fundamentally different.
- User changed constraints → re-run.

### Curated Solution Survival

After re-running, automatically check curated solutions against the new frontier using `explore curated`. Report survival:
- "3 of your 5 curated solutions survived the constraint change"
- "'Conservative Pick' is still in the frontier. 'Growth Bet' was eliminated — the tighter effort bound excluded it."

If key curated solutions are eliminated, explain *why* (which constraint change caused it) and suggest alternatives from the new frontier.

### Run Comparison

After re-running, use `explore compare_runs` to explain what changed structurally:
- **Criteria diff**: which constraints were added, removed, or changed between runs
- **Frontier diff**: how solution count and objective ranges shifted
- **Option coverage diff**: which options gained or lost Pareto membership

This turns iteration from "re-run and hope" into cause-and-effect reasoning:
- "After relaxing the effort constraint, high-impact features started appearing in solutions — the constraint was masking an entire class of approaches."
- "Adding the new objective split previously identical solutions into distinct clusters — there was a hidden tradeoff."
- "Removing the correlated objective didn't change the frontier shape, confirming it was redundant."

### Iteration Coaching
- "The frontier gave you 12 solutions. That's a lot of tradeoff space. Want to add a constraint to narrow it?"
- "Only 2 solutions survived. Your constraints might be too tight."
- 5-10 solutions on the frontier is a healthy number for most decisions.
- Results don't match intuition about combinations? Check the **aggregation method** on objectives (sum vs avg vs min vs max vs quadratic). A sum-aggregated cost objective behaves very differently from an avg-aggregated one. If an objective depends on interactions between options, use quadratic aggregation with an interaction matrix.

### Scenario Results Interpretation

When scenarios are defined, optimization runs separately per scenario. At the examine step:
- **Robust options** appear in solutions across all scenarios — safer bets regardless of which future materializes.
- **Scenario-specific options** excel in particular futures — conditional picks.
- Frame recommendations by risk tolerance: conservative → robust options, balanced → probability-weighted, aggressive → scenario-specific bets.
- If all options perform similarly across scenarios, scenarios aren't adding insight — simplify.

## Activation
Use this expertise at the boundary between modeling and solving, and when interpreting solver results that suggest structural changes.

## Scope Boundaries
- **Owns:** Solve execution — validate→run→examine loop, mode selection, constraint strategy, infeasibility diagnosis, run comparison
- **Routes to solution_interpreter:** When results are healthy and ready for user presentation
- **Routes back to problem_framing:** When infeasibility or bad results indicate a structural problem (missing constraint, wrong objective, approach mismatch)
- **Routes back to data_collection:** When diagnostics suggest score quality issues (low variance driving flat frontiers, scale distortion)

## Guardrails
- Ensure the score matrix is complete before running — the optimizer requires every option scored on every objective.
- Let the user drive constraint additions — constraints should reflect real requirements, not be added just to shrink the frontier.
- Always diagnose infeasibility — when the solver returns no solutions, explain which constraints conflict and suggest the smallest relaxation that restores feasibility.

# Charging network siting

Pick which of 44 candidate EV fast-charging sites to build across five metros and two highway corridors, maximizing drivers served while holding down catchment overlap and build cost, under a $22M budget, a 10–16 site program, per-metro queue caps, competing-lot exclusions, a committed corridor flagship, and a public commitment that every metro gets a site. The first example with an **interaction matrix on a binary problem**: linear reach overstates coverage where catchments overlap — two downtown garages share the same drivers — so a quadratic overlap term carries the correction, and a top-N-by-reach ranking fails twice (7 Harborview picks against a cap of 4, three metros missed entirely; repaired, it lands at 80.7 k-drivers/day where the frontier reaches 99.3 at *less* overlap and *less* cost).

- **`problem.json`**: 3 objectives (DriversServed maximize `sum`, Overlap minimize **`quadratic`**, Cost minimize `sum`), binary approach, constraints (the $22M budget, 10–16 cardinality, per-metro `group_limit` **floors of 1** and caps of 4, corridor caps, the flagship `force_include`, 3 exclusion pairs), and two scenarios (`adoption_surge`, `grid_cost_inflation`).
- **`scores.json`**: the 44 sites scored per objective, plus the 44×44 `Overlap` interaction matrix (strong within a catchment — Harborview pairs most — near-zero across regions). Pairwise-only: triple-overlap is understated, stated here honestly.
- **`solutions.json`**: the exploratory NSGA `run` and the per-scenario `scenario_run`. No exact overlay — see the scope note below.

Load with `model load source="charging_network_siting"`, or paste this to an agent connected to Frontier:

> Map the frontier of build programs across drivers served, catchment overlap, and cost under the $22M budget. Then prove the public commitments: is every metro served, and the North-corridor flagship built, in every feasible program? What's the minimum coverage any legal program delivers — does 38 k-drivers/day hold, and does 43? Show how the picks shift if North-corridor adoption surges or metro grid quotes inflate 30%.

## The workflow

1. **Solve** (`solve run`, plus `solve run_scenarios`): the optimizer produces the reach/overlap/cost frontier; the scenarios re-map it under a corridor adoption surge (+40% corridor reach) and dense-metro grid-cost inflation (+30% Harborview costs).
2. **Explore the tradeoffs** (`explore tradeoffs`): the extremes, a balanced program, and the knees — the overlap axis is where clustered high-reach programs pay, the correction a ranking can't see.
3. **Audit the guarantees** (`explore audit`): one conjunctive call proves all six public commitments — the five metro floors and the flagship — hold in **every** feasible program. Then the emergent one: *every* feasible program serves at least 38 k-drivers/day (a floor written nowhere in the model — it falls out of the floors + budget + cardinality arithmetic), while 43 is `violated` with a concrete witness program serving 42.6.
4. **Decide** (`explore curate`): pin a few programs and commit on the tradeoffs.

**Exact-scope note.** Ask for `solve solver="highs"` here and the engine *declines, by design*: the exact MILP optimizes additive (`sum`) objectives, and `Overlap` is `quadratic` on a binary selection — outside that scope — so the response is a redefine hint, not a silent wrong answer. The audit beats above still run: audit is a *feasibility* solve, and a quadratic objective that no bound touches never enters the constraint region. For the certifiable quadratic sibling (minimize-`quadratic` on a *proportional* mean-variance shape), see [`supplier_selection`](../supplier_selection/); for the binary certify + audit arc on an all-`sum` shape, see [`claims_investigation_triage`](../claims_investigation_triage/).

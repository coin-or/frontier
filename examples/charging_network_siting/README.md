# Charging network siting

Pick which of 72 candidate EV fast-charging sites to build across seven metros and three highway corridors, maximizing drivers served while holding down catchment overlap and build cost, under a $34M budget, a 16–24 site program, per-metro queue caps, competing-lot exclusions, a committed corridor flagship, and a public commitment that every metro gets a site. The first example with an **interaction matrix on a binary problem**: linear reach overstates coverage where catchments overlap — two downtown garages share the same drivers — so a quadratic overlap term carries the correction, and a top-N-by-reach ranking fails twice (8 Harborview picks against a cap of 4, two metros missed entirely; repaired, it lands at 137.3 k-drivers/day where the frontier reaches 151.2 at *less* overlap and *less* cost).

- **`problem.json`**: 3 objectives (DriversServed maximize `sum`, Overlap minimize **`quadratic`**, Cost minimize `sum`), binary approach, constraints (the $34M budget, 16–24 cardinality, per-metro `group_limit` **floors of 1** and caps of 4, corridor caps, the flagship `force_include`, 5 exclusion pairs), and two scenarios (`adoption_surge`, `grid_cost_inflation`).
- **`scores.json`**: the 72 sites scored per objective, plus the 72×72 `Overlap` interaction matrix (strong within a catchment — Harborview pairs most — near-zero across regions). Pairwise-only: triple-overlap is understated, stated here honestly.
- **`solutions.json`**: the exploratory NSGA `run` and the per-scenario `scenario_run`. No exact overlay — see the scope note below.

Load with `model load source="charging_network_siting"`, or paste this to an agent connected to Frontier:

> Map the frontier of build programs across drivers served, catchment overlap, and cost under the $34M budget. Then prove the public commitments: is every metro served, and the North-corridor flagship built, in every feasible program? What's the minimum coverage any legal program delivers — does 53 k-drivers/day hold, and does 59? Show how the picks shift if North-corridor adoption surges or metro grid quotes inflate 30%.

## The workflow

1. **Solve** (`solve run`, plus `solve run_scenarios`): the optimizer produces the reach/overlap/cost frontier; the scenarios re-map it under a corridor adoption surge (+40% corridor reach) and dense-metro grid-cost inflation (+30% Harborview costs).
2. **Explore the tradeoffs** (`explore tradeoffs`): the extremes, a balanced program, and the knees — the overlap axis is where clustered high-reach programs pay, the correction a ranking can't see.
3. **Audit the guarantees** (`explore audit`): one conjunctive call proves all eight public commitments — the seven metro floors and the flagship — hold in **every** feasible program. Then the emergent one: *every* feasible program serves at least 53 k-drivers/day (a floor written nowhere in the model — it falls out of the floors + budget + cardinality arithmetic), while 59 is `violated` with a concrete witness program serving 58.0.
4. **Decide** (`explore curate`): pin a few programs and commit on the tradeoffs.

**Exact-scope note.** Ask for `solve solver="highs"` here and the engine *declines, by design*: the exact MILP optimizes additive (`sum`) objectives, and `Overlap` is `quadratic` on a binary selection — outside that scope — so the response is a redefine hint, not a silent wrong answer. The audit beats above still run: audit is a *feasibility* solve, and a quadratic objective that no bound touches never enters the constraint region. For the certifiable quadratic sibling (minimize-`quadratic` on a *proportional* mean-variance shape), see [`supplier_selection`](../supplier_selection/); for the binary certify + audit arc on an all-`sum` shape, see [`claims_investigation_triage`](../claims_investigation_triage/).

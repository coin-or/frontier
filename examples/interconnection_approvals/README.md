# Interconnection approvals

A regional grid operator approves which of 22 large-load interconnection requests to accept this cycle, alongside 8 enabling substation upgrades — maximizing net value while holding down capex and reliability risk, under zone queue caps, node-headroom rivalries, and the enabler structure that makes the problem combinatorial: upgrades carry **zero standalone value** and pay only through the requests they unlock, several requests share one enabler, and two speculative upgrades with no committed load should never be bought (the frontier confirms they never are). The **scenarios-on-binary showcase**: three capex envelopes ($180M / $240M / $300M) modeled as scenarios, so the deliverable isn't one portfolio — it's which approvals survive every budget, and what the next $60M actually buys.

- **`problem.json`**: 3 objectives (NetValue maximize, Cost / ReliabilityRisk minimize, all `sum`), binary approach, base constraints (the $240M capex bound, ≤6 approvals per zone, 12 request→upgrade dependencies, 3 exclusion pairs), and the three budget scenarios — each `constraint_overrides` list **restates the full constraint set** (overrides replace, not merge) with only the capex bound moved.
- **`scores.json`**: the 30 options scored per objective; enabler upgrades carry negative ReliabilityRisk (they relieve system stress), the two speculative ones carry nothing.
- **`solutions.json`**: the base NSGA `run`, the exact-MILP `exact_run` overlay, and the per-budget `scenario_run`.

Load with `model load source="interconnection_approvals"`, or paste this to an agent connected to Frontier:

> Map the approval frontier across net value, capex, and reliability risk at the $240M envelope, certify it exactly, then run the three budget scenarios and tell me: which approvals survive every envelope, what does moving from $240M to $300M actually buy, and which upgrades earn their cost only through what they unlock?

## The workflow

1. **Solve** (`solve run` + `solve run_scenarios`): the base frontier plus one frontier per capex envelope — max net value climbs $494M → $650M → $790M across the three budgets.
2. **Explore across budgets** (`explore scenario_frontiers`, `explore scenario_results`): the robustness read — R15 and R20 sit in the value-oriented plans at *every* envelope (approve-regardless), while R21 enters only at $300M: that's what the next $60M buys, and it's a nameable request, not a curve.
3. **Certify** (`solve solver="highs"` → `explore certify`): the exact overlay proves each base-frontier portfolio optimal for its tradeoff — and never spends a dollar on the two speculative upgrades, the cheapest sanity check in the bundle.
4. **Examine the enablers** (`explore composition`, `explore solutions`): U2 unlocks four requests and appears wherever two or more of them do — the enabler pays through what it unlocks, which is why ranking options by standalone value scores every upgrade last and still can't build the best portfolio.
5. **Decide** (`explore curate`): pin the portfolio per your capex conviction; the curated set carries across re-runs as the envelope firms up.

**Scale note.** Thirty options is deliberately readable — every approval can be narrated — while 2^30 portfolios with dependencies and exclusions is far past hand-pruning. For the same binary MILP arc at 120-option scale (where exact coverage reclaim is the headline), see [`capital_project_selection_120`](../capital_project_selection_120/); for scenarios that shock *scores* rather than the constraint set, see [`supplier_selection`](../supplier_selection/) and [`charging_network_siting`](../charging_network_siting/).

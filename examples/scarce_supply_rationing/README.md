# Scarce supply rationing

Split one quarter's constrained memory-chip supply across 36 customers whose committed demand runs ~1.8× what the fabs will deliver — every plan cuts someone, and the question is what protecting each account costs. Distributors pay spot (top revenue per share, near-zero strategic weight, fragile demand); hyperscale and tier-1 contracts pay less but carry the relationships — and the **contractual minimum shares** — the board protects. Proportional, purely linear (exact multi-objective **LP** with duals), and the per-option allocation-floor showcase: a single-objective Solver run lands on the max-revenue corner with the strategic mandate pinned at its floor, blind to the +22% strategic value the frontier offers for a 6% revenue concession.

- **`problem.json`**: 3 objectives (Revenue / StrategicValue maximize, DemandFragility minimize, all `sum`), proportional approach, constraints (8% anti-concentration cap; **per-customer floors** HYP-01 ≥ 6%, HYP-02 ≥ 5%, HYP-03 ≥ 4%, IND-01 ≥ 4%, IND-02 ≥ 3% — contractual minimums; credit caps on DST-01 and DST-02; a StrategicValue ≥ 4.8 board mandate), and two scenarios: `fab_outage` (**the floors rise** — same absolute commitments, ~25% less supply, so 6/5/4/4/3 become 8/7/5/5/4 as shares) and `spot_surge` (distributor Revenue +35%).
- **`scores.json`**: the 36 customers scored per 1% of supply, segment economics doing the conflict work.
- **`solutions.json`**: the exploratory NSGA `run`, the exact-LP `exact_run` overlay with solver duals, and the per-scenario `scenario_run`.

Load with `model load source="scarce_supply_rationing"`, then drive the workflow the way a user would — one ask per phase:

> 1. *“How could we split this quarter's supply? Show me the real tradeoffs between revenue, the strategic accounts, and demand we can't count on — and what happens if the fab outage hits or spot prices spike.”*
> 2. *“Keep the balanced split and the one that maximizes revenue. Are these optimal, or just plausible?”*
> 3. *“At the revenue-max split, what is each of our commitments costing — the board's mandate and every contract floor? Which would I renegotiate first?”*
> 4. *“If the fab outage happens, who absorbs the cut? Write up the recommendation for the allocation committee.”*

## The workflow

1. **Solve** (`solve run`, plus `solve run_scenarios`): the optimizer maps the rationing frontier and its two shocked variants — under `fab_outage` the raised floors eat share and the distributor segment absorbs it (average share 13.9% → 13.2%).
2. **Explore the tradeoffs** (`explore tradeoffs`): the extremes, a balanced split, and the knees — the max-revenue corner sits *at* the strategic mandate (4.84 against a floor of 4.8), which is exactly what a one-objective Solver run can't tell you it's paying.
3. **Certify and examine** (`solve solver="highs"` → `explore certify` → `explore sensitivity`): the exact LP overlay audits the heuristic frontier, and the duals do the explaining — the mandate's shadow price at the revenue corner, per-customer reduced costs with the floored accounts pinned (the price of each contractual minimum), and the near-miss customer one relaxation away from earning share.
4. **Decide** (`explore curate`): pin the split you'd defend to the board; curated picks carry across re-runs as supply firms up.

**Differentiation note.** [`production_mix`](../production_mix/) and [`budget_allocation`](../budget_allocation/) are the LP-duals siblings for *deploying* capacity you have; this is the rationing shape — demand exceeds supply, floors encode promises already made, and the scenario moves the *constraints* (commitments as shares) rather than the scores. The per-option floors are `allocation_bound` constraints, priced on the exact path; for the QP flavor of proportional allocation see [`supplier_selection`](../supplier_selection/).

# Scarce supply rationing

**The decision.** Split one quarter's constrained memory-chip supply across 36 customers whose committed demand runs ~1.8× what the fabs will deliver — every plan cuts someone, and the question is what protecting each account costs. Distributors pay spot (top revenue per share, near-zero strategic weight, fragile demand); hyperscale and tier-1 contracts pay less but carry the relationships — and the **contractual minimum shares** — the board protects.

**Why Frontier.** Proportional, purely linear (exact multi-objective **LP** with duals), and the per-option allocation-floor showcase: a single-objective Solver run lands on the max-revenue corner with the strategic mandate pinned at its floor, blind to the +22% strategic value the frontier offers for a 6% revenue concession.

**What ships here** — the raw inputs (step 1), the canonical model they frame into, and pre-solved results:

- **`data.csv`**: the raw inputs a decision owner would actually have — everything step 1 pastes.
- **`problem.json`**: 3 objectives (Revenue / StrategicValue maximize, DemandFragility minimize, all `sum`), proportional approach, constraints (8% anti-concentration cap; **per-customer floors** HYP-01 ≥ 6%, HYP-02 ≥ 5%, HYP-03 ≥ 4%, IND-01 ≥ 4%, IND-02 ≥ 3% — contractual minimums; credit caps on DST-01 and DST-02; a StrategicValue ≥ 4.8 board mandate), and two scenarios: `fab_outage` (**the floors rise** — same absolute commitments, ~25% less supply, so 6/5/4/4/3 become 8/7/5/5/4 as shares) and `spot_surge` (distributor Revenue +35%).
- **`scores.json`**: the 36 customers scored per 1% of supply, segment economics doing the conflict work.
- **`solutions.json`**: the exploratory NSGA `run`, the exact-LP `exact_run` overlay with solver duals, and the per-scenario `scenario_run`.

## The runbook

1. **Frame it from the raw inputs** — paste this ask, together with `data.csv`, into a fresh session:

   > We have one quarter of constrained memory-chip supply to divide across 36 customers, and
   > committed demand runs about 1.8× what the fabs will deliver — every plan cuts someone.
   > Attached (`data.csv`) is the account list: for each customer, the revenue ($M), strategic
   > value, and demand fragility we'd get **per 1% of the quarter's supply**, plus contractual
   > minimum shares and credit caps where they exist.
   >
   > The decision is what percent of supply each customer gets — shares must total 100%. We
   > want the most revenue and strategic value we can get while minimizing exposure to demand
   > that could evaporate.
   >
   > Hard rules:
   > - Anti-concentration: no customer above 8% of supply.
   > - The contractual minimums in the CSV are binding floors (HYP-01 ≥6%, HYP-02 ≥5%,
   >   HYP-03 ≥4%, IND-01 ≥4%, IND-02 ≥3%).
   > - The credit caps in the CSV are binding ceilings (DST-01 ≤4%, DST-02 ≤5%).
   > - Board mandate: total strategic value of the allocation must reach at least 4.8.
   >
   > Two futures I want stress-tested:
   > - **Fab outage** — supply drops ~25%. The absolute contractual commitments don't move,
   >   so as shares of the smaller quarter the five floors rise to 8/7/5/5/4. Every other rule
   >   stays as-is.
   > - **Spot surge** — spot pricing spikes ~35% on the distributor (DST) channel; contracts
   >   hold, so only DST revenue changes.

   Framing that input (`model create` + `model update`) lands on exactly this problem — the ask plus the data reconstruct `problem.json` and `scores.json` verbatim (guarded by `tests/test_upstream_kits.py`). `model load source="scarce_supply_rationing"` is the shortcut: it skips framing and restores the pre-solved runs too.

2. *“How could we split this quarter's supply? Show me the real tradeoffs between revenue, the strategic accounts, and demand we can't count on — and what happens if the fab outage hits or spot prices spike.”*
   `solve run` + `solve run_scenarios` → `explore tradeoffs` + `explore scenario_frontiers`: the rationing frontier plus both shocks — `fab_outage` restates the whole constraint set with *raised* floors (6/5/4/4/3 → 8/7/5/5/4: same commitments, less supply), and the distributor segment absorbs it (average share 13.9% → 13.2%).
3. *“Keep the balanced split and the one that maximizes revenue. Are these optimal, or just plausible?”*
   `explore curate` per pick (floored accounts read as pinned at the revenue corner — that's the story, not a defect) → `solve solver="highs"` → `explore certify`: the exact multi-objective-LP overlay; every point honors the floors and the mandate — the max-revenue corner sits *at* the mandate (4.84 vs 4.8).
4. *“At the revenue-max split, what is each of our commitments costing — the board's mandate and every contract floor? Which would I renegotiate first?”*
   `explore sensitivity` at the revenue corner (`source="exact"`): the mandate priced as a `model_bound` lever, **`floored_options`** giving each contract floor's price per point of allocation, near-misses, and `suggested_scenarios`. Duals rank, scenarios quantify — price a real renegotiation with a re-solve.
5. *“If the fab outage happens, who absorbs the cut? Write up the recommendation for the allocation committee.”*
   `explore scenario_results` (robustness tiers, per-scenario `varies`/`held_fixed` — name who shrinks, not just how much) → `explore curated format="markdown"`: lead with the floor prices — the mandate and the contracts are the levers management can renegotiate.

**Differentiation note.** [`production_mix`](../production_mix/) and [`budget_allocation`](../budget_allocation/) are the LP-duals siblings for *deploying* capacity you have; this is the rationing shape — demand exceeds supply, floors encode promises already made, and the scenario moves the *constraints* (commitments as shares) rather than the scores. The per-option floors are `allocation_bound` constraints, priced on the exact path; for the QP flavor of proportional allocation see [`supplier_selection`](../supplier_selection/).

# Community program funding

**The decision.** A city splits a participatory budget across 32 program proposals from six districts, maximizing community impact and residents served while holding down delivery risk — no program above 12% of the fund, blended delivery risk capped, and six council-mandated anchor floors (one per district) locking in the equity commitment that every district's flagship program is funded.

**Why Frontier.** Purely linear LP over a 32-way split with floors and a risk cap coupling every share — and the duals answer the question every council meeting argues about: *what do the equity commitments actually cost?* At the impact-max anchor the six guarantees split cleanly: one is priced — D4's flood-mitigation floor holds its program at 3% and costs ~1.85 impact-points per allocation point, the transfer the council is choosing to make — and five are free: the other districts' flagships earn the 12% cap on merit, floors slack.

**What ships here** — the raw inputs (step 1), the canonical model they frame into, and pre-solved results:

- **`data.csv`**: the raw inputs a budget office would actually have — everything step 1 pastes.
- **`problem.json`**: 3 objectives (CommunityImpact and ResidentsServed maximize, DeliveryRisk minimize; per-1%-of-fund rates, `sum`), proportional approach, 12% cap, a 2.6 delivery-risk ceiling, the six mandated floors, and the `overrun_wave` scenario.
- **`scores.json`**: the 32 programs' per-1% rates on each objective.
- **`solutions.json`**: the exploratory NSGA `run`, the per-scenario `scenario_run`, and the exact-LP `exact_run` overlay (HiGHS) with solver-exact duals per point.

## The runbook

1. **Frame it from the raw inputs** — paste this ask, together with `data.csv`, into a fresh session:

   > We're allocating next year's participatory budget across 32 community program
   > proposals from our six districts (`data.csv`): each has a community-impact rate,
   > residents served (thousands), and a delivery-risk rate, all per 1% of the fund.
   >
   > The decision is what percent of the fund each program gets — shares total 100%,
   > and a program can get nothing. Maximize total community impact and residents
   > served; minimize total delivery risk (all three scale with the share).
   >
   > Hard rules:
   > - No program above 12% of the fund.
   > - Blended delivery risk stays at or under 2.6.
   > - Council-mandated anchor floors (the `mandated_floor_pct` column): each district's
   >   flagship program keeps its minimum share — Youth-Jobs-Corps 5%,
   >   Neighborhood-Safety-Retrofit 6%, and Community-Health-Workers,
   >   Flood-Mitigation-Small, Summer-Youth-Employment, and Cooling-Centers 3% each.
   >
   > One future to stress-test:
   > - **Overrun wave** — construction and hiring overruns: every program's delivery
   >   risk reads 25% higher against the same risk cap.

   Framing that input (`model create` + `model update`) lands on exactly this problem — the ask plus the data reconstruct `problem.json` and `scores.json` verbatim (guarded by `tests/test_upstream_kits.py`). `model load source="community_program_funding"` is the shortcut: it skips framing and restores the pre-solved runs too.

2. *“How should we split the fund? Show me the real impact-versus-reach-versus-risk choices.”*
   `solve run` → `explore tradeoffs`: the three-objective funding frontier — extremes, a balanced split, and the knees.
3. *“Which splits survive an overrun wave?”*
   `solve run_scenarios` → `explore scenario_results`: the frontier re-solved with every risk rate 25% higher against the same 2.6 cap — which programs hold their share when the fund must lean safer.
4. *“Keep the balanced split and the impact-max one. Are these actually optimal?”*
   `explore curate` per pick → `solve solver="highs"` → `explore certify`: the exact LP overlay audits the heuristic frontier point-for-point (NSGA dominates no exact point).
5. *“What are the council's guarantees actually costing us?”*
   `explore sensitivity solution_id=<impact-max>`: solver-exact duals — the price-of-equity table. At the impact-max anchor, one floor is pinned and priced — Flood-Mitigation-Small held at its 3% floor, costing ~1.85 impact-points per unit of allocation — and five are free: Youth-Jobs-Corps, Community-Health-Workers, Summer-Youth-Employment, Neighborhood-Safety-Retrofit, and Cooling-Centers all earn the 12% cap on merit, floors slack (their reduced costs price the *cap*, saying they'd take more if allowed); the delivery-risk ceiling prices at ~1.15 impact-points per unit of risk. (Values as read at the impact-max anchor of the shipped exact overlay — duals are anchor-specific marginal rates; confirm a big move by re-solving with the changed floor.)
6. *“Write it up for the council packet.”*
   `explore curated format="markdown"`: the handoff table.

A free guarantee says the mandate aligns with merit; a priced one names the transfer the council is choosing to make. For allocation floors under scarcity see [`scarce_supply_rationing`](../scarce_supply_rationing/); for floors under correlated risk (QP), [`supplier_selection`](../supplier_selection/).

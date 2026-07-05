# Marketing channel budget

**The decision.** Split a media budget across 40 channel × audience/geo cells balancing four conflicting goals: Conversions, Reach, ROAS, and Brand Lift. Direct-response cells convert and return well but reach few people; broad upper-funnel cells reach and build brand but convert poorly – and same-audience cells overlap, so blended reach combines sub-additively and stacking one audience saturates.

**Why Frontier.** The approx-first showcase: audience overlap makes Reach a maximize-quadratic (blended reach = the square root of the overlap form), a structure beyond mean-variance – so this decision runs on the approximate frontier end to end, no exact pass, and loses nothing for it: coverage, scenarios, curation, and composition are solver-independent. The failure of hand allocation is concrete: rank-by-ROAS piles the budget into seven same-audience direct-response cells and blended reach collapses to 2.1, where the frontier holds 4.7 – 2.3× the reach – at a 2% conversions concession.

**What ships here** – the raw inputs (step 1), the canonical model they frame into, and pre-solved results:

- **`data.csv` + `reach_overlap.csv`**: the raw inputs a decision owner would actually have – everything step 1 pastes.
- **`problem.json`**: 4 objectives (Conversions / ROAS / Brand Lift averaged, Reach quadratic via the audience-overlap matrix), proportional approach, constraints (no cell >15%, ≤2 active cells per platform, blended ROAS ≥2.0x), and two scenarios (`signal_loss`, `demand_pullback`).
- **`scores.json`**: the 40 cells with per-cell scores, plus the Reach overlap matrix (diagonal = own reach squared; negative off-diagonals between same-platform and same-audience cells = shared eyeballs).
- **`solutions.json`**: the exploratory NSGA `run` plus the per-scenario `scenario_run`.

## The runbook

1. **Frame it from the raw inputs** – paste this ask, together with `data.csv` + `reach_overlap.csv`, into a fresh session:

   > We're splitting next quarter's media budget across 40 channel line items (`data.csv`):
   > conversions, reach, ROAS, and brand-lift ratings per cell, plus each cell's platform
   > and audience. Reach doesn't add linearly – cells sharing a platform or an audience
   > overlap, so blended reach is sub-additive; `reach_overlap.csv` carries the pairwise
   > overlap matrix our media team measured (diagonal = own reach squared, negative
   > entries = shared audience).
   >
   > The decision is what percent of the budget each cell gets – shares total 100%.
   > Maximize conversions, reach (with the overlap correction), ROAS, and brand lift
   > (allocation-weighted; reach combines through the overlap matrix).
   >
   > Hard rules:
   > - No cell above 15% of budget.
   > - At most 2 active cells per platform (the `platform_group` column).
   > - Blended ROAS must stay at or above 2.0x.
   >
   > Two futures to stress-test:
   > - **Signal loss** – measurement degrades: conversions read 20% lower across the board.
   > - **Demand pullback** – conversions −15% and ROAS −10% across the board.

   Framing that input (`model create` + `model update`) lands on exactly this problem – the ask plus the data reconstruct `problem.json` and `scores.json` verbatim (guarded by `tests/test_upstream_kits.py`). `model load source="channel_budget"` is the shortcut: it skips framing and restores the pre-solved runs too.

2. *"How should we split the media budget across these 40 cells? Show me the real tradeoffs – remembering that cells sharing an audience overlap rather than add – and what happens if measurement degrades or demand pulls back."*
   `solve run` + `solve run_scenarios` → `explore tradeoffs`: the Conversions/Reach/ROAS/Brand-Lift frontier (Reach combining sub-additively via the overlap matrix) plus the `signal_loss` and `demand_pullback` scenario frontiers.
3. *"Our performance team wants to allocate by ROAS. What would that miss?"*
   `explore compare`: the by-ROAS plan (top seven ROAS cells at their caps – three CRM cells and three shopper cells stacked on the same audiences) evaluates to Conversions 32.6 / Reach 2.1 / Brand 15.0; the frontier holds a point at Conversions 31.9 / Reach 4.7 / Brand 19.4 – 2.3× the reach and a third more brand lift for a 2% conversions concession. The reach-max corner (8.6) shows the far end of what overlap-aware spreading buys.
4. *"Where do diminishing returns kick in, and which limit is holding the mix back?"*
   `explore tradeoffs` knees + `explore sensitivity`: the saturation is visible as the frontier flattens toward the reach corner; the examine reports the frontier-inferred binding analysis (this shape carries no solver duals – the tradeoff prices are read off the frontier itself).
5. *"Keep the balanced split and the conversion-max one, and write the plan up for the growth review."*
   `explore curate` per pick → `explore curated format="markdown"`: the handoff table.

This example runs entirely on the approximate frontier by design: the overlap term makes Reach a maximize-quadratic, beyond the exact solver's convex minimize-risk scope – the workflow's exploration layer carries it whole. For the exact mean-variance counterpart, where the quadratic is a minimize-risk term, see [`supplier_selection`](../supplier_selection/) and [`investment_portfolio`](../investment_portfolio/).

# Marketing channel budget

**The decision.** Split a media budget across 22 channel × audience/geo combinations balancing four conflicting goals: Conversions, Reach, ROAS, and Brand Lift. Direct-response channels convert and return well but reach few people; broad upper-funnel channels reach and build brand but convert poorly, and same-audience channels overlap, so reach combines sub-additively.

**Why Frontier.** Too combinatorial and interaction-laden for a spreadsheet or an LLM to allocate by hand.

**What ships here** — the raw inputs (step 1), the canonical model they frame into, and pre-solved results:

- **`data.csv` + `reach_overlap.csv`**: the raw inputs a decision owner would actually have — everything step 1 pastes.
- **`problem.json`**: 4 objectives (Conversions / ROAS / Brand Lift averaged, Reach quadratic via an audience-overlap matrix), proportional approach, constraints (no channel >15%, ≤1 line item per platform, blended ROAS ≥2.0x), and two scenarios (`signal_loss`, `demand_pullback`).
- **`scores.json`**: the 22 channels with per-channel scores, plus the Reach audience-overlap interaction matrix (negative off-diagonals between same-audience channels = diminishing combined reach).
- **`solutions.json`**: the exploratory NSGA `run` plus the per-scenario `scenario_run`.

## The runbook

1. **Frame it from the raw inputs** — paste this ask, together with `data.csv` + `reach_overlap.csv`, into a fresh session:

   > We're splitting next quarter's media budget across 22 channel line items (`data.csv`):
   > conversions, reach, ROAS, and brand-lift ratings per line item, plus which platform
   > each belongs to. Reach doesn't add linearly — line items sharing an audience overlap,
   > so combined reach is sub-additive; `reach_overlap.csv` carries the pairwise overlap
   > matrix our media team measured (negative = shared audience).
   >
   > The decision is what percent of the budget each line item gets — shares total 100%.
   > Maximize conversions, reach (with the overlap correction), ROAS, and brand lift
   > (allocation-weighted; reach combines through the overlap matrix).
   >
   > Hard rules:
   > - No line item above 15% of budget.
   > - At most one active line item per platform group (the `platform_group` column).
   > - Blended ROAS must stay at or above 2.0x.
   >
   > Two futures to stress-test:
   > - **Signal loss** — measurement degrades: conversions read 20% lower across the board.
   > - **Demand pullback** — conversions −15% and ROAS −10% across the board.

   Framing that input (`model create` + `model update`) lands on exactly this problem — the ask plus the data reconstruct `problem.json` and `scores.json` verbatim (guarded by `tests/test_upstream_kits.py`). `model load source="channel_budget"` is the shortcut: it skips framing and restores the pre-solved runs too.

2. *“How should we split the marketing budget across these 22 channels? Show me the real tradeoffs — remembering that channels sharing an audience overlap rather than add — and what happens if measurement signal degrades or demand pulls back.”*
   `solve run` + `solve run_scenarios` → `explore tradeoffs`: the Conversions/Reach/ROAS/Brand-Lift frontier (Reach combining sub-additively via the overlap matrix) plus the `signal_loss` and `demand_pullback` scenario frontiers.
3. *“Where do diminishing returns kick in, and which limit is holding the mix back?”*
   `explore tradeoffs` knees + `explore sensitivity`: maximizing Reach is a non-convex quadratic, so the exact backend *declines* this shape — no certificate; the examine reports the frontier-inferred binding analysis instead.
4. *“Keep the balanced split and the conversion-max one, and write the plan up for the growth review.”*
   `explore curate` per pick → `explore curated format="markdown"`: the handoff table.

This example stays on the heuristic frontier: the audience-overlap term makes Reach a maximize-quadratic, outside the exact solver's convex minimize-risk scope. For the exact mean-variance counterpart, where the quadratic is a minimize-risk term, see [`supplier_selection`](../supplier_selection/) and [`investment_portfolio`](../investment_portfolio/).

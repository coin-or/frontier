# Runbook — investment portfolio (continuous QP path, exact duals + scenarios)

Five prompts driving FRAME → SCORE → EXPLORE → CURATE → CERTIFY → EXAMINE → DECIDE over this
example. Each prompt is a natural user ask spanning several workflow steps — the Tools and
Expect lines tell the driving agent what should fire and what shape comes back. FRAME and
SCORE are pre-baked in `problem.json` / `scores.json` (including the covariance matrix and
three macro scenarios), so step 1 loads them. The README stays the narrative overview; this is
the paste-and-drive script.

1. **Load and understand the decision**
   Prompt: *"Load the investment portfolio example. What am I allocating, and what rules am I
   already living with?"*
   Tools: `model` (action=load, then get/summary) → `solve` (action=validate).
   Expect: a `problem_id`; 3 objectives (Return↑, Volatility↓ quadratic, Yield↑), 30 funds,
   proportional approach, the caps (single-fund, per-sector, volatility bound) and the
   `recession` / `inflation` / `rate_cuts` scenarios echoed back; `ready: true` with the shape
   exact-supported.

2. **See the allocations — across the macro futures**
   Prompt: *"How should we allocate? Show me the return/risk/yield tradeoffs, and how the
   picture changes in a recession, an inflation run, or rate cuts."*
   Tools: `solve` (action=run) → `solve` (action=run_scenarios) → `explore` (action=tradeoffs)
   → `explore` (action=scenario_frontiers).
   Expect: the base frontier with extremes / balanced / `inflection_point_candidates` (with
   `rationale`); a per-scenario frontier per macro regime; tradeoffs flags
   `scenarios_available` so the narration layers in robustness.

3. **Shortlist, then check these are optimal**
   Prompt: *"Keep the balanced portfolio and the calmest one. Are these optimal, or just
   decent?"*
   Tools: `explore` (action=curate, per pick) → `solve` (solver="highs") → `explore`
   (action=certify).
   Expect: `curated: true` per pick plus a `quality` gate — on this proportional shape the
   distribution checks are live (single-fund concentration, allocations pinned at the cap);
   the exact mean-variance QP overlay; the certificate's `dominance_audit`, `coverage`,
   `invariant`, and `corner_sharpening` (strongest at the volatility corner), plus
   `quality_gates` over the certified points.

4. **What moves the needle, and what survives**
   Prompt: *"At the balanced portfolio, which of my rules is costing me the most — and which
   allocations hold up across all three macro futures?"*
   Tools: `explore` (action=sensitivity) → `explore` (action=scenario_results).
   Expect: `source: solver_exact` with `where_to_invest` (shadow prices per lever),
   `near_misses` and `capped_options` (reduced costs), the `frontier_shadow_price_trend`, and
   `suggested_scenarios` seeded from the top levers (duals rank, scenarios quantify; copy a
   suggestion's `motivated_by` onto any scenario created from it). Then `option_robustness`
   tiers (core / common / marginal), `scenario_risk` (expected, worst-case, CVaR), and
   per-scenario `varies` + `held_fixed` lines restating exactly what each scenario changed.

5. **The write-up**
   Prompt: *"Write the shortlist up for the investment committee."*
   Tool: `explore` (action=curated, format="markdown").
   Expect: the handoff table with per-finalist `quality`, and the stakeholder-writeup pointer
   (context → decided → why → confidence → impact → next steps).

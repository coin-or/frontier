# Runbook — scarce supply rationing (continuous LP path, allocation-floor duals)

Five prompts driving FRAME → SCORE → EXPLORE → CURATE → CERTIFY → EXAMINE → DECIDE over this
example. Each prompt is a natural user ask spanning several workflow steps — the Tools and
Expect lines tell the driving agent what should fire and what shape comes back. FRAME and
SCORE are pre-baked in `problem.json` / `scores.json` (including the two shock scenarios), so
step 1 loads them. The README stays the narrative overview; this is the paste-and-drive
script — and the pricing showcase: step 4 reads what every promise in the model costs,
straight from the solver's duals.

1. **Load and understand what's already promised**
   Prompt: *"Load the supply rationing example. What am I deciding here, and what promises are
   already baked in before I start?"*
   Tools: `model` (action=load, then get/summary) → `solve` (action=validate).
   Expect: a `problem_id`; 3 objectives (Revenue↑, StrategicValue↑, DemandFragility↓), 36
   customers, proportional approach; the echo should read the constraints as *commitments* —
   five contractual minimum shares, two distributor credit caps, the 8% concentration limit,
   the board's StrategicValue ≥ 4.8 mandate — plus the `fab_outage` / `spot_surge` scenarios;
   `ready: true` with the shape exact-supported.

2. **See the ways to split it — including the bad quarters**
   Prompt: *"How could we split this quarter's supply? Show me the real tradeoffs between
   revenue, the strategic accounts, and demand we can't count on — and what happens if the fab
   outage hits or spot prices spike."*
   Tools: `solve` (action=run) → `solve` (action=run_scenarios) → `explore` (action=tradeoffs)
   → `explore` (action=scenario_frontiers).
   Expect: the base frontier with extremes / balanced / knees; one frontier per shock. The
   `fab_outage` scenario restates the whole constraint set with *raised* floors (6/5/4/4/3 →
   8/7/5/5/4) — same absolute commitments, less supply — and the narration should say so.

3. **Shortlist, then check these are actually optimal**
   Prompt: *"Keep the balanced split and the one that maximizes revenue. Are those genuinely
   the best versions of themselves, or just plausible?"*
   Tools: `explore` (action=curate, per pick) → `solve` (solver="highs") → `explore`
   (action=certify).
   Expect: `curated: true` per pick with the proportional `quality` checks live (the floored
   accounts *will* read as pinned at the revenue corner — that's the story, not a defect); the
   exact multi-objective-LP overlay; the certificate's `dominance_audit`, `coverage`,
   `invariant`, and `quality_gates`. Every overlay point honors the floors and the mandate.

4. **What are our promises costing us?**
   Prompt: *"At the revenue-max split, what is each of our commitments actually costing —
   the board's mandate and every contract floor? Which one would I renegotiate first?"*
   Tool: `explore` (action=sensitivity, solution_id=the revenue corner, source="exact").
   Expect: `source: solver_exact` with the reads in decision language — `where_to_invest`
   including a role-`model_bound` lever (the mandate, priced: relaxing it one unit buys ~that
   much revenue); **`floored_options`** (each contract floor's price per point of allocation —
   the account held above what it would earn); `capped_options` / `near_misses`; and
   `suggested_scenarios` seeded from the top levers. Duals rank, scenarios quantify — price a
   real renegotiation with a re-solve before quoting it.

5. **Who takes the hit, and the write-up**
   Prompt: *"If the fab outage happens, who absorbs the cut? Then write up the recommendation
   for the allocation committee."*
   Tools: `explore` (action=scenario_results) → `explore` (action=curated, format="markdown").
   Expect: `option_robustness` tiers, `scenario_risk`, and per-scenario `varies` + `held_fixed`
   lines restating exactly what each shock changed — the distributor segment's share shrinks
   under the outage; name who, not just how much. Then the handoff table with per-finalist
   `quality` and the stakeholder-writeup pointer — lead with the floor prices: the mandate and
   the contracts are the levers management can actually renegotiate.

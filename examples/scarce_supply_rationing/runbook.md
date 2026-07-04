# Runbook — scarce supply rationing (continuous LP path, allocation-floor duals)

Ordered prompts walking FRAME → SCORE → EXPLORE → CURATE → CERTIFY → EXAMINE → DECIDE over this
example, each naming the MCP tool it exercises and the response shape to expect. FRAME and SCORE
are pre-baked in `problem.json` / `scores.json` (including the two shock scenarios), so step 1
loads them. The README stays the narrative overview; this is the paste-and-drive script — and
the pricing showcase: step 5 reads what every promise in the model costs, straight from the
solver's duals.

1. **FRAME + SCORE — load the model**
   Prompt: *"Load the scarce_supply_rationing example and summarize what decision it frames."*
   Tool: `model` (action=load, then get/summary).
   Expect: a `problem_id`; 3 objectives (Revenue↑, StrategicValue↑, DemandFragility↓, all
   linear), 36 options, proportional approach, the 8% global cap, the five per-customer
   contractual floors, two distributor credit caps, the StrategicValue ≥ 4.8 mandate, and the
   `fab_outage` / `spot_surge` scenarios echoed back.

2. **EXPLORE — base frontier and the shock futures**
   Prompt: *"Map the revenue/strategic/fragility frontier, and how it shifts if a fab outage
   raises the contractual floors or spot pricing spikes."*
   Tools: `solve` (action=run) → `solve` (action=run_scenarios) → `explore` (action=tradeoffs) →
   `explore` (action=scenario_frontiers).
   Expect: the base frontier with extremes / balanced / knees; one frontier per shock. Note the
   `fab_outage` scenario restates the whole constraint set with *raised* floors (6/5/4/4/3 →
   8/7/5/5/4) — same absolute commitments, less supply.

3. **CURATE — shortlist with names**
   Prompt: *"Pin the balanced split and the max-revenue corner."*
   Tool: `explore` (action=curate, per solution).
   Expect: `curated: true` per pick plus a `quality` gate — on this proportional shape the
   distribution checks are live (single-customer concentration, allocations pinned at bounds;
   the floored accounts *will* read as pinned at the revenue corner — that's the story, not a
   defect).

4. **CERTIFY — exact LP overlay**
   Prompt: *"Solve it exactly and certify the frontier."*
   Tools: `solve` (solver="highs") → `explore` (action=certify).
   Expect: the exact multi-objective-LP overlay; the certificate's `dominance_audit`,
   `coverage`, `invariant`, `corner_sharpening`, and `quality_gates`. Every overlay point
   honors the floors and the mandate — the exact path enforces the model's own bounds.

5. **EXAMINE — what every promise costs (the duals)**
   Prompt: *"At the max-revenue split, what does each commitment cost us?"*
   Tool: `explore` (action=sensitivity, solution_id=the revenue corner, source="exact").
   Expect: `source: solver_exact` with four reads in decision language —
   `where_to_invest` including a role-`model_bound` lever (the strategic mandate, priced:
   relaxing it by one unit buys ~that much revenue); **`floored_options`** (each contractual
   floor's price per point of allocation — the account held above what it would earn);
   `capped_options` / `near_misses` (reduced costs); and `suggested_scenarios` seeded from the
   top levers. Duals rank, scenarios quantify: price a real move with a re-solve before quoting
   it.

6. **EXAMINE — who absorbs the shock**
   Prompt: *"Who absorbs the cut when the fab outage raises the floors?"*
   Tool: `explore` (action=scenario_results).
   Expect: `option_robustness` tiers, `scenario_risk` per objective, and per-scenario `varies` +
   `held_fixed` lines restating exactly what each shock changed (the outage varies the
   constraint set; the spot surge varies distributor Revenue scores). The distributor segment's
   share shrinks under the outage — name who, not just how much.

7. **DECIDE — the handoff**
   Prompt: *"Export the shortlist and write it up."*
   Tool: `explore` (action=curated, format="markdown").
   Expect: the handoff table with per-finalist `quality`, and the stakeholder-writeup pointer —
   lead with the floor prices: the board's mandate and the contracts are the levers management
   can actually renegotiate, and this is the analysis that prices them.

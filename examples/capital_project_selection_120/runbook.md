# Runbook — capital project selection (binary MILP path)

Five prompts driving FRAME → SCORE → EXPLORE → CURATE → CERTIFY → EXAMINE → DECIDE over this
example. Each prompt is a natural user ask spanning several workflow steps — the Tools and
Expect lines tell the driving agent what should fire and what shape comes back. FRAME and
SCORE are pre-baked in `problem.json` / `scores.json`, so step 1 loads them. The README stays
the narrative overview; this is the paste-and-drive script.

1. **Load and sanity-check the decision**
   Prompt: *"Load the capital project selection example. What decision does it frame, and does
   the setup even have room to work with?"*
   Tools: `model` (action=load, then get/summary) → `solve` (action=validate) → `explore`
   (action=audit, no property).
   Expect: a `problem_id`; 4 objectives (NPV↑, Cost↓, Risk↓, StrategicFit↑), 120 projects, the
   budget / category caps / dependencies / exclusions / portfolio-size range echoed back in
   plain terms; `ready: true`; audit verdict `feasible` with a concrete witness plan. (Tighten
   the budget into contradiction and the verdict flips to `no_feasible_plan`, with `conflicts`
   naming a minimal set of constraints that cannot all hold together — leads to relax, never
   auto-relaxed.)

2. **See the real funding options**
   Prompt: *"Which projects should we fund? Show me the real choices — where we can push value,
   where risk bites, and where the budget actually pinches."*
   Tools: `solve` (action=run) → `explore` (action=tradeoffs).
   Expect: a frontier `run`; tradeoffs with `objective_ranges`, `extreme_solutions`,
   `balanced_solution`, `inflection_point_candidates` (each with a `jump_factor` and one-line
   `rationale`), `binding_analysis` (which caps and the budget bind), and `option_selection`
   consensus stats.

3. **Shortlist, then check the numbers are real**
   Prompt: *"Keep the balanced plan and the safest one as finalists. And how much should I
   trust these — are they actually the best versions of themselves?"*
   Tools: `explore` (action=curate, per pick) → `solve` (solver="highs") → `explore`
   (action=certify).
   Expect: `curated: true` per pick plus a `quality` gate (GOOD / WARNING / DEGENERATE, with
   the triggering check named — flagged finalists stay in the set; the call is yours); the
   exact-MILP overlay in `exact_run`; a certificate with `dominance_audit` (how many heuristic
   points exact strictly beats — the headline at 120 binary options), `coverage`, the
   `invariant`, `corner_sharpening`, and `quality_gates`.

4. **The sign-off questions**
   Prompt: *"What's the tightest lever on this portfolio, what should we stress-test, and can
   you guarantee we never blow the risk ceiling no matter which feasible plan we land on?"*
   Tools: `explore` (action=sensitivity) → `explore` (action=audit, with a property).
   Expect: integer selections carry no solver duals, so sensitivity returns the
   `frontier_inferred` binding analysis plus `suggested_scenarios` seeded from the most binding
   constraints (copy a suggestion's `motivated_by` onto any scenario created from it). The
   property audit returns `holds` (proven over every feasible plan), `violated` (with a
   counterexample witness), or `inconclusive` (with the raw solver status — not evidence
   either way).

5. **The write-up**
   Prompt: *"Write the shortlist up for the investment review."*
   Tool: `explore` (action=curated, format="markdown").
   Expect: the handoff table with a `quality` column per finalist and the stakeholder-writeup
   pointer (context → decided → why → confidence → impact → next steps).

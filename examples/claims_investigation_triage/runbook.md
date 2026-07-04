# Runbook — claims investigation triage (binary MILP + governance audit path)

Five prompts driving FRAME → SCORE → EXPLORE → CURATE → CERTIFY → EXAMINE → DECIDE over this
example. Each prompt is a natural user ask spanning several workflow steps — the Tools and
Expect lines tell the driving agent what should fire and what shape comes back. FRAME and
SCORE are pre-baked in `problem.json` / `scores.json`, so step 1 loads them. The README stays
the narrative overview; this is the paste-and-drive script — and the governance showcase:
step 4 proves guarantees over the *whole feasible space*, not just the frontier.

1. **Load and sanity-check the decision**
   Prompt: *"Load the claims triage example. What am I deciding, and is it workable as set up?"*
   Tools: `model` (action=load, then get/summary) → `solve` (action=validate) → `explore`
   (action=audit, no property).
   Expect: a `problem_id`; 3 objectives (ExpectedRecovery↑, Hours↓, Friction↓), 180 claims, the
   1,170-hour capacity / $4,840k recovery target / per-line caps / six referrals echoed back in
   plain terms; `ready: true`; audit verdict `feasible` with a concrete witness plan. (Tighten
   the recovery target past ~$4,990k and the verdict flips to `no_feasible_plan`, with
   `conflicts` naming a minimal set of commitments that cannot all hold together.)

2. **See the real options — including the bad month**
   Prompt: *"Which claims should we work this month? Show me my real choices across recovery,
   hours, and how much we'd annoy legitimate customers — and how the picture changes if the CAT
   event pulls one of my seniors."*
   Tools: `solve` (action=run) → `solve` (action=run_scenarios) → `explore` (action=tradeoffs).
   Expect: a frontier `run` and a `capacity_cut` scenario frontier; tradeoffs with ranges,
   extremes, a balanced plan, knees, and `binding_analysis` (the hours capacity and the Auto
   line cap bind). The narration should surface the friction axis — the thing a
   recovery-per-hour ranking can't see.

3. **Shortlist, then check the numbers are real**
   Prompt: *"Keep the balanced plan and the gentlest one that still hits the target. How much
   should I trust these?"*
   Tools: `explore` (action=curate, per pick) → `solve` (solver="highs") → `explore`
   (action=certify).
   Expect: `curated: true` per pick with a `quality` gate; the exact-MILP overlay in
   `exact_run`; a certificate whose `dominance_audit` is the scale story here — at 180 binary
   options the exact overlay dominates a large fraction of the heuristic points — plus
   `coverage`, the `invariant`, and `quality_gates`.

4. **What's guaranteed, no matter what we pick**
   Prompt: *"Is there any legal plan that skips the regulator referrals or any of the four
   big-ticket claims? And is LIA-1002 covered too?"*
   Tools: `explore` (action=audit, audit_property=a LIST of ten force_include dicts) →
   `explore` (action=audit, one force_include dict for LIA-1002).
   Expect: first call verdict `holds` with a per-`properties` breakdown (ten × `holds`) — a
   proof over every feasible plan in one call. The four whales are *not* force_included
   anywhere: drop any one and the book can't reach the recovery target inside the hours cap,
   so their inclusion is a theorem of the constraint set — narrate that emergence ("every plan
   happens to include them" is an observation; `holds` is a proof). Second call: `violated`
   with a concrete `witness` plan that skips LIA-1002 — the guarantee has a sharp edge.

5. **What's limiting us, and the write-up**
   Prompt: *"What's holding us back, what should we stress-test next quarter, and write this
   up for the claims committee."*
   Tools: `explore` (action=sensitivity) → `explore` (action=curated, format="markdown").
   Expect: integer selections carry no solver duals, so sensitivity returns the
   `frontier_inferred` binding analysis plus `suggested_scenarios` seeded from the most binding
   constraints (copy a suggestion's `motivated_by` onto any scenario created from it); then the
   handoff table with per-finalist `quality` and the stakeholder-writeup pointer — lead the
   writeup with the audited guarantee, since it holds no matter which finalist is picked.

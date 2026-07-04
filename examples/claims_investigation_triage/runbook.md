# Runbook — claims investigation triage (binary MILP + governance audit path)

Ordered prompts walking FRAME → SCORE → EXPLORE → CURATE → CERTIFY → EXAMINE → DECIDE over this
example, each naming the MCP tool it exercises and the response shape to expect. FRAME and SCORE
are pre-baked in `problem.json` / `scores.json`, so step 1 loads them. The README stays the
narrative overview; this is the paste-and-drive script — and the governance showcase: steps 6–7
prove guarantees over the *whole feasible space*, not just the frontier.

1. **FRAME + SCORE — load the model**
   Prompt: *"Load the claims_investigation_triage example and summarize what decision it frames."*
   Tool: `model` (action=load, then get/summary).
   Expect: a `problem_id`; 3 objectives (ExpectedRecovery↑, Hours↓, Friction↓, all `sum`), 180
   options, the 1,170-hour cap / $4,840k recovery floor / per-line caps / six referrals /
   45–100 cardinality echoed back, plus the `capacity_cut` scenario.

2. **Pre-solve check**
   Prompt: *"Is the model ready to solve? Probe feasibility exactly."*
   Tools: `solve` (action=validate), `explore` (action=audit, no property).
   Expect: `ready: true` with the `solvers` block noting the shape is exact-supported; audit
   verdict `feasible` with a concrete witness plan. (Tighten the recovery floor past ~$4,990k
   and the verdict flips to `no_feasible_plan`, with `conflicts` naming a minimal set of
   constraints that cannot all hold together.)

3. **EXPLORE — map the frontier and the capacity shock**
   Prompt: *"Map the recovery/hours/friction frontier, and how it degrades if a CAT deployment
   cuts capacity to 1,140 hours."*
   Tools: `solve` (action=run) → `solve` (action=run_scenarios) → `explore` (action=tradeoffs).
   Expect: a frontier `run`; tradeoffs with `objective_ranges`, extremes / balanced /
   `inflection_point_candidates`, and `binding_analysis` (the hours cap and the Auto line cap
   bind); a `capacity_cut` scenario frontier.

4. **CURATE — shortlist with names**
   Prompt: *"Pin the balanced plan and the low-friction end as finalists."*
   Tool: `explore` (action=curate, per solution).
   Expect: `curated: true` per pick plus a `quality` gate (GOOD / WARNING / DEGENERATE, with the
   triggering check named). Flagged finalists stay in the set — the call is yours.

5. **CERTIFY — prove the finalists**
   Prompt: *"Solve it exactly and certify the frontier."*
   Tools: `solve` (solver="highs") → `explore` (action=certify).
   Expect: the exact-MILP overlay in `exact_run`; a certificate whose `dominance_audit` is the
   scale story here — at 180 binary options the exact overlay dominates a large fraction of the
   heuristic points — plus `coverage`, the `invariant`, `corner_sharpening`, and `quality_gates`.

6. **EXAMINE — the compound guarantee (one conjunctive call)**
   Prompt: *"Prove that every critical claim — the six regulator referrals plus PRP-1001,
   LIA-1001, PRP-1002, WC-1001 — is investigated in every feasible plan."*
   Tool: `explore` (action=audit, audit_property=a LIST of ten force_include dicts).
   Expect: verdict `holds` with a per-`properties` breakdown (ten × `holds`) — a proof over the
   whole feasible region in one call. The four whales are *not* force_included anywhere: drop
   any one and the book can't reach the recovery floor inside the hours cap, so their inclusion
   is a theorem of the constraint set. Narrate that emergence — it's the difference between
   "every frontier plan happens to include them" (an observation) and `holds` (a proof).

7. **EXAMINE — the boundary of the guarantee**
   Prompt: *"Is LIA-1002 also guaranteed?"*
   Tool: `explore` (action=audit, audit_property=one force_include dict).
   Expect: verdict `violated` with a concrete `witness` — a feasible plan that skips it. The
   guarantee has a sharp, provable edge; present the witness as a plan, entity-native.

8. **EXAMINE — what's binding, and what to stress-test**
   Prompt: *"What's the tightest lever?"*
   Tool: `explore` (action=sensitivity).
   Expect: integer selections carry no solver duals, so sensitivity returns the
   `frontier_inferred` binding analysis plus `suggested_scenarios` seeded from the most binding
   constraints (copy a suggestion's `motivated_by` onto any scenario you create from it).

9. **DECIDE — the handoff**
   Prompt: *"Export the shortlist and write it up for the review."*
   Tool: `explore` (action=curated, format="markdown").
   Expect: the handoff table with a `quality` column per finalist and the stakeholder-writeup
   pointer (context → decided → why → confidence → impact → next steps) — lead the writeup with
   the audited guarantee, since it's the part that holds no matter which finalist is picked.

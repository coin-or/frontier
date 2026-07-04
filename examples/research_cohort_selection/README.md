# Research cohort selection

Pick exactly 24 of 144 screened volunteers for a biomarker study, maximizing signal strength while holding down retention risk and per-participant cost. The conflict is built into the screening reality: the highest-expression volunteers sit at the expensive academic centers and carry the most dropout risk, so a top-24-by-signal list lands entirely in one stratum — the floors require all six. Exact-K selection (`cardinality min=max=24`) over C(144,24) ≈ 10^28 possible cohorts, with per-stratum **floors** and per-site caps, all-`sum` objectives — certifiable — and the **emergent-guarantee audit**: prove a cap nobody wrote down.

- **`problem.json`**: 3 objectives (SignalStrength maximize, RetentionRisk / CostPerParticipant minimize, all `sum`), binary approach, and the structural-diversity constraints (exactly 24; stratum floors 4/4/4/3/3/2 with a deliberately loose stated cap of 8; at most 4 per site; three same-household exclusion pairs; one screen-failed volunteer `force_exclude`d — the data-hygiene beat).
- **`scores.json`**: the 144 volunteers scored per objective, signal clustering at the costly high-dropout sites by construction.
- **`solutions.json`**: the exploratory NSGA `run` plus the exact-MILP `exact_run` overlay — every point exactly 24 volunteers, floors held.

Load with `model load source="research_cohort_selection"`, or paste this to an agent connected to Frontier:

> Map the frontier of 24-person cohorts across signal strength, retention risk, and cost, certify it exactly, and then tell me something the constraints don't say: what's the most rare-variant (F) volunteers any feasible cohort can carry — does "at most 6" hold across every legal cohort, and does "at most 5"?

## The workflow

1. **Solve** (`solve run`): the optimizer produces the signal/risk/cost frontier of exact-24 cohorts.
2. **Explore the tradeoffs** (`explore tradeoffs`): the extremes, a balanced cohort, and the knees — the frontier reaches ~99% of the ranking's signal at lower risk *and* lower cost, because the floors leave real choice inside each stratum.
3. **Certify** (`solve solver="highs"` → `explore certify`): the exact MILP overlay proves each cohort optimal for its tradeoff; integer selections carry no duals, so the examine falls back to the frontier-inferred binding read (the site caps and stratum floors bind — the floor read reports what one extra member above the floor buys).
4. **Audit the emergent guarantee** (`explore audit`): the model states stratum F may hold up to 8 — but audit "at most 6 from F" and the verdict is `holds`, across every feasible cohort. Nobody wrote 6 anywhere: the floors on A–E (4+4+4+3+3) against K=24 *imply* it. Audit "at most 5" and it flips to `violated`, with a witness cohort carrying exactly 6. A constraint set has consequences its authors didn't state; audit is how you discover and prove them.
5. **Decide** (`explore curate`): pin the cohorts you'd take to the steering committee.

**Emergence note.** This is the audit flavor [`claims_investigation_triage`](../claims_investigation_triage/) doesn't show: triage proves a *stated-policy* guarantee (mandated claims always investigated); here the guarantee is *unstated arithmetic* — the interplay of exact-K and floors tightening a loose cap from 8 to a provable 6. Same tool, different epistemics: one verifies the model encodes the policy, the other reveals what the policy entails. For the same exact-K + floors mechanics at selection-with-budget scale, see [`capital_project_selection_120`](../capital_project_selection_120/).

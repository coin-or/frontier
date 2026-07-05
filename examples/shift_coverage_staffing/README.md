# Float-pool shift coverage

**The decision.** A regional hospital accepts which of 120 per-diem shift offers (30 nurses × five units × day/night blocks) go into next month's float pool – maximizing patient-demand-weighted coverage value while holding down cost and fatigue risk, under a $210k budget, a 60–80 roster size, per-unit coverage floors, a 3-block cap per nurse, and same-block exclusions.

**Why Frontier.** 2^120 candidate rosters with floors, caps, and exclusions coupling every acceptance – and the governance layer earns its keep: `explore audit` proves guarantees across *every* feasible roster, including two nobody wrote down. No night-coverage rule exists in the model, yet ICU, ED, and MedSurg each provably keep at least 2 night blocks in every feasible roster (the unit floors exceed each unit's day supply – the arithmetic forces nights); and no feasible roster costs less than ~$185.7k, a provable minimum spend for finance.

**What ships here** – the raw inputs (step 1), the canonical model they frame into, and pre-solved results:

- **`data.csv`**: the raw inputs a staffing office would actually have – everything step 1 pastes.
- **`problem.json`**: 3 objectives (CoverageValue maximize, Cost and FatigueRisk minimize, all `sum` totals), binary approach, and the roster constraints (budget, size range, unit floors, per-nurse caps, same-block exclusions).
- **`scores.json`**: the 120 offers scored on each objective.
- **`solutions.json`**: the exploratory NSGA `run` plus the exact-MILP `exact_run` overlay (HiGHS).

## The runbook

1. **Frame it from the raw inputs** – paste this ask, together with `data.csv`, into a fresh session:

   > We're filling next month's float pool and I want help picking which per-diem shift
   > offers to accept (`data.csv`): 120 offers, each with the nurse, unit, block (week ×
   > day/night), a coverage-value rating, cost ($k), and a fatigue-risk score.
   >
   > The decision is which offers to accept – each one is in or out. We want the most
   > total coverage value at the least total cost and fatigue risk.
   >
   > Hard rules:
   > - Total cost stays within the $210k float budget.
   > - Accept between 60 and 80 offers.
   > - Unit coverage floors: at least 12 ICU, 14 ED, 12 MedSurg, 8 Oncology, and 8 LD
   >   offers accepted.
   > - No nurse works more than 3 accepted blocks.
   > - A nurse offering two units in the same block works at most one of them.

   Framing that input (`model create` + `model update`) lands on exactly this problem – the ask plus the data reconstruct `problem.json` and `scores.json` verbatim (guarded by `tests/test_upstream_kits.py`). `model load source="shift_coverage_staffing"` is the shortcut: it skips framing and restores the pre-solved runs too.

2. *"Which offers should we accept? Show me the real coverage-versus-cost-versus-burnout choices."*
   `solve run` → `explore tradeoffs`: the three-objective roster frontier – the coverage-max roster (5,097 points at the full $210k), the lean roster (4,776 points at $197k), and the low-fatigue roster (1,190 fatigue points), most rosters landing at the 60-offer floor.
3. *"Keep the balanced roster and the lean one. Are these actually optimal?"*
   `explore curate` per pick → `solve solver="highs"` → `explore certify`: the exact-MILP overlay (47 certified points; NSGA dominates no exact point).
4. *"Before I sign the roster: can you guarantee every unit keeps night coverage, whichever feasible roster we land on – and what's the least this pool can cost?"*
   `explore audit` with a compound property: ICU, ED, and MedSurg each keep **≥2 night blocks in every feasible roster** – proven in one conjunctive call, and *emergent*: no night rule exists in the model; the unit floors exceed each unit's day supply, so the arithmetic forces nights. And the minimum-spend probe: **Cost ≥ $185.7k holds across every feasible roster** (at $186.1k the audit returns a concrete counterexample roster instead) – the number finance can plan on.
5. *"Write the roster up for the staffing huddle."*
   `explore curated format="markdown"`: the handoff table.

Integer selections carry no solver duals: `explore sensitivity` returns the frontier-inferred binding analysis. For the audit flagship with regulator-mandated referrals see [`claims_investigation_triage`](../claims_investigation_triage/); for exact-K selection with stratum floors, [`research_cohort_selection`](../research_cohort_selection/).

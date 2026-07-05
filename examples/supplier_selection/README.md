# Supplier selection

**The decision.** Split a production order across 25 global suppliers balancing cost, reliability, lead time, ESG risk, and correlated regional disruption: the cheap suppliers are slower, less reliable, and riskier, and the per-region caps plus the quadratic concentration term make it too combinatorial for a spreadsheet or an LLM alone.

**Why Frontier.** The minimize-risk quadratic puts it on Frontier's exact mean-variance (QP) path.

**What ships here** — the raw inputs (step 1), the canonical model they frame into, and pre-solved results:

- **`data.csv` + `concentration_interactions.csv`**: the raw inputs a decision owner would actually have — everything step 1 pastes.
- **`problem.json`**: 5 objectives (Cost / LeadTime / ESGRisk / ConcentrationRisk minimize, Reliability maximize; ConcentrationRisk is quadratic), proportional approach, constraints (≤15% per supplier, ≤3 active suppliers per region, weighted reliability ≥78), and two scenarios (`china_disruption`, `demand_surge`).
- **`scores.json`**: 25 suppliers across 6 regions with per-objective scores, plus the `ConcentrationRisk` interaction matrix (high within-region correlation, ~0 across regions).
- **`solutions.json`**: the exploratory NSGA `run`, the exact mean-variance QP `exact_run` overlay (HiGHS) with solver-exact duals per point, and the per-scenario `scenario_run`.

## The runbook

1. **Frame it from the raw inputs** — paste this ask, together with `data.csv` + `concentration_interactions.csv`, into a fresh session:

   > We're splitting a production order across 25 global suppliers (`data.csv`): unit cost,
   > reliability, lead time, and ESG risk ratings, plus each supplier's region. Regional
   > disruptions are correlated — concentrating within a region compounds the risk — so
   > `concentration_interactions.csv` carries the pairwise concentration-risk matrix (high
   > within a region, near zero across regions).
   >
   > The decision is what percent of the order each supplier gets — shares total 100%.
   > Minimize cost, lead time, ESG risk, and correlated concentration risk; maximize
   > reliability (allocation-weighted; concentration risk combines through the matrix).
   >
   > Hard rules:
   > - No supplier above 15% of the order.
   > - At most 3 active suppliers per region.
   > - Weighted reliability must stay at or above 78.
   >
   > Two futures to stress-test:
   > - **China disruption** — export controls and logistics backlogs throttle every CN
   >   supplier to at most 5% of the order; every other rule stays as-is.
   > - **Demand surge** — per-supplier capacity tightens: the cap drops from 15% to 10%;
   >   every other rule stays as-is.

   Framing that input (`model create` + `model update`) lands on exactly this problem — the ask plus the data reconstruct `problem.json` and `scores.json` verbatim (guarded by `tests/test_upstream_kits.py`). `model load source="supplier_selection"` is the shortcut: it skips framing and restores the pre-solved runs too.

2. *“How should we split the order across these 25 suppliers, keeping regional concentration in check? Show me the real cost/reliability/lead-time/ESG choices — and how they hold up if a China disruption throttles the CN suppliers or demand surges.”*
   `solve run` + `solve run_scenarios` → `explore tradeoffs`: the five-objective sourcing frontier plus per-scenario frontiers for `china_disruption` (every CN supplier throttled to ≤5% of the order) and `demand_surge` (per-supplier capacity tightens to 10%).
3. *“Keep the balanced mix and the most reliable one. Are these actually optimal?”*
   `explore curate` per pick → `solve solver="highs"` → `explore certify`: the exact mean-variance QP overlay, sharpest at the minimum-concentration-risk corner.
4. *“Which of our rules costs us the most, and which supplier just missed the cut?”*
   `explore sensitivity`: solver-exact duals — whether a region cap or the reliability floor is the binding lever, the closest near-miss supplier, and which sit pinned at a cap.
5. *“Write it up for the sourcing review.”*
   `explore curated format="markdown"`: the handoff table.

For the same QP shape in finance, see [`investment_portfolio`](../investment_portfolio/); for the energy version, [`capacity_planning`](../capacity_planning/).

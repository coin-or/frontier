# Supplier selection

Split a production order across 25 global suppliers balancing cost, reliability, lead time, ESG risk, and correlated regional disruption: the cheap suppliers are slower, less reliable, and riskier, and the per-region caps plus the quadratic concentration term make it too combinatorial for a spreadsheet or an LLM alone. The minimize-risk quadratic puts it on Frontier's exact mean-variance (QP) path.

- **`problem.json`**: 5 objectives (Cost / LeadTime / ESGRisk / ConcentrationRisk minimize, Reliability maximize; ConcentrationRisk is quadratic), proportional approach, constraints (≤15% per supplier, ≤3 active suppliers per region, weighted reliability ≥78), and two scenarios (`china_disruption`, `demand_surge`).
- **`scores.json`**: 25 suppliers across 6 regions with per-objective scores, plus the `ConcentrationRisk` interaction matrix (high within-region correlation, ~0 across regions).
- **`solutions.json`**: the exploratory NSGA `run` plus the per-scenario `scenario_run`.

Load with `model load source="supplier_selection"`, or paste this to an agent connected to Frontier:

> How should we split the order across these 25 suppliers? Show me the real cost/reliability/lead-time/ESG choices — keeping regional concentration in check — how they hold up if China goes offline or demand surges, then check the finalists are actually optimal and tell me which of our rules costs us the most.

## The workflow

1. **Solve** (`solve run`, plus `solve run_scenarios` for the disruption scenarios): the optimizer produces the multi-sourcing frontier across the five objectives and a per-scenario frontier for `china_disruption` (those suppliers offline) and `demand_surge` (per-supplier capacity tightens to 10%).
2. **Explore the tradeoffs** (`explore tradeoffs`): the extremes, a balanced plan, the knees, and how resilient each mix is across the scenarios.
3. **Certify and examine** (`solve solver="highs"` → `explore certify` → `explore sensitivity`): the exact mean-variance QP overlay audits the heuristic frontier and sharpens the minimum-concentration-risk corner; the duals show which constraint (a region cap, the reliability floor) is the binding lever, which supplier is the closest near-miss, and which sit pinned at a cap.
4. **Decide** (`explore curate`): pin a few sourcing plans and commit on the tradeoffs.

For the same QP shape in finance, see [`investment_portfolio`](../investment_portfolio/); for the energy version, [`capacity_planning`](../capacity_planning/).

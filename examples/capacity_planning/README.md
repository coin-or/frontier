# Generation capacity planning

Choose a generation capacity mix (share %) across 22 candidate projects to balance the energy trilemma: cheap power is dirty or intermittent, while clean and firm power is expensive. Too combinatorial and too constrained for a spreadsheet, and the correlated-intermittency risk is nonlinear, so an LLM can't reason it through alone. The minimize-risk quadratic puts it on Frontier's exact mean-variance (QP) path.

- **`problem.json`**: 5 objectives (LCOE / CO2 / VariabilityRisk / LandUse minimize, Firmness maximize; VariabilityRisk is quadratic), proportional approach, constraints (no project >25%, a group limit per technology, CO2 ≤0.20 t/MWh, Firmness ≥50), and two scenarios (`carbon_price`, `low_renewables_year`).
- **`scores.json`**: 22 projects across 9 technologies with LCOE/CO2/Firmness/LandUse/VariabilityRisk scores, plus the VariabilityRisk covariance matrix (stacking correlated renewables raises portfolio risk super-linearly).
- **`solutions.json`**: the exploratory NSGA `run` plus the per-scenario `scenario_run`.

Load with `model load source="capacity_planning"`, then drive the workflow the way a user would — one ask per phase:

> 1. *“Help me build the generation mix from these 22 projects. Show me the real tradeoffs between cost, carbon, firmness, variability, and land use — and how they shift in a low-renewables year.”*
> 2. *“Keep the balanced mix and the firmest one. Are these actually optimal?”*
> 3. *“Which limit binds hardest — the CO2 cap or the firmness floor — and what would relaxing it buy?”*
> 4. *“Write it up for the planning board.”*

## The workflow

1. **Solve** (`solve run`, plus `solve run_scenarios` for the scenarios): the optimizer produces the capacity-mix frontier across the five objectives and a per-scenario frontier for `carbon_price` and `low_renewables_year` (solar and wind correlations rise).
2. **Explore the tradeoffs** (`explore tradeoffs`): the extremes, a balanced mix, the knees, and how robust each mix is across the scenarios.
3. **Certify and examine** (`solve solver="highs"` → `explore certify` → `explore sensitivity`): the exact mean-variance QP overlay audits the heuristic frontier and sharpens the minimum-variability-risk corner; the duals show which constraint (the CO2 cap, the Firmness floor) is the binding lever, which project is the closest near-miss, and which sit pinned at a cap.
4. **Decide** (`explore curate`): pin a few capacity mixes and commit on the tradeoffs.

For the same QP shape, see [`supplier_selection`](../supplier_selection/) and [`investment_portfolio`](../investment_portfolio/).

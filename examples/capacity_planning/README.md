# Generation capacity planning

**The decision.** Choose a generation capacity mix (share %) across 22 candidate projects to balance the energy trilemma: cheap power is dirty or intermittent, while clean and firm power is expensive.

**Why Frontier.** Too combinatorial and too constrained for a spreadsheet, and the correlated-intermittency risk is nonlinear, so an LLM can't reason it through alone. The minimize-risk quadratic puts it on Frontier's exact mean-variance (QP) path.

**What ships here** — the raw inputs (step 1), the canonical model they frame into, and pre-solved results:

- **`data.csv` + `variability_interactions.csv` + `variability_low_renewables.csv`**: the raw inputs a decision owner would actually have — everything step 1 pastes.
- **`problem.json`**: 5 objectives (LCOE / CO2 / VariabilityRisk / LandUse minimize, Firmness maximize; VariabilityRisk is quadratic), proportional approach, constraints (no project >25%, CO2 ≤0.20 t/MWh, Firmness ≥50), and two scenarios (`carbon_price`, `low_renewables_year`).
- **`scores.json`**: 22 projects across 9 technologies with LCOE/CO2/Firmness/LandUse/VariabilityRisk scores, plus the VariabilityRisk covariance matrix (stacking correlated renewables raises portfolio risk super-linearly).
- **`solutions.json`**: the exploratory NSGA `run`, the exact mean-variance QP `exact_run` overlay (HiGHS) with solver-exact duals per point, and the per-scenario `scenario_run`.

## The runbook

1. **Frame it from the raw inputs** — paste this ask, together with `data.csv` + `variability_interactions.csv` + `variability_low_renewables.csv`, into a fresh session:

   > We're choosing a generation capacity mix across 22 candidate projects (`data.csv`):
   > LCOE ($/MWh), CO2 (t/MWh), a firmness rating, a variability-risk rating, and land use,
   > plus each project's technology. Stacking correlated renewables compounds portfolio
   > variability — `variability_interactions.csv` carries the pairwise covariance our
   > planners use (correlated within a resource region, near zero across).
   >
   > The decision is each project's share of the mix — shares total 100%. Minimize cost,
   > carbon, correlated variability risk, and land use; maximize firmness
   > (allocation-weighted; variability combines through the covariance matrix).
   >
   > Hard rules:
   > - No project above 25% of the mix.
   > - Portfolio CO2 at or below 0.20 t/MWh.
   > - Portfolio firmness at or above 50.
   >
   > Two futures to stress-test:
   > - **Carbon price** — LCOE reads 15% higher across the board.
   > - **Low renewables year** — resource correlation worsens: swap in the
   >   `variability_low_renewables.csv` covariance; everything else unchanged.

   Framing that input (`model create` + `model update`) lands on exactly this problem — the ask plus the data reconstruct `problem.json` and `scores.json` verbatim (guarded by `tests/test_upstream_kits.py`). `model load source="capacity_planning"` is the shortcut: it skips framing and restores the pre-solved runs too.

2. *“Help me build the generation mix from these 22 projects. Show me the real tradeoffs between cost, carbon, firmness, variability, and land use — and how they shift in a low-renewables year.”*
   `solve run` + `solve run_scenarios` → `explore tradeoffs`: the five-objective capacity frontier plus per-scenario frontiers for `carbon_price` and `low_renewables_year`.
3. *“Keep the balanced mix and the firmest one. Are these actually optimal?”*
   `explore curate` per pick → `solve solver="highs"` → `explore certify`: the exact mean-variance QP overlay, sharpest at the minimum-variability-risk corner.
4. *“Which limit binds hardest — the CO2 cap or the firmness floor — and what would relaxing it buy?”*
   `explore sensitivity`: solver-exact duals naming the binding lever, the closest near-miss project, and which sit pinned at a cap.
5. *“Write it up for the planning board.”*
   `explore curated format="markdown"`: the handoff table.

For the same QP shape, see [`supplier_selection`](../supplier_selection/) and [`investment_portfolio`](../investment_portfolio/).

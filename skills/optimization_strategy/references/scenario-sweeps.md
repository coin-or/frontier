# Optimization Strategy — Scenario Sweep Discipline

Construction discipline for scenario sweeps, factored out of the `frontier://skills/optimization_strategy` core (its *Sensitivity vs Scenario Analysis* section carries the short form and the produce/read split). Fetch before constructing scenarios: `get_skill('optimization_strategy', section='Sweep Discipline — Constructing Scenarios')`.

## Sweep Discipline — Constructing Scenarios

- **Vary exactly what the scenario names — hold every other anchor fixed.** One lever per scenario keeps the reading causal; bundled changes are fine only when the bundle *is* the named state of the world. When the swept parameter sits inside a larger definition (a score that feeds an aggregate, a cap inside a group), re-derive the dependent quantities from the current question rather than inheriting stale constants. Remember `constraint_overrides` replace the *whole* base constraint set — restate the unchanged constraints, or the sweep silently varies more than it names. The engine restates each scenario's `varies` / `held_fixed` in `scenario_results`; check it matches your intent.
- **A discontinuity is a finding about your assumptions until verified.** When one sweep point flips feasibility or steps an objective sharply, first identify the modeling choice that creates the break (a replace-all override, a threshold crossing, an integer cliff). If a plausible alternative reading of the parameter removes the break, report both readings and let the user pick — not just the dramatic one.

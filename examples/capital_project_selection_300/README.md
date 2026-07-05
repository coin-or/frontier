# Capital project selection (300 projects)

**The decision.** Pick which of 300 capital projects to fund, maximizing total NPV and strategic value while holding down total cost and risk exposure, under a hard $1,550M budget with per-category caps, dependencies, mutual exclusions, and a portfolio-size range (45–100) – stress-tested against 12% cost inflation and a delivery crunch that caps execution at 70 projects.

**Why Frontier.** Binary (each project in or out), 4 objectives, combinatorial constraints: at this scale the exact-MILP frontier covers materially more of the tradeoff surface than a fixed-resolution metaheuristic, the canonical explore-fast-then-certify showcase.

**What ships here** — the raw inputs (step 1), the canonical model they frame into, and pre-solved results:

- **`data.csv`**: the raw inputs a decision owner would actually have — everything step 1 pastes.
- **`problem.json`**: 4 objectives (NPV and StrategicFit maximize, Cost and Risk minimize, all `sum` totals), binary approach, and the combinatorial constraints (budget, category caps, dependencies, exclusions, portfolio-size range).
- **`scores.json`**: the 300 projects scored on each objective.
- **`problem.json`** also carries the two scenarios (`cost_inflation`, `delivery_crunch`).
- **`solutions.json`**: the exploratory NSGA `run`, the per-scenario `scenario_run`, and the exact-MILP `exact_run` overlay (HiGHS or cuOpt).

## The runbook

1. **Frame it from the raw inputs** — paste this ask, together with `data.csv`, into a fresh session:

   > We're finalizing next cycle's capital plan and I want help picking the portfolio. Attached
   > is our project list (`data.csv`): 300 candidates, each scored with NPV ($M), cost ($M), a
   > risk score, and a strategic-fit score, plus its category, any enabler project it requires,
   > any project it's mutually exclusive with, and whether it's already committed.
   >
   > The decision is which projects to fund — each one is in or out. We want the most total NPV
   > and total strategic fit we can get while holding down total spend and total risk exposure.
   >
   > Hard rules:
   > - Total cost must stay within the $1,550M budget.
   > - Fund between 45 and 100 projects.
   > - Category caps: at most 20 Growth, 15 Digital, 15 R&D, and 18 Maintenance projects.
   >   Compliance and Efficiency are uncapped.
   > - A project with a `requires` entry can only be funded if that enabler is funded too.
   > - For each mutually-exclusive pair, fund at most one.
   > - The seven projects marked `committed` are already contracted — they must be in.
   >
   > Two futures to stress-test:
   > - **Cost inflation** — construction and equipment run 12% over estimate across the
   >   board; the $1,550M budget holds, so the same envelope buys fewer projects.
   > - **Delivery crunch** — the delivery org can execute at most 70 projects; the
   >   portfolio-size range tightens to 45–70.

   Framing that input (`model create` + `model update`) lands on exactly this problem — the ask plus the data reconstruct `problem.json` and `scores.json` verbatim (guarded by `tests/test_upstream_kits.py`). `model load source="capital_project_selection_300"` is the shortcut: it skips framing and restores the pre-solved runs too.

2. *“Which projects should we fund? Show me the real choices — where we can push value, where risk bites, and where the budget pinches.”*
   `solve run` → `explore tradeoffs`: the NPV/cost/risk/strategic-fit frontier — extremes, a balanced plan, inflection points, and the binding read (the budget and category caps).
3. *“Keep the balanced plan and the safest one as finalists. How much should I trust these?”*
   `explore curate` per pick (each carries a `quality` gate) → `solve solver="highs"` → `explore certify`: the exact-MILP overlay names which heuristic points it dominates — the headline at 300 binary options — plus coverage, the NSGA-never-dominates invariant, and corner sharpening. When a finalist lands among the dominated points, re-curate its exact counterpart (`explore curate` on the certified point that beats it) so the step-6 handoff carries certified plans.
4. *“Which picks survive cost inflation, and what does the delivery crunch cost us?”*
   `solve run_scenarios` → `explore scenario_results`: the frontier re-solved per future — which projects hold their place when every cost reads 12% higher against the same $1,550M, and what the 45–70 execution cap prices out (the base frontier's median portfolio is 70 projects, so the crunch bites half of it).
5. *“What's the tightest lever, and can you guarantee we never blow the risk ceiling, whichever feasible plan we land on?”*
   `explore sensitivity` → `explore audit`: integer selections carry no solver duals, so sensitivity returns the frontier-inferred binding analysis plus `suggested_scenarios`; the audit proves a property over **every** feasible plan (`holds`) or returns a counterexample witness.
6. *“Write the shortlist up for the investment review.”*
   `explore curated format="markdown"`: the handoff table with per-finalist quality and the stakeholder-writeup pointer.

**Aggregation note.** All four objectives are totals (`sum`): a capital *deployment* decision wants the most total value the budget buys, with the binding budget and caps mediating portfolio size. Per-project *quality* (average strategic-fit or risk *level*) would be `avg`, which answers a different fixed-size question and falls outside the exact-MILP's linear scope. For `avg` / `quadratic` aggregation on a continuous shape, see [`investment_portfolio`](../investment_portfolio/).

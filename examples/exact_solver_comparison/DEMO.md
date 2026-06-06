# Live demo — explore → certify on the capital plan (coverage-led)

The notebook (`exact_solver_comparison.ipynb`) carries the *charts*; this is the **live
native-workflow walkthrough** (web UI / MCP) showing the complementary **explore → certify**
loop on the headline decision, `capital_project_selection_120` — a 120-project binary MILP.

Numbers below come from the engine the MCP server wraps, against the bundle's shipped overlay
(`solutions.json`) — i.e. exactly what a live `explore certify` returns.

## Demo mechanic (read first)
A **cold** exact solve on this MILP is ~157 s and currently overruns a synchronous MCP turn
(an async/background `solve` is the proper fix, tracked separately). For the demo, the exact
overlay is **pre-baked** into `solutions.json` (`run` = NSGA frontier, `exact_run` = HiGHS
overlay), so `explore certify` returns instantly. Do **not** trigger a cold `solve(solver=highs)`
live on this problem.

## Walkthrough
1. **`model`** load `capital_project_selection_120` — 120 projects, 4 objectives
   (NPV · Cost · Risk · StrategicFit), rich combinatorial constraints (budget + cardinality +
   dependencies + exclusions + group caps).
2. **`solve run`** (NSGA) — the EA explores the combinatorial frontier (~37 plans, <1 s).
   Surface `binding_analysis` (the budget binds).
3. **`explore tradeoffs`** — navigate Risk vs StrategicFit; show the balanced + inflection plans.
4. **`explore certify`** — the hero beat. **Lead with coverage, not the dominance count:**
   - **Coverage** — exact reclaims **~23%** of the trade-off-surface hypervolume the EA missed.
     *This is the robust headline; it never reads zero.*
   - **Invariant** — NSGA dominates **0** exact points → *"exact can only confirm or improve."*
   - **Corner** — exact sharpens the NPV corner: **~626 → ~952**.
   - *(bonus, seed-dependent)* dominance audit: exact strictly beats a couple of EA plans
     (~2/37), with a concrete example. Present as a bonus — it can read 0 on other frontiers;
     **coverage carries the beat.**
5. **`explore sensitivity`** — on this MILP it **degrades gracefully** (`source=frontier_inferred`,
   a clear "integer/MILP has no exact duals → binding_analysis" message, no crash). The bridge to:
6. **switch to `investment_portfolio`** (continuous QP) — the *same* `explore sensitivity` now
   returns **solver-exact shadow prices + reduced costs** (a fast ~1 s live QP solve). That is the
   home of the duals/explainability beat; a MILP structurally can't show it.

## The one honest line
EA explores → exact **certifies** (reclaims coverage + proves the invariant + sharpens the
corner). The win is a **trustworthy, navigable frontier** — *not* "EA beats exact." Lead with
coverage; the dominance count is a bonus when it fires.

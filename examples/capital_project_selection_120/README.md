# Capital Project Selection (120 projects)

Scaled stress instance of [capital_project_selection](../capital_project_selection): **120 projects**, 4 objectives (NPV / Cost / Risk / StrategicFit), under a hard budget + per-category caps + dependencies + exclusions + cardinality. At this scale the exact-MILP frontier (cuOpt, one solve per scalarization) covers materially more of the tradeoff surface than a fixed-resolution metaheuristic — the canonical Frontier x cuOpt pairing showcase.

**Prompt:** "Map the efficient frontier of funding plans across NPV, cost, risk, and strategic fit within the $610M budget, and walk me through a few representative plans."

Files: [problem.json](problem.json) · [scores.json](scores.json)

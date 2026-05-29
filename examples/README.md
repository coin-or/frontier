# Examples

Loadable Frontier problems — combinatorial, multi-objective decisions that need a real solver, not a spreadsheet. Each has a `problem.json` (objectives, approach, constraints, scenarios) + a `scores.json` (options, scores, interaction matrices), and a paste-able prompt in its own README.

| Example | Decision & objectives | Files |
|---|---|---|
| **[Investment portfolio](investment_portfolio/)** | allocate across 30 ETFs — return / volatility *(quadratic covariance)* / yield, with scenarios | [problem.json](investment_portfolio/problem.json) · [scores.json](investment_portfolio/scores.json) |
| **[Marketing channel budget](channel_budget/)** | allocate budget across 22 channels — conversions / reach *(quadratic overlap)* / ROAS / brand, per-platform caps | [problem.json](channel_budget/problem.json) · [scores.json](channel_budget/scores.json) |
| **[Supplier selection](supplier_selection/)** | multi-source across 25 suppliers — cost / reliability / lead time / ESG / *quadratic concentration risk*, per-region caps | [problem.json](supplier_selection/problem.json) · [scores.json](supplier_selection/scores.json) |
| **[Generation capacity planning](capacity_planning/)** | mix 22 generation projects — cost / CO2 / firmness + *quadratic intermittency*, emissions cap | [problem.json](capacity_planning/problem.json) · [scores.json](capacity_planning/scores.json) |
| **[cuOpt portfolio](cuopt_portfolio/)** | the portfolio problem via the opt-in GPU cuOpt backend | [notebook](cuopt_portfolio/cuopt_portfolio_frontier.ipynb) |

See the [main README](../README.md) for setup and [architecture.md](../architecture.md) for technical reference.

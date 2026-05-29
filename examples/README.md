# Examples

Sample problems for Frontier — combinatorial, multi-objective decisions that need a real solver. Each is a loadable `problem.json` (definition) + `scores.json` (options + scores) with a paste-able prompt, one per target problem type.

- **[Portfolio optimization](investment_portfolio/)** — *investment portfolio construction.* 30 ETFs × return / volatility (quadratic covariance) / yield, with scenarios.
- **[Marketing channel budget](channel_budget/)** — *budget / channel allocation.* 22 channels × 4 conflicting goals (conversions, reach, ROAS, brand) with quadratic audience overlap and per-platform caps.
- **[Supplier selection](supplier_selection/)** — *vendor selection.* 25 suppliers × 5 goals (cost, reliability, lead time, ESG, quadratic concentration risk) with per-region caps.
- **[Generation capacity planning](capacity_planning/)** — *infrastructure planning.* 22 generation projects across the energy trilemma (cost, CO2, firmness) with quadratic intermittency risk and an emissions cap.
- **[cuOpt portfolio](cuopt_portfolio/)** — the portfolio problem via the opt-in GPU cuOpt QP backend (notebook).

See the [main README](../README.md) for setup and [architecture.md](../architecture.md) for technical reference.

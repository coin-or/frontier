# Budget allocation

Split a fixed growth budget across 8 initiatives, trading ROI against strategic reach, with no initiative above 35%. Two purely linear objectives over a continuous allocation make this the simplest exact multi-objective LP: a clean end-to-end pass of the Frontier workflow.

- **`problem.json`**: 2 objectives (ROI and Strategic Reach, both maximize), proportional approach, one 35% per-initiative cap.
- **`scores.json`**: the 8 initiatives scored on ROI (%) and reach (0–10).
- **`solutions.json`**: the exploratory NSGA `run` plus the exact-LP `exact_run` overlay (HiGHS), with solver-exact duals per point.

Load with `model load source="budget_allocation"`, then drive the workflow the way a user would — one ask per phase:

> 1. *“How should we split the growth budget across these eight initiatives? Show me the real ROI-versus-reach choices.”*
> 2. *“Keep the balanced split and the ROI-max one. Are these actually optimal?”*
> 3. *“Which of our limits is costing us the most, and which initiative just missed the cut?”*
> 4. *“Write it up for the planning review.”*

## The workflow

1. **Solve** (`solve run`): the optimizer produces the ROI/reach Pareto frontier.
2. **Explore the tradeoffs** (`explore tradeoffs`): the extremes, a balanced plan, and the knees.
3. **Certify and examine** (`solve solver="highs"` → `explore certify` → `explore sensitivity`): the exact LP overlay audits the heuristic frontier and sharpens the ROI corner; the duals at the balanced plan show the Strategic Reach floor pricing at ~4.0 (each point of reach costs ~4% ROI, rising into diminishing returns), Localization as the closest near-miss (reduced cost ~10), and AI Copilot and Self-Serve Onboarding pinned at the 35% cap.
4. **Decide** (`explore curate`): pin a few plans and commit on the tradeoffs.

A small near-miss says "improve the option"; a binding cap says "lift your own limit." For the richer product-mix LP see [`production_mix`](../production_mix/); for the mean-variance QP, [`investment_portfolio`](../investment_portfolio/); for binary selection with no duals, [`capital_project_selection_120`](../capital_project_selection_120/).

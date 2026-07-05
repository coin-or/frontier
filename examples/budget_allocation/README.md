# Budget allocation

**The decision.** Split a fixed growth budget across 8 initiatives, trading ROI against strategic reach, with no initiative above 35%.

**Why Frontier.** Two purely linear objectives over a continuous allocation make this the simplest exact multi-objective LP: a clean end-to-end pass of the Frontier workflow.

**What ships here** — the raw inputs (step 1), the canonical model they frame into, and pre-solved results:

- **`data.csv`**: the raw inputs a decision owner would actually have — everything step 1 pastes.
- **`problem.json`**: 2 objectives (ROI and Strategic Reach, both maximize), proportional approach, one 35% per-initiative cap.
- **`scores.json`**: the 8 initiatives scored on ROI (%) and reach (0–10).
- **`solutions.json`**: the exploratory NSGA `run` plus the exact-LP `exact_run` overlay (HiGHS), with solver-exact duals per point.

## Step 1 — the ask

Paste this, together with `data.csv`, into a fresh session:

> We're setting next year's growth budget and I want help splitting it across eight
> candidate initiatives (`data.csv`): each is rated on ROI (%) and strategic reach (0–10).
>
> The decision is what percent of the budget each initiative gets — shares total 100%,
> and an initiative can get nothing. We want the highest blended ROI and the most
> strategic reach; both read as the allocation-weighted average of the ratings.
>
> One hard rule: no single initiative may take more than 35% of the budget.

Framing that input (`model create` + `model update`) lands on exactly this problem — the ask plus the data reconstruct `problem.json` and `scores.json` verbatim (guarded by `tests/test_upstream_kits.py`). `model load source="budget_allocation"` is the shortcut: it skips framing and restores the pre-solved runs too.

## The runbook

1. *“How should we split the growth budget across these eight initiatives? Show me the real ROI-versus-reach choices.”*
   `solve run` → `explore tradeoffs`: the ROI/reach frontier — extremes, a balanced plan, and the knees.
2. *“Keep the balanced split and the ROI-max one. Are these actually optimal?”*
   `explore curate` per pick → `solve solver="highs"` → `explore certify`: the exact LP overlay audits the heuristic frontier and sharpens the ROI corner.
3. *“Which of our limits is costing us the most, and which initiative just missed the cut?”*
   `explore sensitivity`: solver-exact duals — the Strategic Reach floor pricing at ~4.0 (each point of reach costs ~4% ROI, rising into diminishing returns), Localization the closest near-miss (reduced cost ~10), AI Copilot and Self-Serve Onboarding pinned at the 35% cap. (Values as read at the balanced anchor of the shipped exact overlay — duals are anchor-specific, so expect them to shift at another frontier point or after a re-solve.)
4. *“Write it up for the planning review.”*
   `explore curated format="markdown"`: the handoff table.

A small near-miss says "improve the option"; a binding cap says "lift your own limit." For the richer product-mix LP see [`production_mix`](../production_mix/); for the mean-variance QP, [`investment_portfolio`](../investment_portfolio/); for binary selection with no duals, [`capital_project_selection_300`](../capital_project_selection_300/).

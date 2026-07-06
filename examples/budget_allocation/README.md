# Budget allocation

**The decision.** Split a fixed growth budget across 24 candidate initiatives from five departments, trading projected ROI against strategic reach and time-to-impact — no initiative above 20% of the budget, at most 3 funded per department, blended time-to-impact within 9 months, and a downturn scenario that haircuts the discretionary growth bets.

**Why Frontier.** Three conflicting linear objectives over a continuous 24-way split, with department caps and a time bound coupling every share to every other: a ranking hands you one corner and breaches a cap on the way (sort-by-ROI puts 4 picks in Product against a cap of 3; repaired, it lands on the ROI-max corner blind to the rest of the frontier). Purely linear objectives keep it an exact multi-objective LP — the solver returns duals: which initiative is a near-miss, and what each limit costs.

**What ships here** — the raw inputs (step 1), the canonical model they frame into, and pre-solved results:

- **`data.csv`**: the raw inputs a decision owner would actually have — everything step 1 pastes.
- **`problem.json`**: 3 objectives (ROI and Strategic Reach maximize, TimeToImpact minimize), proportional approach, 20% per-initiative cap, 5 department group caps, a 9-month blended time bound, and the downturn scenario.
- **`scores.json`**: the 24 initiatives scored on ROI (%), reach (0–10), and time-to-impact (months).
- **`solutions.json`**: the exploratory NSGA `run`, the per-scenario `scenario_run`, and the exact-LP `exact_run` overlay (HiGHS) with solver-exact duals per point.

## The runbook

1. **Frame it from the raw inputs** — paste this ask, together with `data.csv`, into a fresh session:

   > We're setting next year's growth budget and I want help splitting it across 24
   > candidate initiatives from five departments (`data.csv`): each is rated on ROI (%),
   > strategic reach (0–10), and time-to-impact (months).
   >
   > The decision is what percent of the budget each initiative gets — shares total 100%,
   > and an initiative can get nothing. We want the highest blended ROI, the most strategic
   > reach, and the shortest time-to-impact; all three read as the allocation-weighted
   > average of the ratings.
   >
   > Hard rules: no single initiative may take more than 20% of the budget; fund at most 3
   > initiatives per department; and the blended time-to-impact must come in at or under
   > 9 months.
   >
   > Also model a downturn scenario: the discretionary growth bets take the ROI haircut in
   > the `roi_under_downturn` column; everything else holds.

   Framing that input (`model create` + `model update`) lands on exactly this problem — the ask plus the data reconstruct `problem.json` and `scores.json` verbatim (guarded by `tests/test_upstream_kits.py`). `model load source="budget_allocation"` is the shortcut: it skips framing and restores the pre-solved runs too.

2. *“How should we split the budget? Show me the real ROI-versus-reach-versus-speed choices.”*
   `solve run` → `explore tradeoffs`: the three-objective frontier — extremes, a balanced plan, and the knees. The balanced plan lands near ROI 22.8 / reach 6.8 / 5.9 months; the ROI-max corner (26.2 / 5.6 / 8.8 months) is what a repaired sort-by-ROI would pick — the frontier prices what that corner gives up: ~21% of the reach and ~3 months of speed for ~3.4 points of ROI.
3. *“Which splits survive a downturn?”*
   `solve run_scenarios` → `explore scenario_results`: the frontier re-solved under the haircut — which picks hold their share when Marketplace drops to 19% ROI and the paid-growth bets fade, and which corner was riding the discretionary spend.
4. *“Keep the balanced split and the ROI-max one. Are these actually optimal?”*
   `explore curate` per pick → `solve solver="highs"` → `explore certify`: the exact LP overlay audits the heuristic frontier point-for-point — dominance audit, coverage, the NSGA-never-dominates invariant — and sharpens the corners the heuristic left slack.
5. *“Which of our limits is costing us the most, and which initiative just missed the cut?”*
   `explore sensitivity`: solver-exact duals — the Strategic Reach floor pricing at ~8.25 (each extra point of blended reach costs ~8.25 points of ROI at the margin), Brand Refresh the closest near-miss (reduced cost ~0.5), and Self-Serve Onboarding, AI Copilot, Customer Education, and Lifecycle Campaigns pinned at the 20% cap — the cap binds; they'd take more if allowed. (Values as read at the balanced anchor of the shipped exact overlay — duals are anchor-specific marginal rates, so expect them to shift at another frontier point or after a re-solve; confirm a big move by re-solving with the changed limit.)
6. *“Write it up for the planning review.”*
   `explore curated format="markdown"`: the handoff table.

A small near-miss says “improve the option”; a binding cap says “lift your own limit.” For the product-mix LP with structural exclusions see [`production_mix`](../production_mix/); for the mean-variance QP, [`investment_portfolio`](../investment_portfolio/); for binary selection with audit guarantees, [`capital_project_selection_300`](../capital_project_selection_300/); for the participatory-budget LP where the duals price equity mandates, [`community_program_funding`](../community_program_funding/).

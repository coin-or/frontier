# Production mix allocation

**The decision.** Allocate a fixed plant capacity across 10 products on three lines, trading margin, throughput, and sustainability, with no product above 30% of capacity and at most two SKUs per line, stress-tested across two scenarios.

**Why Frontier.** Three purely linear objectives over a continuous allocation make this an exact multi-objective LP: a full pass of the Frontier workflow, from the frontier through scenario stress tests to the exact certify and solver duals.

**What ships here** — the raw inputs (step 1), the canonical model they frame into, and pre-solved results:

- **`data.csv`**: the raw inputs a decision owner would actually have — everything step 1 pastes.
- **`problem.json`**: 3 objectives (all maximize), proportional approach, a 30% per-product cap, three per-line `group_limit`s (≤2 active SKUs each), and two scenarios (`input_cost_spike`, `capacity_crunch`).
- **`scores.json`**: the 10 products scored on margin ($/unit), throughput (k units/wk), and sustainability (0–10).
- **`solutions.json`**: the exploratory NSGA `run`, the exact-LP `exact_run` overlay (HiGHS) with solver-exact duals per point, and the per-scenario `scenario_run`.

## The runbook

1. **Frame it from the raw inputs** — paste this ask, together with `data.csv`, into a fresh session:

   > We're re-planning how to load the plant across ten products (`data.csv`): per-unit
   > margin ($), throughput (k units/week), and a sustainability rating, plus which of our
   > three lines each product runs on. For the four commodity SKUs the sheet also carries
   > the re-priced margin if the input-cost spike we're worried about lands.
   >
   > The decision is what percent of plant capacity each product gets — shares total 100%.
   > We want the best blended margin, throughput, and sustainability (allocation-weighted
   > averages).
   >
   > Hard rules:
   > - No product above 30% of capacity.
   > - Changeovers limit each line to at most 2 active SKUs.
   >
   > Two futures to stress-test:
   > - **Input cost spike** — the four commodity SKUs re-price to the margins in the
   >   `margin_under_input_cost_spike` column; everything else unchanged.
   > - **Capacity crunch** — a demand surge tightens the per-product cap from 30% to 25%;
   >   every other rule stays as-is.

   Framing that input (`model create` + `model update`) lands on exactly this problem — the ask plus the data reconstruct `problem.json` and `scores.json` verbatim (guarded by `tests/test_upstream_kits.py`). `model load source="production_mix"` is the shortcut: it skips framing and restores the pre-solved runs too.

2. *“How should we load the plant across these ten products? Show me the margin/throughput/sustainability tradeoffs — and how they hold up under the stress scenarios.”*
   `solve run` + `solve run_scenarios` → `explore tradeoffs`: the frontier plus `input_cost_spike` and `capacity_crunch` scenarios — the knees where the exchange rate jumps, and how the achievable frontier *shrinks* under the crunch.
3. *“Keep the balanced plan and the max-margin one. Are these actually optimal?”*
   `explore curate` per pick → `solve solver="highs"` → `explore certify`: the exact LP overlay audits the heuristic frontier (all three per-line limits bind).
4. *“Where should we invest next — what's binding, and which product just missed the cut?”*
   `explore sensitivity`: the Throughput floor as the binding lever (~0.5 margin per unit, rising into diminishing returns), Gear Sets the closest near-miss, Aerospace / Optics / Fasteners pinned at the 30% cap, and the line-limited products filtered as structural exclusions. (Values as read at the balanced anchor of the shipped exact overlay — duals are anchor-specific, so expect them to shift at another frontier point or after a re-solve.)
5. *“Write the loading plan up for the ops review.”*
   `explore curated format="markdown"`: the handoff table.

The interior, near-zero-reduced-cost SKU (here Pump Assemblies) is the swing that sets the marginal price; Frontier infers it from the duals today, and an exposed solver basis status would name it directly. The exact LP path runs on either backend (HiGHS on CPU, cuOpt on GPU), so the same shadow prices and reduced costs come back on GPU. For the two-objective LP see [`budget_allocation`](../budget_allocation/); for the mean-variance QP, [`investment_portfolio`](../investment_portfolio/).

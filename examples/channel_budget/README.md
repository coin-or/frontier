# Marketing channel budget

Loadable Frontier example — split a marketing budget across 5 channels to balance conversions across 3 campaign goals (Brand Awareness, Product Launch, Seasonal Sale). Channels specialize, so the mix is a real tradeoff, not one "best."

- **`problem.json`** — definition: 3 objectives (one per campaign, maximize), proportional approach, ≤40% per channel, an `email_sunset` scenario.
- **`scores.json`** — the 5 channels and the 5×3 conversion-rate score matrix.

Load both into Frontier (`model create` → `model update` → `solve run` → `explore`), or paste this to an agent connected to Frontier:

> Allocate my marketing budget across the 5 channels in scores.json to balance conversions across three campaigns — Brand Awareness, Product Launch, Seasonal Sale. No channel over 40%. Show the tradeoff frontier — which mixes favor which campaigns — and how it shifts if we retire Email. Not one "best."

# Supplier selection

Loadable Frontier example — split orders across 4 suppliers to balance blended unit cost against reliability. The cheapest supplier is the least reliable, so it's a genuine tradeoff, not one "best."

- **`problem.json`** — definition: 2 objectives (Cost ↓, Reliability ↑), proportional approach, ≤45% per supplier (diversification), a `supplierC_disruption` scenario.
- **`scores.json`** — the 4 suppliers with blended cost ($/unit) and reliability scores.

Load both into Frontier (`model create` → `model update` → `solve run` → `explore`), or paste this to an agent connected to Frontier:

> Allocate orders across the 4 suppliers in scores.json to minimize blended unit cost and maximize reliability. No supplier over 45%. Show the cost–reliability frontier and how it shifts if SupplierC (the cheapest) is disrupted. Not one "best."

# Product Fix Triage — Frontier Multi-Objective Optimizer

Working triage of fixes identified during demo. Issues are generalized to apply across any optimization problem domain.

---

## P0 — Correctness / Misleading Output

| # | Fix | Why It Matters | Suggested Approach | Effort |
|---|-----|---------------|-------------------|--------|
| 1 | **Robustness metric is too broad** — counts any appearance in any Pareto solution as "robust" | With large Pareto fronts, nearly every option appears somewhere. Metric becomes meaningless and misleads users about what is truly stable. | Weight by appearance frequency, or compute robustness only over a curated/representative subset (e.g. knee-point solutions). Expose frequency threshold as a parameter. | M |
| 2 | **Expected values computed from frontier extremes, not representative solutions** | Reporting max-of-objective across all Pareto solutions as "expected value" misrepresents the distribution and inflates apparent performance. | Compute expected values over a balanced or user-curated solution set, not over all frontier extremes. Label clearly as "across balanced solutions" vs "frontier range". | S |
| 3 | **No warning when an objective is non-additive but scored additively** | Weighted-average scoring silently mismodels quantities like variance/volatility that are not linear in the portfolio weights. Applies to any objective that is subadditive, superadditive, or otherwise non-linear. | At solve time, detect when a known non-additive objective type is used with an additive scorer and emit a structured warning in the result. Document the assumption violation. | M |

---

## P1 — Usability / Agent Consumption

| # | Fix | Why It Matters | Suggested Approach | Effort |
|---|-----|---------------|-------------------|--------|
| 4 | **Marginal analysis output too large** — current output is ~100K+ characters per scenario | LLM context windows and human attention have hard limits. Unusable output means the feature is effectively unavailable at scale. | Default to summary-first format: headline metrics + knee-point solutions only. Provide a `verbose=true` flag for full detail. | M |
| 5 | **Solve overflow — engine generates more solutions than requested** | Unpredictable output size breaks downstream tooling and expectations. Users lose control over compute cost and response size. | Enforce requested count as a hard cap (post-prune to N best-spread solutions), or clearly document and surface why more were generated (e.g. "requested 100, generated 329 due to enumeration"). | S |
| 6 | **No direct solution comparison action** | Without a compare primitive, agents must fetch each solution individually and diff manually, which is brittle and expensive in tokens. | Add `explore compare <id_a> <id_b>` action that returns a side-by-side diff of objectives, constraints, and key decision variables. | S |

---

## P2 — Stability / Experience

| # | Fix | Why It Matters | Suggested Approach | Effort |
|---|-----|---------------|-------------------|--------|
| 7 | **Solution content signatures drift across sessions** | If signatures change after curation or re-exploration, users can't reliably reference or track solutions across interactions. Breaks any workflow that pins solutions by ID. | Make signatures deterministic and stable: hash over canonical decision-variable values, not over internal state or ordering. Verify stability under re-explore. | M |
| 8 | **Balanced solution selection not always intuitive** | Centroid-distance picks a single "balanced" point that may not match user intent, especially in asymmetric Pareto fronts. | Return 2-3 balanced candidates with different balance profiles (e.g. centroid, knee-point, equal-weight tradeoff). Let user select or tune balance criteria. | M |

---

## Notes

- P0 fixes affect correctness of reported results and should block any production use or demo.
- P1 fixes affect whether the tool is usable at all for LLM-driven workflows.
- P2 fixes affect reliability and UX polish.
- All fixes should be implemented and tested against a generic optimizer problem (not only the ETF demo case) to avoid overfitting the fix to that domain.

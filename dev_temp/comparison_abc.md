# A/B/C Comparison: ETF Portfolio Optimization

**Date:** 2026-04-12
**Problem:** 25-ETF portfolio allocation across 3 objectives (return, volatility, yield)
**Constraints:** Vol cap 20%, max 2 sector ETFs, max 2 alternatives, 4-12 holdings

---

## Method Summary

| | A: LLM Only | B: LLM + Pyomo Solver | C: Frontier |
|---|---|---|---|
| **What it is** | Claude reasons through the data manually | Claude writes a Pyomo MILP script, runs epsilon-constraint sweeps | Frontier MCP tools: model → solve → explore → curate |
| **Setup effort** | None | ~220 lines Python + install Pyomo + GLPK | 5 tool calls (create, update scores, add constraints, solve, explore) |
| **Time to result** | Instant (LLM inference) | ~1 sec solve + manual script dev time | ~2 sec solve + interactive exploration |
| **Solutions found** | 4 (hand-picked) | 41 Pareto-optimal | 166 Pareto-optimal |
| **Frontier coverage** | 4 guessed points | Sparse grid (41 points, epsilon grid gaps) | Dense coverage (166 points, evolutionary search) |

---

## Head-to-Head: Growth Portfolio

| Metric | A: LLM Only | B: Pyomo | C: Frontier |
|--------|-------------|----------|-------------|
| **Return** | 14.34% | 20.64% | 19.67% |
| **Volatility** | 16.65% | 19.96% | 18.78% |
| **Yield** | 1.05% | 0.90% | 0.86% |
| **Holdings** | 6 | 4 | 6 |
| **Top positions** | VOO 30%, GLD 25%, VUG 15% | GLD 61%, VDE 37% | GLD 68%, VDE 28% |

**Verdict:** LLM left 5.3pp of return on the table by diversifying into lower-return equities (VOO, VUG) instead of concentrating in the dominant return assets (GLD, VDE). Both optimizers found the GLD+VDE combination; the LLM's intuition toward "traditional diversification" actually hurt performance under a linear-avg objective model.

---

## Head-to-Head: Balanced Portfolio

| Metric | A: LLM Only | B: Pyomo | C: Frontier |
|--------|-------------|----------|-------------|
| **Return** | 9.02% | 11.23% | 8.61% |
| **Volatility** | 12.61% | 11.13% | 10.42% |
| **Yield** | 2.72% | 3.28% | 4.55% |
| **Holdings** | 6 | 4 | 5 |
| **Top positions** | VOO 25%, BND 20%, GLD 15%, VTV 15% | GLD 47%, HYG 43% | HYG 67%, GLD 29% |

**Verdict:** All three found different "balanced" points — each is Pareto-optimal at its own tradeoff. Frontier found the best yield (4.55% vs 2.72%) at lower vol (10.4% vs 12.6%) by leaning into HYG. The LLM's portfolio has higher vol AND lower yield than Frontier's — it's likely **dominated** (Frontier's is strictly better on 2 of 3 objectives).

---

## Head-to-Head: Income Portfolio

| Metric | A: LLM Only | B: Pyomo | C: Frontier |
|--------|-------------|----------|-------------|
| **Return** | 4.08% | 3.76% | 4.16% |
| **Volatility** | 9.05% | 7.91% | 8.35% |
| **Yield** | 4.59% | 6.67% | 6.44% |
| **Holdings** | 7 | 4 | 4 |
| **Top positions** | HYG 20%, SCHD 15%, VYM 15%, BND 15% | HYG 97% | HYG 96% |

**Verdict:** LLM's income portfolio is **dominated** — both optimizers find ~6.4-6.7% yield vs LLM's 4.59%, at similar or better return. The LLM "diversified" across 7 ETFs, diluting the yield leader (HYG at 6.7%). The optimizers correctly identified that HYG concentration maximizes income under the linear model.

---

## Head-to-Head: Safety Portfolio

| Metric | A: LLM Only | B: Pyomo | C: Frontier |
|--------|-------------|----------|-------------|
| **Return** | 2.32% | 1.79% | 2.15% |
| **Volatility** | 5.90% | 2.33% | 3.33% |
| **Yield** | 4.29% | 3.78% | 3.76% |
| **Holdings** | 6 | 4 | 6 |
| **Top positions** | VGSH 35%, BND 20%, TIP 15% | VGSH 97% | VGSH 88% |

**Verdict:** LLM's safety portfolio has nearly 2x the volatility of the optimizers' solutions. By only allocating 35% to VGSH (the lowest-vol asset at 2.2%), the LLM missed the opportunity to push vol much lower. The optimizers concentrated in VGSH to minimize vol. However, the LLM's portfolio has a marginally higher yield tradeoff (4.29% vs ~3.78%).

---

## Overall Comparison

### Result Quality

| Dimension | A: LLM Only | B: Pyomo | C: Frontier |
|-----------|-------------|----------|-------------|
| **Pareto-optimal?** | Likely dominated on 2+ of 4 strategies | All 41 solutions verified non-dominated | All 166 solutions non-dominated |
| **Frontier coverage** | 4 guessed points | 41 points (sparse grid) | 166 points (dense evolutionary) |
| **Extreme discovery** | Missed true extremes by 5-6pp | Found true extremes | Found true extremes |
| **Constraint satisfaction** | Manual checking | Provably exact (MILP) | Validated post-solve |

### Interpretability & UX

| Dimension | A: LLM Only | B: Pyomo | C: Frontier |
|-----------|-------------|----------|-------------|
| **Tradeoff quantification** | None — 4 isolated points | Manual post-processing needed | Built-in: correlations, marginal rates, knee detection |
| **Strategy curation** | LLM narrates reasoning | User manually labels solutions | Named curation with content signatures that survive re-runs |
| **"What if" exploration** | Ask LLM again (loses context) | Re-run script with new epsilon bounds | `explore compare`, `explore marginal_analysis` — interactive |
| **Presentation guidance** | None | None | Solution interpreter skill auto-injects (never say "best", quantify tradeoffs) |
| **Setup for non-engineers** | Works in chat | Requires Python, Pyomo, GLPK, coding ability | 5 natural-language tool calls |

### Effort

| Dimension | A: LLM Only | B: Pyomo | C: Frontier |
|-----------|-------------|----------|-------------|
| **User effort** | Describe problem in chat | Write ~220-line script, install solver, design epsilon grid | Describe problem in chat |
| **Iteration cost** | Re-explain from scratch | Edit script, re-run, re-filter, re-curate | `model update` + `solve run` (preserves curated solutions) |
| **Domain expertise needed** | Low | High (optimization modeling, solver selection, Pareto theory) | Low (skill guidance coaches the user) |

---

## Key Takeaways

### 1. LLM-only solutions are reasonable but not optimal
The LLM produces portfolios that satisfy constraints and roughly align with stated goals. But it leaves significant value on the table — **5.3pp of return** in the growth case, **1.9pp of yield** in the income case. Its intuition toward traditional diversification actively hurts under a linear-average objective model.

### 2. Optimizers find the same dominant ETFs
Both Pyomo and Frontier converge on the same core holdings: GLD+VDE for growth, HYG for income, VGSH for safety. This validates that the underlying data and objectives are well-defined — the optimizers agree on the structure of the Pareto frontier.

### 3. Frontier's advantage is density + interpretability
Pyomo found 41 Pareto solutions; Frontier found 166 (4x more). More importantly, Frontier provides the exploration layer (tradeoff correlations, marginal analysis with knee detection at solution 31, named curation) that transforms raw optimization output into a decision-making tool. Pyomo gives you a spreadsheet of allocation vectors.

### 4. The linear volatility model creates concentration
All three methods produce concentrated portfolios because weighted-average volatility doesn't reward diversification. A covariance-based (quadratic) volatility model would produce more diversified portfolios — an area where Frontier could add future value by supporting quadratic objectives.

### 5. Frontier = optimizer accessibility
Frontier's contribution isn't a better optimizer — it's making optimization accessible through natural-language tool calls, auto-injected guidance, and built-in exploration. The same optimization that requires 220 lines of Python and domain expertise becomes 5 tool calls with coaching.

# A/B/C Comparison: 30-ETF Portfolio Optimization

**Date:** 2026-04-13
**Problem:** 30-ETF portfolio, 3 objectives (return ↑, volatility ↓, yield ↑), 4 constraints
**Data:** `dev_temp/etf_cache/etf_30_consolidated.json` (yfinance, 5yr 2021-2026)
**Plot:** `dev_temp/pareto_comparison.png`

---

## 1. Method Summary

| | A: Frontier (MCP tools) | B: Agent + pymoo | C: LLM Only |
|---|---|---|---|
| **Setup** | 5 tool calls (create, scores, constraints, solve, explore) | 267-line Python script with custom repair operator | 0 lines — pure reasoning |
| **Solver** | NSGA-II (built-in, auto-configured) | NSGA-III (manual config: pop=200, gen=500, seed=42) | Human heuristic search |
| **Solve time** | ~2 sec | 8.7 sec | Instant (inference) |
| **Pareto solutions** | **182** | **45** | **4** (hand-picked) |
| **Skill guidance** | ✅ Auto-injected at 3 phases | ❌ N/A | ❌ N/A |
| **Exploration tools** | tradeoffs, compare, marginal_analysis, curate | Manual post-processing | None |

---

## 2. Objective Ranges

| Objective | Frontier | pymoo | LLM |
|-----------|----------|-------|-----|
| Return (max) | 2.31 – **19.01** | 3.75 – 14.17 | 1.56 – 18.58 |
| Volatility (min) | **3.06** – 18.76 | 9.23 – 17.43 | 4.52 – 19.98 |
| Yield (max) | 0.26 – **5.50** | 1.78 – 4.53 | 0.90 – 5.06 |

**Frontier found the widest range on every objective.** pymoo's frontier is compressed — it never reached the true extremes (max return 14.17% vs Frontier's 19.01%, min vol 9.23% vs Frontier's 3.06%). The LLM's Growth strategy gets close to Frontier's return extreme but its Safety/Income strategies trail significantly.

---

## 3. Curated Strategies Head-to-Head

### Growth

| | Frontier | pymoo | LLM |
|---|---|---|---|
| **Return** | **19.01%** | 14.17% | 18.58% |
| **Volatility** | 17.56% | 16.87% | **19.98%** |
| **Yield** | 0.70% | **1.78%** | 0.90% |
| **Core holdings** | GLD 76%, VDE 18% | GLD 23%, VDE 12%, GSG 11% | GLD 35%, VDE 30% |
| **Holdings** | 8 | 12 | 5 |

**Gap:** Frontier finds 4.8pp more return than pymoo. pymoo's repair operator spreads allocations too thin (12 holdings at the minimum-enforced 1%+), diluting the growth signal. LLM gets close to Frontier but rides the vol constraint ceiling at 19.98%.

### Balanced

| | Frontier | pymoo | LLM |
|---|---|---|---|
| **Return** | 9.89% | 9.40% | **9.82%** |
| **Volatility** | **11.07%** | 13.30% | 12.90% |
| **Yield** | **3.52%** | 3.33% | 2.72% |
| **Core holdings** | HYG 56%, GLD 36% | VDE 13%, DBA 12%, VGSH 11% | VOO 25%, GLD 15%, SCHD 15% |

**Gap:** Frontier's balanced is strictly better than LLM's — same return, 1.8pp less vol, 0.8pp more yield. LLM's balanced portfolio is **dominated** by Frontier's.

### Income

| | Frontier | pymoo | LLM |
|---|---|---|---|
| **Return** | **4.27%** | 4.12% | 2.81% |
| **Volatility** | **8.46%** | 10.80% | 10.78% |
| **Yield** | **5.50%** | 4.53% | 5.06% |
| **Core holdings** | HYG 86% | HYG 28%, EMB 12% | HYG 40%, EMB 20%, VNQI 15% |

**Gap:** Frontier dominates both others — higher return, lower vol, AND higher yield. LLM's income portfolio uses VNQI (-0.58% return, 18.22% vol) which drags performance.

### Safety

| | Frontier | pymoo | LLM |
|---|---|---|---|
| **Return** | 2.31% | **4.93%** | 1.56% |
| **Volatility** | **3.06%** | 9.23% | 4.52% |
| **Yield** | 3.91% | 3.70% | **4.04%** |
| **Core holdings** | VGSH 94% | VGSH 21%, HYG 13% | VGSH 50%, BND 20%, TIP 20% |

**Gap:** pymoo's "Safety" has 3x more vol than Frontier's — it never found the VGSH-concentrated low-vol region. Frontier finds 3.06% vol by concentrating in VGSH. LLM gets closer (4.52%) but doesn't push the concentration far enough.

---

## 4. Issues & Observations

### Frontier
- ✅ Skill guidance auto-injected at all 3 phase transitions (data_collection → optimization_strategy → solution_interpreter)
- ✅ String options accepted on create
- ✅ Objectives/options persisted on create
- ⚠️ Solve response (182 solutions × 30 allocations) exceeds MCP token limit, saved to temp file — agent can't see raw solutions directly, must use explore tools
- ✅ Explore tools (tradeoffs, compare, curate) work within MCP limits and provide actionable summaries

### pymoo
- ⚠️ **Compressed frontier** — 45 solutions vs Frontier's 182, with narrower objective ranges on all 3 axes
- ⚠️ **Repair operator complexity** — 80+ lines of the 267-line script is the repair operator; this is the main engineering burden
- ⚠️ **Over-diversification** — all 4 curated strategies have exactly 12 holdings (the max). The repair operator's normalization logic distributes weight too broadly, preventing the concentrated allocations that are optimal under linear-avg objectives
- ⚠️ **Missing extremes** — never found the VGSH-concentrated safety region (min vol 9.23% vs Frontier's 3.06%) or the GLD-concentrated growth region (max return 14.17% vs Frontier's 19.01%)
- Root cause: the repair operator clips and renormalizes allocations in a way that prevents corner solutions

### LLM Only
- ⚠️ **Balanced portfolio is dominated** by Frontier's balanced (same return, worse vol and yield)
- ⚠️ **Income portfolio uses a yield trap** — VNQI at 15% has -0.58% return and 18.22% vol
- ⚠️ **Safety doesn't push concentration** — 50% VGSH leaves room for improvement; an optimizer finds 94% is better
- ✅ **Growth is competitive** — 18.58% return is close to Frontier's 19.01%, achieved by systematically pushing the vol constraint to ceiling (19.98%)
- ✅ **Honest self-assessment** — the LLM correctly identified which of its portfolios might be dominated

---

## 5. Solution Interpretation Responses

### A: Frontier's Interpretation

> Here is how the tradeoff space breaks down across these four strategies.
>
> **Growth** pushes for maximum capital appreciation at 19.0% annualized return, driven by a 76% allocation to gold (GLD) and 18% to energy (VDE) — two of the strongest performers over the past five years. The cost is clear: volatility climbs to 17.6%, and dividend yield drops to just 0.7%. This portfolio is a concentrated bet on commodity-linked returns.
>
> **Safety** sits at the opposite extreme. With 94% in short-term treasuries (VGSH), volatility compresses to just 3.1% — but annualized return falls to 2.3%. Interestingly, the yield stays at 3.9% because VGSH itself pays a meaningful coupon. This is near-cash stability.
>
> **Income** maximizes yield at 5.5% by concentrating 86% in high-yield bonds (HYG). Return drops to 4.3% and volatility sits at 8.5% — a moderate risk profile. This strategy accepts lower growth in exchange for the highest cash flow.
>
> **Balanced** splits the difference: 56% HYG and 36% GLD produce 9.9% return at 11.1% volatility with 3.5% yield. No single objective dominates — all three are in the middle of their respective ranges.
>
> ### Tradeoff Quantification
> - Moving from **Safety to Balanced**: gaining 7.6pp of return costs 8.0pp of additional volatility — roughly 1:1.
> - Moving from **Balanced to Growth**: gaining another 9.1pp of return costs 6.5pp of volatility but sacrifices 2.8pp of yield.
> - Moving from **Balanced to Income**: gaining 2.0pp of yield costs 5.6pp of return but actually reduces volatility by 2.6pp — income and stability go together here.
>
> Each of these strategies is optimal at its particular tradeoff — none dominates another. The question is which tradeoff you are willing to make. There are also 178 other Pareto-optimal portfolios between these anchors — if you lean toward one direction but want to moderate it, we can explore the gradations.

### B: pymoo's Interpretation

> The optimizer searched 100,000 candidate portfolios across 500 generations and converged on 45 distinct Pareto-optimal allocations. No single portfolio dominates all three objectives simultaneously — every improvement on one metric comes at a measurable cost elsewhere.
>
> **The extremes frame the decision space.** Growth delivers 14.17% annualized return but accepts 16.87% volatility and produces only 1.78% yield. Safety compresses volatility to 9.23% (nearly half) but return drops to 4.93%. Income pushes yield to 4.53% but return falls to 4.12%.
>
> **The cost of chasing return.** Moving from Safety to Growth buys 9.24pp of additional return. The price is 7.64pp of additional volatility and 1.92pp of lost yield. Each additional point of return costs roughly 0.83 points of volatility.
>
> **Income and safety are neighbors, not twins.** Safety (4.93% return, 9.23% vol, 3.70% yield) and Income (4.12% return, 10.80% vol, 4.53% yield) have similar return profiles, but Income accepts 1.57pp more volatility to capture 0.83pp more yield.
>
> **Structural patterns.** Gold (GLD) and short-term Treasuries (VGSH) appear in all four strategies, playing opposite roles: GLD drives return, VGSH dampens volatility. High-yield bonds (HYG) appear everywhere because they uniquely combine moderate return with high yield at contained volatility.
>
> Which of these profiles aligns with what you are trying to accomplish?

### C: LLM's Interpretation

> Here are four portfolio strategies built from the same 30-ETF universe, each pushing a different objective as far as the constraints allow. The point is not to pick one — it is to see what you are trading away for what you are getting.
>
> **Growth (18.58% return, 0.90% yield, 19.98% vol)** concentrates 65% of capital in gold and energy and rides the volatility constraint right to its 20% ceiling. This portfolio earned the highest returns over the past 5 years, but pays almost nothing in dividends and would have delivered stomach-churning drawdowns.
>
> **Safety (1.56% return, 4.04% yield, 4.52% vol)** is the mirror image: half the portfolio in short-term treasuries. Volatility drops under 5%, but returns barely keep pace with inflation. The 4% yield is the main source of real return.
>
> **The tradeoff between return and yield is the sharpest tension.** Moving from Growth to Income, you gain 4.16pp of dividend yield but surrender 15.77pp of total return.
>
> **The balanced portfolio is a compromise, not an optimization.** Balanced (9.82% return, 2.72% yield, 12.90% vol) sits in the middle on every metric without excelling at any.
>
> The question is not which portfolio is correct. It is which tradeoff you can live with for the next 5-10 years.

---

## 6. Interpretation Quality Assessment

| Criterion | Frontier | pymoo | LLM |
|-----------|---------|-------|-----|
| Never says "best" | ✅ | ✅ | ✅ |
| Presents extremes first | ✅ | ✅ | ✅ |
| Quantifies tradeoffs | ✅ (4 specific pp comparisons) | ✅ (3 specific pp comparisons) | ✅ (2 comparisons) |
| Asks user preference | ✅ "which tradeoff you are willing to make" | ✅ "which of these profiles" | ✅ "which tradeoff you can live with" |
| Mentions exploration options | ✅ "178 other portfolios...we can explore the gradations" | ❌ | ❌ |
| Structural insight | ✅ HYG universal, return-yield tension | ✅ GLD/VGSH roles, DBA diversifier | ✅ Commodity supercycle caveat |
| Acknowledges limitations | Implicit (linear vol) | ✅ Repair operator, stochastic | ✅ Extensive limitations section |

**All three agents produced good interpretation text** following the "never say best" principle. Frontier's is the most actionable because it invites continued exploration ("178 other portfolios between these anchors"). The LLM's is the most honest about limitations. pymoo's interpretation is solid but has no path to deeper exploration.

---

## 7. Summary

**Frontier found the richest, widest Pareto front** (182 solutions spanning the full objective space) with zero code and auto-injected skill guidance. pymoo found a compressed frontier (45 solutions, narrower ranges) due to its repair operator over-diversifying allocations. The LLM produced 4 reasonable portfolios through reasoning, one of which (Balanced) is demonstrably dominated by Frontier's balanced solution.

The plot (`pareto_comparison.png`) shows this visually: Frontier's blue cloud spans the full return-vol-yield space, pymoo's green diamonds cluster in the interior, and the LLM's red stars land on or near the frontier in some cases (Growth) but inside it in others (Balanced, Income).

See individual run docs for full details:
- `run2_frontier.md` — Frontier execution log, 182-solution raw data
- `run2_pymoo.md` — pymoo script, 45-solution raw data
- `run2_llm_only.md` — LLM reasoning process, limitations analysis

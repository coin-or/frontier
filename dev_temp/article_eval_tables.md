# Evaluation Tables: Frontier vs Solver vs LLM

Distilled data tables and side-by-side response quotes for article use. All data from identical 30-ETF problem (3 objectives, 4 constraints, same input data).

---

## Table 1: What Each Method Found

| | Frontier | Agent + pymoo | LLM Only |
|---|:---:|:---:|:---:|
| **Pareto solutions** | 182 | 45 | 4 |
| **Custom code written** | 0 lines | 267 lines | 0 lines |
| **Solve time** | ~2s | 8.7s | instant |
| **Return range** | 2.3 – 19.0% | 3.8 – 14.2% | 1.6 – 18.6% |
| **Volatility range** | 3.1 – 18.8% | 9.2 – 17.4% | 4.5 – 20.0% |
| **Yield range** | 0.3 – 5.5% | 1.8 – 4.5% | 0.9 – 5.1% |
| **Widest range (of 3)** | **3 of 3** | 0 of 3 | 0 of 3 |

---

## Table 2: Head-to-Head at Same Return Targets

*"At the same return level, which method needs less volatility?"*

| Target Return | Frontier vol | pymoo vol | LLM vol |
|:---:|:---:|:---:|:---:|
| 4% | **5.4%** | 10.0% | 10.8% |
| 6% | **7.2%** | 13.2% | — |
| 8% | **8.5%** | 14.4% | 12.9% |
| 10% | **9.5%** | 12.4% | 12.9% |
| 12% | **12.3%** | 17.4% | — |
| 14% | **13.3%** | 16.9% | — |
| 18% | **16.8%** | — | 20.0% |

Frontier achieves lower volatility at every return target. The LLM has no solution at 3 of 7 targets. pymoo's gap widens at the extremes.

---

## Table 3: The Dominated Portfolio

*LLM's Balanced vs. Frontier's Balanced — same role, different quality.*

| Objective | Frontier Balanced | LLM Balanced | Winner |
|---|:---:|:---:|:---:|
| Expected Return | 9.89% | 9.82% | Frontier (+0.07pp) |
| Volatility | 11.07% | 12.90% | Frontier (-1.83pp) |
| Dividend Yield | 3.52% | 2.72% | Frontier (+0.80pp) |

Frontier's Balanced is strictly better on all three objectives. The LLM's is **dominated** — a user seeing only the LLM's output would have no way to know a better solution exists.

---

## Table 4: Pitfall Scorecard

| Pitfall | Frontier | Agent + Solver | LLM Only |
|---------|:---:|:---:|:---:|
| Infeasible plans | Impossible by construction | Depends on custom code | Manual verification |
| Stray assumptions | Explicit data entry | Data loaded from file | Judgment calls shipped as decisions |
| Incomplete exploration | 182 solutions, full range | 45 solutions, missed corners | 4 solutions, massive gaps |
| Opaque reasoning | Computed marginal rates | Auditable with custom analysis | Narrative only |

---

## Interpretation Responses: Side-by-Side

### How each method describes the Balanced portfolio

**Frontier:**
> **Balanced** splits the difference: 56% HYG and 36% GLD produce 9.9% return at 11.1% volatility with 3.5% yield. No single objective dominates — all three are in the middle of their respective ranges.

**pymoo:**
> **Balanced occupies useful middle ground.** At 9.40% return, 13.30% vol, and 3.33% yield, the Balanced portfolio captures 66% of Growth's return at 79% of Growth's volatility, while still generating nearly double Growth's yield.

**LLM:**
> **Balanced (9.82% return, 2.72% yield, 12.90% vol)** sits in the middle on every metric without excelling at any. [...] Whether that tradeoff is worth it depends entirely on your time horizon, income needs, and tolerance for watching your portfolio swing 20% in a bad quarter.

*All three read well. But only one is backed by a solution that isn't dominated.*

---

### How each method quantifies tradeoffs

**Frontier** — computed marginal rates from 182 solutions:
> Moving from **Safety to Balanced**: gaining 7.6 percentage points of return costs 8.0 points of additional volatility — roughly 1:1.
> Moving from **Balanced to Growth**: gaining another 9.1 points of return costs 6.5 points of volatility but sacrifices 2.8 points of yield.
> Moving from **Balanced to Income**: gaining 2.0 points of yield costs 5.6 points of return but actually reduces volatility by 2.6 points — income and stability go together here.

**pymoo** — computed from 45 solutions:
> Moving from Safety to Growth buys 9.24 percentage points of additional return. The price is 7.64 points of additional volatility and 1.92 points of lost yield. Put differently, each additional point of return costs roughly 0.83 points of volatility -- not a linear exchange, but a useful heuristic.

**LLM** — computed from 4 hand-picked portfolios:
> Moving from Growth to Income, you gain 4.16 percentage points of dividend yield but surrender 15.77 percentage points of total return.

*The structure is identical. The difference: Frontier's rates measure the actual Pareto surface (182 data points). The LLM's measure the gap between two of its own guesses.*

---

### How each method invites further exploration

**Frontier:**
> Each of these strategies is optimal at its particular tradeoff — none dominates another. [...] There are also **178 other Pareto-optimal portfolios** between these anchors — if you lean toward one direction but want to moderate it, we can explore the gradations.

**pymoo:**
> Which of these profiles -- or which region of the tradeoff space -- aligns with what you are trying to accomplish?

**LLM:**
> The question is not which portfolio is correct. It is which tradeoff you can live with for the next 5-10 years.

*Frontier can deliver on the promise — 178 portfolios are actually there to explore. pymoo gestures toward a "region" but the user would need to write code to access it. The LLM's question is rhetorical — there are no other portfolios to show.*

---

### How each method handles structural insight

**Frontier** — derived from computed correlations across 182 solutions:
> The strong positive correlation between return and volatility (r=0.95) means there is no free lunch. [...] HYG appears in every curated strategy, suggesting high-yield bonds occupy a unique position in the tradeoff space.

**pymoo** — observed from 45 solutions:
> Gold (GLD) and short-term Treasuries (VGSH) appear in all four strategies, playing opposite roles: GLD drives return, VGSH dampens volatility. [...] **What is absent is informative.** No strategy allocates to MCHI (China, -4.96% return).

**LLM** — inferred from reasoning:
> This portfolio earned the highest returns over the past 5 years, but it pays almost nothing in dividends and would have delivered stomach-churning drawdowns along the way. It is a bet that the commodity/energy/tech supercycle continues.

*All three produce useful structural observations. The difference is verifiability: Frontier's r=0.95 is computed. The LLM's "supercycle" framing is editorial.*

---

### Where the LLM is most honest

> I evaluated approximately 40-50 candidate allocations by hand [...] I have no guarantee that any of these four portfolios is globally optimal for its stated objective. A solver exploring the full space would almost certainly find allocations that dominate mine on one or more metrics.

> **Income** is the most suspect. VNQI has -0.58% return and 18.22% volatility -- it is a yield trap that drags down both return and risk-adjusted performance.

> The honest answer is: I do not know how far these portfolios are from the true efficient frontier of this problem.

*This self-assessment is accurate — confirmed by the comparison data. But it only appears after the recommendations, in a limitations section most users won't read.*

---

## The Single Number

At 6% target return:
- **Frontier** needs **7.2% volatility**
- **pymoo** needs **13.2% volatility**
- **LLM** has **no solution**

The gap is 6 percentage points of volatility between Frontier and the next-best option. That's the cost of incomplete exploration — not in theory, in a real allocation.

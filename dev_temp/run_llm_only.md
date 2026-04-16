# LLM-Only Portfolio Construction

## Raw Data Reference

| Ticker | Category | Return (%) | Volatility (%) | Div Yield (%) | Sector ETF? | Alt ETF? |
|--------|----------|-----------|----------------|---------------|-------------|----------|
| VOO | US Large Cap Blend | 11.89 | 15.61 | 1.09 | No | No |
| VTV | US Large Cap Value | 10.34 | 14.45 | 1.92 | No | No |
| VUG | US Large Cap Growth | 12.05 | 19.80 | 0.41 | No | No |
| VO | US Mid Cap | 6.60 | 17.12 | 1.44 | No | No |
| VB | US Small Cap | 5.75 | 19.00 | 1.28 | No | No |
| VXUS | International Total | 7.64 | 15.68 | 2.99 | No | No |
| VEA | Intl Developed | 8.79 | 16.75 | 2.94 | No | No |
| VWO | Emerging Markets | 4.40 | 15.36 | 2.71 | No | No |
| BND | US Aggregate Bond | 0.21 | 6.51 | 4.30 | No | No |
| VGSH | Short-Term Treasury | 1.83 | 2.20 | 3.76 | No | No |
| VGLT | Long-Term Treasury | -5.03 | 13.82 | 4.90 | No | No |
| LQD | IG Corporate Bond | 0.04 | 9.91 | 5.15 | No | No |
| TIP | TIPS | 1.03 | 6.62 | 5.84 | No | No |
| HYG | High Yield Bond | 3.85 | 7.88 | 6.70 | No | No |
| BNDX | Intl Bond | 0.28 | 6.10 | 3.26 | No | No |
| EMB | EM Bond | 1.79 | 10.44 | 5.89 | No | No |
| VNQ | REITs | 2.45 | 19.69 | 3.93 | No | Yes |
| GLD | Gold | 20.00 | 15.90 | 0.00 | No | Yes |
| GSG | Commodities | 15.17 | 19.52 | 0.00 | No | Yes |
| VGT | Technology | 15.88 | 21.39 | 0.40 | Yes | No |
| VHT | Healthcare | 4.26 | 14.83 | 1.32 | Yes | No |
| VDE | Energy | 21.97 | 26.62 | 2.43 | Yes | No |
| VFH | Financials | 8.20 | 19.06 | 1.62 | Yes | No |
| VYM | High Dividend | 10.71 | 14.38 | 2.37 | No | No |
| SCHD | Dividend Quality | 7.45 | 15.35 | 3.44 | No | No |

---

## Strategy 1: Growth Portfolio

### Reasoning Process

**Goal:** Maximize return, accept higher volatility, sacrifice dividend yield.

**Step 1 -- Identify top returners:**
- VDE: 21.97% return (but 26.62% vol -- very high, sector ETF)
- GLD: 20.00% return (15.90% vol -- excellent return/vol, alternative ETF)
- VGT: 15.88% return (21.39% vol, sector ETF)
- GSG: 15.17% return (19.52% vol, alternative ETF)
- VUG: 12.05% return (19.80% vol)
- VOO: 11.89% return (15.61% vol)

**Step 2 -- Apply constraints mentally:**
- Max 2 sector ETFs: I want VDE and VGT (highest returning sectors).
- Max 2 alternative ETFs: I want GLD (best return/vol ratio of any ETF). GSG also attractive but 19.52% vol is high.
- Volatility constraint: weighted avg must be <= 20%. VDE at 26.62% is the problem child. Need to balance.

**Step 3 -- Draft allocation:**
I want to load up on the highest returners while staying under 20% vol. Let me try:

- GLD: 30% (20.00 ret, 15.90 vol) -- best risk-adjusted returner
- VDE: 15% (21.97 ret, 26.62 vol) -- highest return, but vol is punishing
- VGT: 15% (15.88 ret, 21.39 vol) -- strong return
- VUG: 20% (12.05 ret, 19.80 vol) -- growth equity
- VOO: 20% (11.89 ret, 15.61 vol) -- broad market anchor

**Constraint checks:**
- Holdings: 5 (within 4-12)
- Sector ETFs: VDE + VGT = 2 (at limit)
- Alternative ETFs: GLD = 1 (within limit)
- Sum: 30+15+15+20+20 = 100%

**Weighted volatility calculation:**
- GLD: 0.30 * 15.90 = 4.770
- VDE: 0.15 * 26.62 = 3.993
- VGT: 0.15 * 21.39 = 3.209
- VUG: 0.20 * 19.80 = 3.960
- VOO: 0.20 * 15.61 = 3.122
- **Total: 19.054%** -- under 20%, passes.

**Weighted return:**
- GLD: 0.30 * 20.00 = 6.000
- VDE: 0.15 * 21.97 = 3.296
- VGT: 0.15 * 15.88 = 2.382
- VUG: 0.20 * 12.05 = 2.410
- VOO: 0.20 * 11.89 = 2.378
- **Total: 16.466%**

**Weighted dividend yield:**
- GLD: 0.30 * 0.00 = 0.000
- VDE: 0.15 * 2.43 = 0.365
- VGT: 0.15 * 0.40 = 0.060
- VUG: 0.20 * 0.41 = 0.082
- VOO: 0.20 * 1.09 = 0.218
- **Total: 0.725%**

### Growth Portfolio Summary

| Ticker | Allocation | Return | Volatility | Div Yield |
|--------|-----------|--------|------------|-----------|
| GLD | 30% | 20.00 | 15.90 | 0.00 |
| VDE | 15% | 21.97 | 26.62 | 2.43 |
| VGT | 15% | 15.88 | 21.39 | 0.40 |
| VUG | 20% | 12.05 | 19.80 | 0.41 |
| VOO | 20% | 11.89 | 15.61 | 1.09 |
| **Weighted** | **100%** | **16.47%** | **19.05%** | **0.73%** |

**Constraints:** All satisfied. Sector ETFs: 2/2. Alternative ETFs: 1/2. Holdings: 5. Volatility: 19.05% <= 20%.

---

## Strategy 2: Balanced Portfolio

### Reasoning Process

**Goal:** Moderate performance across all three objectives -- decent return, moderate vol, reasonable yield.

**Step 1 -- Strategy:**
Mix equity for return, bonds for yield and vol reduction, and pick ETFs with good yield/return balance. Target roughly 7-10% return, 12-15% vol, 2-3% yield.

**Step 2 -- Select ETFs:**
- VYM: 10.71% ret, 14.38% vol, 2.37% yield -- excellent balanced profile
- VTV: 10.34% ret, 14.45% vol, 1.92% yield -- solid value with decent yield
- VEA: 8.79% ret, 16.75% vol, 2.94% yield -- international diversification with yield
- GLD: 20.00% ret, 15.90% vol, 0.00% yield -- return booster
- HYG: 3.85% ret, 7.88% vol, 6.70% yield -- yield anchor with low vol
- BND: 0.21% ret, 6.51% vol, 4.30% yield -- vol dampener and yield

**Step 3 -- Draft allocation:**
- VYM: 25%
- VTV: 20%
- VEA: 15%
- GLD: 15%
- HYG: 15%
- BND: 10%

**Constraint checks:**
- Holdings: 6 (within 4-12)
- Sector ETFs: 0 (within limit)
- Alternative ETFs: GLD = 1 (within limit)
- Sum: 25+20+15+15+15+10 = 100%

**Weighted volatility:**
- VYM: 0.25 * 14.38 = 3.595
- VTV: 0.20 * 14.45 = 2.890
- VEA: 0.15 * 16.75 = 2.513
- GLD: 0.15 * 15.90 = 2.385
- HYG: 0.15 * 7.88 = 1.182
- BND: 0.10 * 6.51 = 0.651
- **Total: 13.216%**

**Weighted return:**
- VYM: 0.25 * 10.71 = 2.678
- VTV: 0.20 * 10.34 = 2.068
- VEA: 0.15 * 8.79 = 1.319
- GLD: 0.15 * 20.00 = 3.000
- HYG: 0.15 * 3.85 = 0.578
- BND: 0.10 * 0.21 = 0.021
- **Total: 9.664%**

**Weighted dividend yield:**
- VYM: 0.25 * 2.37 = 0.593
- VTV: 0.20 * 1.92 = 0.384
- VEA: 0.15 * 2.94 = 0.441
- GLD: 0.15 * 0.00 = 0.000
- HYG: 0.15 * 6.70 = 1.005
- BND: 0.10 * 4.30 = 0.430
- **Total: 2.853%**

### Balanced Portfolio Summary

| Ticker | Allocation | Return | Volatility | Div Yield |
|--------|-----------|--------|------------|-----------|
| VYM | 25% | 10.71 | 14.38 | 2.37 |
| VTV | 20% | 10.34 | 14.45 | 1.92 |
| VEA | 15% | 8.79 | 16.75 | 2.94 |
| GLD | 15% | 20.00 | 15.90 | 0.00 |
| HYG | 15% | 3.85 | 7.88 | 6.70 |
| BND | 10% | 0.21 | 6.51 | 4.30 |
| **Weighted** | **100%** | **9.66%** | **13.22%** | **2.85%** |

**Constraints:** All satisfied. Sector ETFs: 0/2. Alternative ETFs: 1/2. Holdings: 6. Volatility: 13.22% <= 20%.

---

## Strategy 3: Income Portfolio

### Reasoning Process

**Goal:** Maximize dividend yield, accept lower returns.

**Step 1 -- Identify highest yielders:**
- HYG: 6.70% yield (7.88% vol -- great)
- EMB: 5.89% yield (10.44% vol)
- TIP: 5.84% yield (6.62% vol)
- LQD: 5.15% yield (9.91% vol)
- VGLT: 4.90% yield (13.82% vol -- poor return of -5.03%, avoid)
- BND: 4.30% yield (6.51% vol)
- VNQ: 3.93% yield (19.69% vol -- too much vol for the return)
- VGSH: 3.76% yield (2.20% vol)
- SCHD: 3.44% yield (15.35% vol, 7.45% return -- equity with yield)

**Step 2 -- Strategy:**
Load up on high-yield bonds. Add SCHD for equity yield plus some return. Avoid VGLT (negative return) and VNQ (high vol, low return).

**Step 3 -- Draft allocation:**
- HYG: 25%
- TIP: 20%
- EMB: 15%
- SCHD: 15%
- LQD: 10%
- BND: 10%
- VGSH: 5%

**Constraint checks:**
- Holdings: 7 (within 4-12)
- Sector ETFs: 0 (within limit)
- Alternative ETFs: 0 (within limit)
- Sum: 25+20+15+15+10+10+5 = 100%

**Weighted volatility:**
- HYG: 0.25 * 7.88 = 1.970
- TIP: 0.20 * 6.62 = 1.324
- EMB: 0.15 * 10.44 = 1.566
- SCHD: 0.15 * 15.35 = 2.303
- LQD: 0.10 * 9.91 = 0.991
- BND: 0.10 * 6.51 = 0.651
- VGSH: 0.05 * 2.20 = 0.110
- **Total: 8.915%**

**Weighted return:**
- HYG: 0.25 * 3.85 = 0.963
- TIP: 0.20 * 1.03 = 0.206
- EMB: 0.15 * 1.79 = 0.269
- SCHD: 0.15 * 7.45 = 1.118
- LQD: 0.10 * 0.04 = 0.004
- BND: 0.10 * 0.21 = 0.021
- VGSH: 0.05 * 1.83 = 0.092
- **Total: 2.673%**

**Weighted dividend yield:**
- HYG: 0.25 * 6.70 = 1.675
- TIP: 0.20 * 5.84 = 1.168
- EMB: 0.15 * 5.89 = 0.884
- SCHD: 0.15 * 3.44 = 0.516
- LQD: 0.10 * 5.15 = 0.515
- BND: 0.10 * 4.30 = 0.430
- VGSH: 0.05 * 3.76 = 0.188
- **Total: 5.376%**

### Income Portfolio Summary

| Ticker | Allocation | Return | Volatility | Div Yield |
|--------|-----------|--------|------------|-----------|
| HYG | 25% | 3.85 | 7.88 | 6.70 |
| TIP | 20% | 1.03 | 6.62 | 5.84 |
| EMB | 15% | 1.79 | 10.44 | 5.89 |
| SCHD | 15% | 7.45 | 15.35 | 3.44 |
| LQD | 10% | 0.04 | 9.91 | 5.15 |
| BND | 10% | 0.21 | 6.51 | 4.30 |
| VGSH | 5% | 1.83 | 2.20 | 3.76 |
| **Weighted** | **100%** | **2.67%** | **8.92%** | **5.38%** |

**Constraints:** All satisfied. Sector ETFs: 0/2. Alternative ETFs: 0/2. Holdings: 7. Volatility: 8.92% <= 20%.

---

## Strategy 4: Safety Portfolio

### Reasoning Process

**Goal:** Minimize volatility above all else.

**Step 1 -- Identify lowest-vol ETFs:**
- VGSH: 2.20% vol (1.83% ret, 3.76% yield)
- BNDX: 6.10% vol (0.28% ret, 3.26% yield)
- BND: 6.51% vol (0.21% ret, 4.30% yield)
- TIP: 6.62% vol (1.03% ret, 5.84% yield)
- HYG: 7.88% vol (3.85% ret, 6.70% yield)
- LQD: 9.91% vol (0.04% ret, 5.15% yield)

**Step 2 -- Strategy:**
Concentrate in the lowest-vol instruments. VGSH is the clear winner at 2.20% vol. Load heavily into sub-7% vol bonds.

**Step 3 -- Draft allocation:**
- VGSH: 40%
- BND: 20%
- BNDX: 15%
- TIP: 15%
- HYG: 10%

**Constraint checks:**
- Holdings: 5 (within 4-12)
- Sector ETFs: 0 (within limit)
- Alternative ETFs: 0 (within limit)
- Sum: 40+20+15+15+10 = 100%

**Weighted volatility:**
- VGSH: 0.40 * 2.20 = 0.880
- BND: 0.20 * 6.51 = 1.302
- BNDX: 0.15 * 6.10 = 0.915
- TIP: 0.15 * 6.62 = 0.993
- HYG: 0.10 * 7.88 = 0.788
- **Total: 4.878%**

**Weighted return:**
- VGSH: 0.40 * 1.83 = 0.732
- BND: 0.20 * 0.21 = 0.042
- BNDX: 0.15 * 0.28 = 0.042
- TIP: 0.15 * 1.03 = 0.155
- HYG: 0.10 * 3.85 = 0.385
- **Total: 1.356%**

**Weighted dividend yield:**
- VGSH: 0.40 * 3.76 = 1.504
- BND: 0.20 * 4.30 = 0.860
- BNDX: 0.15 * 3.26 = 0.489
- TIP: 0.15 * 5.84 = 0.876
- HYG: 0.10 * 6.70 = 0.670
- **Total: 4.399%**

### Safety Portfolio Summary

| Ticker | Allocation | Return | Volatility | Div Yield |
|--------|-----------|--------|------------|-----------|
| VGSH | 40% | 1.83 | 2.20 | 3.76 |
| BND | 20% | 0.21 | 6.51 | 4.30 |
| BNDX | 15% | 0.28 | 6.10 | 3.26 |
| TIP | 15% | 1.03 | 6.62 | 5.84 |
| HYG | 10% | 3.85 | 7.88 | 6.70 |
| **Weighted** | **100%** | **1.36%** | **4.88%** | **4.40%** |

**Constraints:** All satisfied. Sector ETFs: 0/2. Alternative ETFs: 0/2. Holdings: 5. Volatility: 4.88% <= 20%.

---

## Cross-Portfolio Comparison

| Metric | Growth | Balanced | Income | Safety |
|--------|--------|----------|--------|--------|
| Wtd Return (%) | 16.47 | 9.66 | 2.67 | 1.36 |
| Wtd Volatility (%) | 19.05 | 13.22 | 8.92 | 4.88 |
| Wtd Div Yield (%) | 0.73 | 2.85 | 5.38 | 4.40 |
| # Holdings | 5 | 6 | 7 | 5 |
| Sector ETFs | 2 | 0 | 0 | 0 |
| Alternative ETFs | 1 | 1 | 0 | 0 |

---

## Brutal Honesty: Limitations & Self-Critique

### Where I Used Intuition vs. Math

**Pure math (arithmetic):** All weighted average calculations were done step-by-step with multiplication and addition. These are verifiable.

**Intuition / heuristics (not math):**
- **ETF selection** was entirely heuristic. I eyeballed the sorted lists and picked ETFs that "seemed good" for each goal. An optimizer would consider all 25 simultaneously.
- **Allocation percentages** were chosen by feel. I picked round numbers (15%, 20%, 25%) and adjusted by gut to stay under the 20% volatility constraint. There is no mathematical basis for why Growth has 30% GLD instead of 28% or 33%.
- **I did not consider correlations at all.** Weighted average volatility is NOT portfolio volatility. Real portfolio volatility depends on the covariance matrix. Two assets with 15% individual volatility but -0.5 correlation would produce a portfolio far less volatile than 15%. My "Safety" portfolio might actually be riskier or safer than calculated depending on bond correlations. This is the single biggest limitation.
- **I implicitly assumed the objective function** for each strategy without defining it precisely. "Maximize return, accept higher vol" -- what's the tradeoff rate? An optimizer needs an explicit objective.

### Dominance Analysis -- Which Portfolios Might Be Dominated?

A portfolio is **dominated** if another feasible portfolio is better on ALL three objectives (higher return, lower vol, higher yield simultaneously).

- **Safety vs. Income:** Income has higher return (2.67 > 1.36), higher yield (5.38 > 4.40), but also higher vol (8.92 > 4.88). NOT dominated -- Safety wins on vol.
- **Growth vs. Balanced:** Growth has higher return (16.47 > 9.66) but worse vol (19.05 > 13.22) and worse yield (0.73 < 2.85). NOT dominated.
- **None of my four portfolios dominate each other**, which is a good sign they represent genuine tradeoffs. But this says nothing about whether *other portfolios I didn't consider* dominate them.

**Could an unconsidered portfolio dominate one of mine?** Almost certainly yes. For example, my Income portfolio might be dominated by a portfolio that adds 5% GLD (boosting return significantly with moderate vol increase) while reducing VGSH (small yield loss). I did not search this space.

### Solution Space Size

With 25 ETFs, 4-12 holdings, and allocations in 1% increments summing to 100%:

- **Choosing k ETFs from 25:** C(25,4) + C(25,5) + ... + C(25,12) = 12,650 + 53,130 + 177,100 + 480,700 + ... approximately 10-15 million combinations of ETFs.
- **For each combination of k ETFs, allocations in 1% increments summing to 100:** This is a stars-and-bars problem: C(99, k-1) possibilities. For k=5, that is C(99,4) = ~3.7 million. For k=8, it is astronomical.
- **Total feasible portfolios:** Conservatively hundreds of billions, possibly trillions.
- **Portfolios I evaluated:** ~4 final portfolios, plus maybe ~5-10 mental drafts during reasoning. Call it roughly **15 candidate portfolios** out of trillions.

I explored approximately 0.000000001% of the solution space.

### What an Optimizer Can Do That I Cannot

1. **Explore the full solution space** systematically, not by heuristic gut feeling.
2. **Handle correlations and covariance.** Real portfolio volatility requires a covariance matrix. I computed weighted-average volatility, which overstates risk for diversified portfolios and understates it for concentrated/correlated ones.
3. **Find Pareto-optimal frontiers.** An optimizer can enumerate all non-dominated portfolios across the three objectives, giving the decision-maker exact tradeoff curves. I gave 4 ad-hoc points.
4. **Precisely optimize continuous allocations.** I used round numbers. An optimizer can find that 27.3% in GLD and 17.8% in VDE is meaningfully better than my rounded guesses.
5. **Handle nonlinear constraints** (e.g., tracking error, conditional value-at-risk) that I cannot reason about.
6. **Guarantee constraint satisfaction** while maximizing the objective. I verified constraints post-hoc; an optimizer enforces them during search.
7. **Sensitivity analysis.** How much does the optimal portfolio change if VDE's expected return drops by 2%? An optimizer can answer this instantly. I would need to re-reason from scratch.

### Summary

These portfolios represent reasonable, heuristic-driven allocations. They satisfy all stated constraints and represent genuinely different risk/return/yield profiles. However, they are almost certainly suboptimal compared to what a mathematical optimizer would produce, particularly because:
- I ignored correlations entirely (weighted avg vol != portfolio vol)
- I explored a negligible fraction of the feasible space
- My allocations are rounded guesses, not optimal solutions
- I cannot guarantee these are Pareto-efficient

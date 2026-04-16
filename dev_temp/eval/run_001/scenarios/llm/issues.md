# Issues Log — LLM Pure Reasoning Method

## 1. Arithmetic Uncertainty

**Severity: Medium**

All portfolio metrics were computed via mental/manual arithmetic. Specific areas of concern:

- **Weighted-average calculations with 6-8 holdings:** Each portfolio requires multiplying 6-8 pairs of numbers and summing. Rounding errors accumulate. I estimate arithmetic is accurate to +/- 0.3% for return and vol, +/- 0.15% for yield.
- **Scenario score adjustments:** Multipliers are straightforward (e.g., 11.98 x 1.5 = 17.97) but chain adjustments (multiplier then override) require careful ordering. I verified each override replaces (not adds to) the multiplied value.
- **Vol constraint boundary cases:** Several portfolios (e.g., S1 Max-Return) required iterative adjustment to stay under 20%. The first attempt at S1 Max-Return came to 20.85%, requiring portfolio restructuring. There may be tighter configurations I didn't explore.

**Specific arithmetic I am least confident about:**
- S2 Income portfolio return (11.00%): 7 terms with mixed equity and bond multipliers
- S3 Income portfolio return (3.92%): Mix of overridden bond returns and crushed equity returns
- S4 Balanced portfolio return (20.25%): 6 terms with multiple override types

## 2. Weighted-Average Volatility Limitation

**Severity: High**

The portfolio volatility is computed as a weighted average of individual ETF volatilities. This is a significant simplification:

- **Real portfolio vol depends on correlations.** A portfolio of VOO (15.63%) and BND (6.51%) at 50/50 would be ~5-8% in reality (negative/low correlation), not 11.07% (the weighted average). My "Safety" portfolios likely overstate true volatility.
- **Diversification benefit is ignored.** Adding uncorrelated assets (GLD, DBA) to equity portfolios reduces real vol more than the weighted average suggests. My Balanced portfolios probably have 2-5% less real vol than stated.
- **The 20% vol constraint may be too loose or too tight** depending on actual correlations. Some portfolios marked as "under 20%" might actually be well under 15% in reality, while others could exceed 20% in high-correlation regimes.
- **Implication for rankings:** The vol metric cannot be reliably used to rank portfolios by risk. A portfolio with 14% weighted-avg vol might have lower real vol than one with 12% if it has better diversification.

## 3. Constraint Tracking Across Scenarios

**Severity: Low-Medium**

Each of the 21 portfolios (4 scenarios x 4-6 portfolios) required checking 5 constraints:
1. Max single allocation <= 30%
2. Vol <= 20%
3. Sector ETFs <= 3
4. Alternative ETFs <= 3
5. 4-12 holdings

**Risk of constraint violations:** I verified each portfolio inline, but the repetitive nature of 100+ constraint checks increases error risk. The most error-prone constraint is the vol ceiling -- it requires a full weighted average calculation. I caught and corrected one violation (S1 Max-Return initial draft at 20.85%).

**ETF group membership could be misapplied.** I treated the following strictly:
- Sectors: VGT, VHT, VDE, VFH, VPU, VDC, VOX (7 total)
- Alternatives: VNQ, VNQI, GLD, GSG, DBA, IGF (6 total)

No portfolio uses more than 3 from either group.

## 4. Dominance Assessment

**Severity: Medium**

**Are any portfolios dominated?**

A portfolio is dominated if another portfolio has better (or equal) return, lower (or equal) vol, AND higher (or equal) yield.

**S1 Base Case:**
- Growth (15.31%, 19.58%, 1.08%) vs Max-Return (16.61%, 19.59%, 1.02%): Max-Return dominates Growth on return (~same vol, ~same yield). However the difference is tiny and within arithmetic uncertainty. **Possible domination.**
- Income (7.24%, 13.45%, 3.81%) vs Max-Yield (4.06%, 12.61%, 4.69%): Neither dominates -- Income has better return, Max-Yield has better yield and vol.

**S3 Recession:**
- Safety (4.17%, 6.34%, 3.89%) vs Income (3.92%, 11.10%, 3.90%): Safety nearly dominates Income -- higher return, much lower vol, comparable yield. Income is only marginally better on yield (3.90% vs 3.89%). **Safety effectively dominates Income in this scenario.**

**S4 Inflation:**
- No clear domination. Each strategy occupies a distinct region.

**Honest assessment:** I did not exhaustively search the combinatorial space. With 30 ETFs and 4-12 holdings at integer percentages (min 1%), the space is enormous. My portfolios represent plausible good solutions found by reasoning about the top ETFs for each objective, not guaranteed optima.

## 5. Candidate Search Depth

**Severity: Medium**

- **S1:** Considered ~10 configurations across 6 portfolios. Focused on top-12 ETFs by return, top-8 by yield, and bottom-5 by vol. Did not systematically evaluate mid-tier ETFs (VO, VB, VFH, VOX) which might participate in balanced solutions.
- **S2:** Considered ~8 configurations. The strong dominance of VGT/VDE made the choice set obvious for growth. Income was harder due to halved bond yields.
- **S3:** ~6 configurations. The viable ETF set collapsed to ~10 (bonds + gold + DBA + IGF). Limited room for creativity.
- **S4:** ~6 configurations. Commodity dominance made growth/balanced straightforward. Safety was the most creative portfolio.

**What I likely missed:**
- Three-way tradeoff exploration: I didn't systematically try to improve yield on growth portfolios or return on income portfolios.
- Mid-tier ETFs that might offer better vol-adjusted contributions (e.g., VHT at 14.83% vol with moderate returns).
- Larger portfolios (10-12 holdings) that might achieve better diversification with small allocations to many ETFs.

## 6. Score Adjustment Ambiguity

**Severity: Low**

- **"Bond yields" in S2:** The spec says "bond yields x 0.5". I interpreted this as dividend_yield for bond ETFs being halved, not the return. This seems consistent with the distinction between "returns" and "yields" in the spec.
- **Sector adjustments in S4:** The spec does not mention sector-specific adjustments for S4 (only equity, bond, and specific overrides). I left sector ETFs at base values except for the VDE override. This could be debated -- are sectors "equity"? I treated them as their own group per the spec's group definitions.
- **"Alternative returns x 0.5" in S3:** Applied before the GLD override (base x 1.3). The override says "base x 1.3" which I interpreted as 19.88 * 1.3 = 25.84, not (19.88 * 0.5) * 1.3. Overrides replace multiplied values.

## 7. Integer Allocation Constraint

**Severity: Low**

All allocations use integer percentages (minimum 1% if held) summing to 100%. This constraint limits precision -- e.g., 7.5% might be optimal for an ETF but I must choose 7% or 8%. With 4-12 holdings and 5% minimum effective step sizes in practice, the quantization error is small relative to other uncertainties.

## 8. Portfolio Construction Heuristic Limitations

**Severity: Medium**

My approach was greedy/heuristic:
1. Rank ETFs by the primary objective for each strategy
2. Select top candidates that satisfy constraints
3. Adjust weights to meet vol ceiling and diversification goals
4. Verify constraints

This misses:
- **Interaction effects:** Two ETFs that are individually mediocre might combine well
- **Non-obvious allocations:** e.g., a 1% allocation to a high-vol ETF might improve frontier position
- **Systematic frontier tracing:** A proper optimizer would vary objective weights continuously to trace the full Pareto frontier. I sampled 4-6 points per scenario.

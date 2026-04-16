# LLM-Only Portfolio Construction

**Date:** 2026-04-12
**Method:** Pure LLM reasoning (no optimization solver)
**Universe:** 25 ETFs from etf_consolidated.json (5yr trailing data, 2021-05 to 2026-04)

## Objectives
- Maximize expected return (ann_return_5yr_pct)
- Minimize volatility (ann_volatility_5yr_pct)
- Maximize dividend yield (dividend_yield_pct)

## Constraints
- Volatility cap: 20%
- Max 2 sector ETFs (VGT, VHT, VDE, VFH)
- Max 2 alternative ETFs (VNQ, GLD, GSG)
- Holdings count: 4-12
- Allocations sum to 100%

---

## Strategy 1: Growth-Oriented

### Reasoning Process

My goal is to maximize return while staying under the 20% vol cap. I start by identifying the highest-return ETFs:

1. **VDE (21.97% ret)** -- best return, but 26.62% vol is way too high to use at large weight.
2. **GLD (20.00% ret, 15.90% vol)** -- excellent return-to-vol ratio, and gold's correlation with equities is typically low, so mixing it in should help vol.
3. **VGT (15.88% ret, 21.39% vol)** -- high return but high vol. Using VDE + VGT would consume both sector slots.
4. **VOO (11.89% ret, 15.61% vol)** -- solid return, moderate vol, broad diversification.
5. **VUG (12.05% ret, 19.80% vol)** -- slightly higher return than VOO but much more volatile.

**Key tension:** VDE has the best return but extreme vol. I need to keep it small or pair it with low-vol assets. VGT also breaches 20% vol solo, but its return is lower than GLD at lower vol -- so GLD is actually a better risk-adjusted pick (I'm using a rough Sharpe-like intuition here, not a formal calculation).

**Selection:**
- GLD 25% (high return, moderate vol, alternative slot 1)
- VOO 30% (reliable return, moderate vol, core)
- VDE 10% (highest return but capped due to vol, sector slot 1)
- VGT 10% (high return, sector slot 2)
- VUG 15% (growth tilt)
- VGSH 10% (vol dampener -- 2.20% vol pulls the portfolio vol down)

**Weighted calculations:**

| ETF  | Weight | Return | Vol   | Div Yield |
|------|--------|--------|-------|-----------|
| GLD  | 0.25   | 5.000  | 3.975 | 0.000     |
| VOO  | 0.30   | 3.567  | 4.683 | 0.327     |
| VDE  | 0.10   | 2.197  | 2.662 | 0.243     |
| VGT  | 0.10   | 1.588  | 2.139 | 0.040     |
| VUG  | 0.15   | 1.808  | 2.970 | 0.062     |
| VGSH | 0.10   | 0.183  | 0.220 | 0.376     |

**Portfolio totals (naive weighted average):**
- **Expected Return: 14.34%**
- **Volatility: 16.65%** (weighted average -- actual would be lower due to imperfect correlation)
- **Dividend Yield: 1.05%**

**Constraint check:** Vol 16.65% < 20% (pass). Sector ETFs: 2 (VDE, VGT -- pass). Alternatives: 1 (GLD -- pass). Holdings: 6 (pass).

---

## Strategy 2: Balanced

### Reasoning Process

I want a middle ground across all three objectives. This means sacrificing some return for lower vol and better yield. I should blend equities, bonds, and some alternatives.

**Key insight:** Bonds like BND and VGSH contribute high dividend yield and very low vol, but near-zero return. HYG (3.85% ret, 7.88% vol, 6.70% div) is interesting -- it bridges the gap with moderate return, low vol, AND the highest dividend yield in the set.

**Selection reasoning:**
- VOO for equity core (decent return, moderate vol, some yield)
- VTV for value tilt (slightly lower return than VOO but higher yield, lower vol)
- GLD for return boost and diversification
- VEA for international diversification and yield
- HYG for yield and low vol
- BND for vol dampening and yield

| ETF  | Weight | Return | Vol   | Div Yield |
|------|--------|--------|-------|-----------|
| VOO  | 0.25   | 2.973  | 3.903 | 0.273     |
| VTV  | 0.15   | 1.551  | 2.168 | 0.288     |
| GLD  | 0.15   | 3.000  | 2.385 | 0.000     |
| VEA  | 0.10   | 0.879  | 1.675 | 0.294     |
| HYG  | 0.15   | 0.578  | 1.182 | 1.005     |
| BND  | 0.20   | 0.042  | 1.302 | 0.860     |

**Portfolio totals:**
- **Expected Return: 9.02%**
- **Volatility: 12.61%**
- **Dividend Yield: 2.72%**

**Constraint check:** Vol 12.61% < 20% (pass). Sector ETFs: 0 (pass). Alternatives: 1 (GLD -- pass). Holdings: 6 (pass).

---

## Strategy 3: Income-Oriented

### Reasoning Process

Maximize dividend yield as the primary objective, with return as secondary and vol kept reasonable. I scan for the highest-yield ETFs:

- HYG: 6.70% div (best yield, low vol, okay return)
- EMB: 5.89% div (EM bond, moderate vol)
- TIP: 5.84% div (TIPS, low vol)
- LQD: 5.15% div (IG corporate, moderate vol, near-zero return)
- VGLT: 4.90% div (long treasury, but NEGATIVE return -- avoid)
- BND: 4.30% div
- VNQ: 3.93% div (REIT, but terrible return-to-vol)
- VGSH: 3.76% div (ultra-low vol)
- SCHD: 3.44% div (dividend equity, decent return)

**Tension:** Pure income means loading up on bonds, but then return craters. I need to balance with some equity yield plays like VYM and SCHD that provide both decent returns AND yield.

| ETF  | Weight | Return | Vol   | Div Yield |
|------|--------|--------|-------|-----------|
| HYG  | 0.20   | 0.770  | 1.576 | 1.340     |
| TIP  | 0.10   | 0.103  | 0.662 | 0.584     |
| SCHD | 0.15   | 1.118  | 2.303 | 0.516     |
| VYM  | 0.15   | 1.607  | 2.157 | 0.356     |
| EMB  | 0.10   | 0.179  | 1.044 | 0.589     |
| BND  | 0.15   | 0.032  | 0.977 | 0.645     |
| VGSH | 0.15   | 0.275  | 0.330 | 0.564     |

**Portfolio totals:**
- **Expected Return: 4.08%**
- **Volatility: 9.05%**
- **Dividend Yield: 4.59%**

**Constraint check:** Vol 9.05% < 20% (pass). Sector ETFs: 0 (pass). Alternatives: 0 (pass). Holdings: 7 (pass).

---

## Strategy 4: Safety / Conservative

### Reasoning Process

Minimize volatility as the primary objective. Accept the lowest return in exchange for the smoothest ride. Dividend yield is a secondary benefit.

**Ultra-low vol candidates:**
- VGSH: 2.20% vol (best in class)
- BNDX: 6.10% vol
- BND: 6.51% vol
- TIP: 6.62% vol
- HYG: 7.88% vol

I want to keep portfolio vol as low as possible while still generating some positive return. A heavy VGSH allocation is the key lever.

| ETF  | Weight | Return | Vol   | Div Yield |
|------|--------|--------|-------|-----------|
| VGSH | 0.35   | 0.641  | 0.770 | 1.316     |
| BND  | 0.20   | 0.042  | 1.302 | 0.860     |
| TIP  | 0.15   | 0.155  | 0.993 | 0.876     |
| HYG  | 0.10   | 0.385  | 0.788 | 0.670     |
| VYM  | 0.10   | 1.071  | 1.438 | 0.237     |
| BNDX | 0.10   | 0.028  | 0.610 | 0.326     |

**Portfolio totals:**
- **Expected Return: 2.32%**
- **Volatility: 5.90%**
- **Dividend Yield: 4.29%**

**Constraint check:** Vol 5.90% < 20% (pass). Sector ETFs: 0 (pass). Alternatives: 0 (pass). Holdings: 6 (pass).

---

## Summary Comparison

| Metric            | Growth   | Balanced | Income  | Safety  |
|-------------------|----------|----------|---------|---------|
| Expected Return   | 14.34%   | 9.02%    | 4.08%   | 2.32%   |
| Volatility (wtd)  | 16.65%   | 12.61%   | 9.05%   | 5.90%   |
| Dividend Yield    | 1.05%    | 2.72%    | 4.59%   | 4.29%   |
| Holdings          | 6        | 6        | 7       | 6       |
| Sector ETFs used  | 2        | 0        | 0       | 0       |
| Alt ETFs used     | 1        | 1        | 0       | 0       |

---

## Honest Assessment of Limitations

### Where I used math vs. intuition

**Actual math:**
- Weighted average return, vol, and dividend yield are straight arithmetic -- I computed these precisely.
- Constraint checks (sector count, alt count, holding count, sum to 100%) are exact.

**Pure intuition (no math):**
- **Asset selection.** I picked ETFs based on eyeballing return/vol/yield profiles and choosing ones that "seemed good" for each strategy. A proper optimizer would evaluate all 25-choose-4-through-12 combinations (millions of possibilities).
- **Weight determination.** I assigned round-number weights (10%, 15%, 20%, etc.) based on gut feel for how much each ETF should contribute. An optimizer would find precise allocations like 13.7% or 22.4% that trace the efficient frontier.
- **Diversification benefit.** My volatility numbers are weighted averages, which OVERESTIMATE true portfolio volatility. Real portfolio vol depends on the covariance matrix between all holdings. A portfolio of assets with low correlation (e.g., GLD + VOO + BND) would have actual vol significantly lower than the weighted average. I have no correlation data and cannot compute this.

### Where my solutions are likely suboptimal or dominated

1. **The Growth portfolio probably leaves return on the table.** An optimizer might find that 12% VDE + 8% VGT + different equity weights yield higher return at the same weighted vol, since I used round numbers without fine-tuning.

2. **The Income portfolio might be dominated.** It's possible to construct a portfolio with the same ~4.6% yield but higher return, or the same return but higher yield. I wouldn't know without evaluating thousands of alternatives.

3. **I cannot find the actual efficient frontier.** These four portfolios are four points in a vast solution space. An optimizer would find the Pareto frontier -- the set of ALL non-dominated portfolios -- and let the user pick. I can only guess at 4 points that might or might not lie on that frontier.

4. **Volatility is overstated everywhere.** Since weighted-average vol ignores diversification benefits (correlation < 1), my actual portfolios would have lower true vol. This means I'm being too conservative -- I could potentially take on more equity exposure and still meet the 20% vol cap. The Growth portfolio's true vol might be closer to 13-14% rather than 16.65%, meaning I could have allocated more aggressively.

5. **No consideration of the return-vol-yield tradeoff surface.** With three objectives, the Pareto frontier is a 2D surface, not a line. I'm guessing at 4 points on that surface without knowing its shape.

6. **Availability bias in ETF selection.** I naturally gravitated toward ETFs I recognized or that had extreme values. An optimizer treats all 25 ETFs equally and might find that a small allocation to an "unremarkable" ETF like VWO or VO improves the portfolio in ways I didn't consider.

### Bottom line

An LLM can produce *reasonable* portfolios that satisfy constraints and roughly align with stated goals. But it cannot find *optimal* portfolios because it lacks: (a) the ability to evaluate the full combinatorial space, (b) covariance data to compute true portfolio risk, and (c) the mathematical machinery to trace the Pareto frontier across three simultaneous objectives.

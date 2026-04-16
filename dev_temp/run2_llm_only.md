# LLM-Only Portfolio Allocation: 30-ETF Problem

## 1. Reasoning Process

### Approach

I solved this by hand through greedy heuristic reasoning -- sorting ETFs by each objective, identifying candidates, then iteratively adjusting allocations to push the target metric while keeping weighted-average volatility under 20% and respecting the sector/alternative holding limits. No optimization solver, no code, no gradient descent. Just mental arithmetic and trial-and-error across roughly 40-50 candidate allocations.

### Growth Strategy (Maximize Return)

**Key insight:** The three highest-returning ETFs are VDE (22.08%), GLD (19.88%), and VGT (16.19%). VDE has punishing volatility (26.59%), so the allocation question becomes: how much VDE can I load before the 20% vol ceiling binds?

I started with balanced mixes of GLD/VDE/VGT/VOO, then realized GSG (15.86% return, alt category) dominates VOO on return while keeping vol manageable since it replaces broad equity exposure. The final portfolio pushes VDE to 30% and GLD to 35%, using the vol budget almost entirely -- landing at 19.98% weighted vol, just 0.02% under the constraint.

The tradeoff: dividend yield collapses to 0.90% because GLD and GSG pay nothing, and VGT pays almost nothing.

### Income Strategy (Maximize Dividend Yield)

**Key insight:** HYG (5.88% yield) and EMB (5.11%) are the yield powerhouses with tolerable volatility. The alternatives group has strong yielders too -- VNQI (4.87%) and VNQ (3.93%) -- but they consume the 3-alternative-ETF cap.

I loaded HYG at 40% and EMB at 20%, then filled with VNQI/VNQ/DBA from alternatives and VGSH for stability. This pushes yield above 5% at the cost of return collapsing to 2.81% -- barely above inflation.

### Safety Strategy (Minimize Volatility)

**Key insight:** VGSH at 2.20% vol is in a league of its own. The next three (BND 6.51%, TIP 6.63%, HYG 7.89%) are all bonds. An all-bond portfolio with heavy short-treasury weighting drives vol to ~4.5%.

I used the minimum 4 holdings to maximize concentration in the lowest-vol assets. More holdings would mean adding higher-vol ETFs. The yield is a pleasant side effect at 4.04% -- short treasuries and bonds pay well in this rate environment.

### Balanced Strategy (Moderate All Three)

**Key insight:** The three objectives conflict. GLD/VDE drive return but kill yield. HYG/VNQI drive yield but kill return. VGSH drives safety but kills return. A balanced portfolio needs a bit of each.

I anchored on VOO (25%) for solid return with moderate vol, added GLD (15%) for return boost, SCHD (15%) for yield-with-return, HYG (15%) for high yield at low vol, VEA (10%) for international diversification, DBA (10%) for an alternative with decent yield and low vol, and VGSH (10%) for stability. The result lands in the middle on all three metrics.

---

## 2. Curated Strategies

### Allocations

| Ticker | Growth | Balanced | Income | Safety |
|--------|--------|----------|--------|--------|
| VOO    | 15%    | 25%      |        |        |
| VTV    |        |          |        |        |
| VUG    |        |          |        |        |
| SCHD   |        | 15%      |        |        |
| VEA    |        | 10%      |        |        |
| VGT    | 10%    |          |        |        |
| VDE    | 30%    |          |        |        |
| GLD    | 35%    | 15%      |        |        |
| GSG    | 10%    |          |        |        |
| DBA    |        | 10%      | 5%     |        |
| HYG    |        | 15%      | 40%    | 10%    |
| EMB    |        |          | 20%    |        |
| VNQI   |        |          | 15%    |        |
| VNQ    |        |          | 10%    |        |
| VGSH   |        | 10%      | 10%    | 50%    |
| BND    |        |          |        | 20%    |
| TIP    |        |          |        | 20%    |
| **Sum**| **100%** | **100%** | **100%** | **100%** |

### Weighted-Average Metrics

| Metric                    | Growth | Balanced | Income | Safety |
|---------------------------|--------|----------|--------|--------|
| Ann. Return (5yr)         | 18.58% | 9.82%    | 2.81%  | 1.56%  |
| Ann. Volatility (5yr)     | 19.98% | 12.90%   | 10.78% | 4.52%  |
| Dividend Yield            | 0.90%  | 2.72%    | 5.06%  | 4.04%  |
| Holdings                  | 5      | 7        | 6      | 4      |
| Sector ETFs held          | 2      | 0        | 0      | 0      |
| Alternative ETFs held     | 2      | 2        | 3      | 0      |

### Constraint Verification

| Constraint                         | Growth | Balanced | Income | Safety |
|------------------------------------|--------|----------|--------|--------|
| Weighted vol <= 20%                | 19.98  | 12.90    | 10.78  | 4.52   |
| Sector ETFs <= 3                   | 2      | 0        | 0      | 0      |
| Alternative ETFs <= 3              | 2      | 2        | 3      | 0      |
| Holdings 4-12                      | 5      | 7        | 6      | 4      |
| Min allocation >= 1%               | 10%    | 10%      | 5%     | 10%    |
| Sum = 100%                         | 100    | 100      | 100    | 100    |

All constraints satisfied across all four strategies.

---

## 3. Solution Interpretation

Here are four portfolio strategies built from the same 30-ETF universe, each pushing a different objective as far as the constraints allow. The point is not to pick one -- it is to see what you are trading away for what you are getting.

### The extremes reveal the cost of each objective

**Growth (18.58% return, 0.90% yield, 19.98% vol)** concentrates 65% of capital in just two assets -- gold and energy -- and rides the volatility constraint right to its 20% ceiling. This portfolio earned the highest returns over the past 5 years, but it pays almost nothing in dividends and would have delivered stomach-churning drawdowns along the way. It is a bet that the commodity/energy/tech supercycle continues.

**Safety (1.56% return, 4.04% yield, 4.52% vol)** is the mirror image: half the portfolio sits in short-term treasuries. Volatility drops to under 5%, but annualized returns barely keep pace with inflation. This is a parking lot for capital, not a growth engine. The 4% yield is the main source of real return.

### The tradeoff between return and yield is the sharpest tension

Moving from Growth to Income, you gain 4.16 percentage points of dividend yield but surrender 15.77 percentage points of total return. This is not a gentle slope -- yield-oriented assets (HYG, EMB, VNQI) have delivered low or negative capital appreciation over the past 5 years. The income portfolio's 5.06% yield sounds attractive until you note its 2.81% total return means capital was actually shrinking in real terms.

### The balanced portfolio is a compromise, not an optimization

**Balanced (9.82% return, 2.72% yield, 12.90% vol)** sits in the middle on every metric without excelling at any. It holds 7 ETFs spanning US equity, international equity, bonds, gold, and agriculture. It gives up about 9 percentage points of return versus Growth in exchange for 7 points less volatility and nearly 2 points more yield. Whether that tradeoff is worth it depends entirely on your time horizon, income needs, and tolerance for watching your portfolio swing 20% in a bad quarter.

### What draws you in?

- If you want to accumulate wealth over a long horizon and can stomach sharp drops, the Growth end of this spectrum is where the action is -- though it is uncomfortably concentrated.
- If you need current income and capital preservation matters more than growth, the Income portfolio delivers 5%+ yield with moderate volatility -- but your purchasing power may erode.
- If volatility keeps you up at night, Safety turns the dial all the way down -- at the cost of almost no real growth.
- If none of those feel right, Balanced is the default middle ground, but "moderate everything" can also mean "exciting at nothing."

The question is not which portfolio is correct. It is which tradeoff you can live with for the next 5-10 years.

---

## 4. Limitations

### What I actually evaluated vs. what exists

The 30-ETF universe with integer percentage allocations and 4-12 holdings creates a combinatorial space on the order of trillions of possible portfolios. I evaluated approximately 40-50 candidate allocations by hand, iterating from greedy starting points. I have no guarantee that any of these four portfolios is globally optimal for its stated objective. A solver exploring the full space would almost certainly find allocations that dominate mine on one or more metrics.

### Where I used intuition vs. math

- **Selection of candidate ETFs:** Pure intuition. I sorted by each metric and picked obvious candidates. I may have overlooked non-obvious combinations (e.g., a mix of mid-cap and emerging market ETFs that happens to produce an efficient frontier point I did not consider).
- **Allocation percentages:** Trial-and-error arithmetic. For Growth, I systematically pushed the vol constraint to its limit, which gives some confidence. For the other three, I converged on "good enough" allocations without exhaustive search.
- **Weighted-average volatility as a risk measure:** The problem defines risk as weighted-average volatility, which ignores correlations. A portfolio of uncorrelated assets with 20% individual vol has much lower portfolio vol than 20%. My allocations optimize for the problem as stated, but a real investor would want correlation-adjusted risk.

### Portfolios that might be dominated

- **Income** is the most suspect. VNQI has -0.58% return and 18.22% volatility -- it is a yield trap that drags down both return and risk-adjusted performance. A solver might find a way to achieve similar yield without that anchor.
- **Balanced** uses 10 percentage point weights somewhat arbitrarily. Small reallocations (e.g., shifting 5% from VEA to GLD) could improve return without meaningfully changing vol or yield.
- **Safety** is likely close to optimal given the dominance of VGSH's volatility advantage. The main question is whether adding a 5th holding with slightly higher vol but meaningfully higher return would improve the risk-return tradeoff.

### What this exercise demonstrates

An LLM can construct feasible, constraint-satisfying portfolios through reasoning alone, and the Growth portfolio's 18.58% return at 19.98% vol suggests the heuristic search found a competitive solution in at least one case. But "competitive" is not "optimal," and the honest answer is: I do not know how far these portfolios are from the true efficient frontier of this problem.

---

## 5. Raw Solutions

```json
{
  "solutions": [
    {
      "name": "Growth",
      "allocations": {"GLD": 35, "VDE": 30, "VOO": 15, "VGT": 10, "GSG": 10},
      "return": 18.58,
      "vol": 19.98,
      "yield": 0.90
    },
    {
      "name": "Balanced",
      "allocations": {"VOO": 25, "GLD": 15, "SCHD": 15, "HYG": 15, "VEA": 10, "DBA": 10, "VGSH": 10},
      "return": 9.82,
      "vol": 12.90,
      "yield": 2.72
    },
    {
      "name": "Income",
      "allocations": {"HYG": 40, "EMB": 20, "VNQI": 15, "VGSH": 10, "VNQ": 10, "DBA": 5},
      "return": 2.81,
      "vol": 10.78,
      "yield": 5.06
    },
    {
      "name": "Safety",
      "allocations": {"VGSH": 50, "BND": 20, "TIP": 20, "HYG": 10},
      "return": 1.56,
      "vol": 4.52,
      "yield": 4.04
    }
  ]
}
```

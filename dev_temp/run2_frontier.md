# ETF Portfolio Allocation — Frontier Run 2

**Date:** 2026-04-13
**Problem:** 30 ETFs, 3 objectives, proportional allocation
**Problem ID:** `df5661c4-12b0-4305-902c-eb55c50134d7`
**Run ID:** `2f9a31a4-7363-435d-935a-9d5dfb49f089`

---

## 1. Execution Log

| Step | Action | Skill Guidance Received |
|------|--------|------------------------|
| 1 | Read JSON data file (30 ETFs, 5 groups) | N/A |
| 2 | `model create` — name="ETF Portfolio 30", domain="Investment Portfolio", approach="proportional", 3 objectives, 30 options (string shorthand) | `data_collection` — "Problem created. Use this guide when entering scores — it covers anchoring, batch efficiency, and completeness." |
| 3 | `model update` — 90 scores (30 ETFs x 3 objectives), all entered in a single batch call | `optimization_strategy` — "Score matrix is 100% complete. Use this guide before running solve — it covers mode selection, constraint strategy, and iteration expectations." |
| 4 | `model update` — 4 constraints (objective_bound on Volatility max 20, two group_limits on Sectors max 3 and Alternatives max 3, cardinality min 4 max 12) | No skill guidance (already provided optimization_strategy) |
| 5 | `solve run` mode="fast" | `solution_interpreter` — "Optimization complete. Use this guide to present results — never say 'best', start with extremes and balanced, quantify tradeoffs." |
| 6 | `explore tradeoffs` | No additional skill guidance |
| 7 | `explore compare` — solutions 1, 182, 153, 97 (extremes + balanced) | No additional skill guidance |
| 8 | `explore curate` — 4 strategies: Growth (sol 1), Balanced (sol 97), Income (sol 153), Safety (sol 182) | No additional skill guidance |

**Skill guidance pattern:** The system provides contextual skill guidance at each workflow transition — after model creation (data_collection), after score completion (optimization_strategy), and after solving (solution_interpreter). Subsequent calls within the same phase do not re-trigger guidance.

---

## 2. Results Summary

### Pareto Frontier

- **Total solutions:** 182
- **Algorithm:** NSGA-II (3 objectives)
- **Mode:** fast

### Objective Ranges

| Objective | Direction | Min | Max | Range |
|-----------|-----------|-----|-----|-------|
| Expected Return (%) | maximize | 2.31 | 19.01 | 16.70 |
| Volatility (%) | minimize | 3.06 | 18.76 | 15.70 |
| Dividend Yield (%) | maximize | 0.26 | 5.50 | 5.24 |

### Correlations (across Pareto frontier)

| Pair | Correlation | Interpretation |
|------|-------------|----------------|
| Return vs Volatility | r = +0.95 | Very strong positive — higher returns require accepting more volatility |
| Return vs Yield | r = -0.94 | Very strong negative — growth-oriented portfolios sacrifice income |
| Volatility vs Yield | r = -0.79 | Strong negative — income-focused portfolios tend to be less volatile |

### Shared Option

- **HYG** (High Yield Bond) appears in all 4 curated strategies — it is the one ETF the optimizer finds universally useful across the tradeoff space.

---

## 3. Curated Strategies Table

### Objective Values

| Strategy | Expected Return (%) | Volatility (%) | Dividend Yield (%) |
|----------|--------------------:|---------------:|-------------------:|
| **Growth** (Sol 1) | 19.01 | 17.56 | 0.70 |
| **Balanced** (Sol 97) | 9.89 | 11.07 | 3.52 |
| **Income** (Sol 153) | 4.27 | 8.46 | 5.50 |
| **Safety** (Sol 182) | 2.31 | 3.06 | 3.91 |

### Allocations (%)

| ETF | Growth | Balanced | Income | Safety |
|-----|-------:|---------:|-------:|-------:|
| GLD | 76 | 36 | — | — |
| VGSH | — | 3 | 4 | 94 |
| HYG | 1 | 56 | 86 | 3 |
| VDE | 18 | — | 1 | — |
| EMB | — | 2 | 3 | — |
| IGF | — | 1 | 1 | 2 |
| VOO | 1 | 1 | 1 | — |
| SCHD | 1 | — | 1 | 1 |
| VTV | 1 | — | — | — |
| TIP | 1 | 1 | — | — |
| VEA | — | — | 2 | — |
| DBA | 1 | — | 1 | — |
| **Holdings** | **8** | **7** | **9** | **4** |

### Strategy Signatures

| Strategy | Content Signature | Dominant Holding |
|----------|------------------|-----------------|
| Growth | `4b684555cd65` | GLD (76%) + VDE (18%) |
| Balanced | `86489439ffc9` | HYG (56%) + GLD (36%) |
| Income | `0ac294ddbeaa` | HYG (86%) |
| Safety | `f0318faf42dc` | VGSH (94%) |

---

## 4. Solution Interpretation

Here is how the tradeoff space breaks down across these four strategies.

**Growth** pushes for maximum capital appreciation at 19.0% annualized return, driven by a 76% allocation to gold (GLD) and 18% to energy (VDE) — two of the strongest performers over the past five years. The cost is clear: volatility climbs to 17.6%, and dividend yield drops to just 0.7%. This portfolio is a concentrated bet on commodity-linked returns.

**Safety** sits at the opposite extreme. With 94% in short-term treasuries (VGSH), volatility compresses to just 3.1% — but annualized return falls to 2.3%. Interestingly, the yield stays at 3.9% because VGSH itself pays a meaningful coupon. This is near-cash stability.

**Income** maximizes yield at 5.5% by concentrating 86% in high-yield bonds (HYG). Return drops to 4.3% and volatility sits at 8.5% — a moderate risk profile. This strategy accepts lower growth in exchange for the highest cash flow.

**Balanced** splits the difference: 56% HYG and 36% GLD produce 9.9% return at 11.1% volatility with 3.5% yield. No single objective dominates — all three are in the middle of their respective ranges.

### Tradeoff Quantification

- Moving from **Safety to Balanced**: gaining 7.6 percentage points of return costs 8.0 points of additional volatility — roughly 1:1.
- Moving from **Balanced to Growth**: gaining another 9.1 points of return costs 6.5 points of volatility but sacrifices 2.8 points of yield.
- Moving from **Balanced to Income**: gaining 2.0 points of yield costs 5.6 points of return but actually reduces volatility by 2.6 points — income and stability go together here.
- The **Safety-to-Income** move is notable: you add 5.4 points of volatility but gain 2.0 points of return and 1.6 points of yield — a relatively efficient trade.

### Structural Observations

The strong positive correlation between return and volatility (r=0.95) means there is no free lunch — the frontier does not offer high-return, low-volatility portfolios. The negative correlation between return and yield (r=-0.94) reveals that the highest-growth assets (GLD, VDE, VGT) pay little or no dividends, while the highest-yielding assets (HYG, VGLT, EMB) have low capital appreciation.

HYG appears in every curated strategy, suggesting high-yield bonds occupy a unique position in the tradeoff space — offering moderate returns with yield that no equity or commodity can match at similar volatility.

### What draws your attention?

Each of these strategies is optimal at its particular tradeoff — none dominates another. The question is which tradeoff you are willing to make:

- Do you prioritize capital growth and accept the ride? (Growth)
- Do you want income above all else? (Income)
- Is stability the priority, even at the cost of returns below inflation? (Safety)
- Or does a middle path that balances all three resonate? (Balanced)

There are also 178 other Pareto-optimal portfolios between these anchors — if you lean toward one direction but want to moderate it, we can explore the gradations.

---

## 5. Raw Data for Plotting

```json
{"solutions": [{"return": 19.0056, "vol": 17.5606, "yield": 0.7003}, {"return": 18.9716, "vol": 17.3002, "yield": 0.6406}, {"return": 18.8864, "vol": 17.8619, "yield": 0.709}, {"return": 18.84, "vol": 15.8066, "yield": 0.2596}, {"return": 18.702, "vol": 15.591, "yield": 0.3317}, {"return": 18.6622, "vol": 16.5935, "yield": 0.5795}, {"return": 18.5299, "vol": 17.9593, "yield": 1.0322}, {"return": 18.4961, "vol": 15.5592, "yield": 0.357}, {"return": 18.388, "vol": 18.2697, "yield": 1.1151}, {"return": 18.3378, "vol": 17.422, "yield": 0.7847}, {"return": 18.2613, "vol": 18.3096, "yield": 1.1283}, {"return": 18.2051, "vol": 15.8158, "yield": 0.5353}, {"return": 18.1893, "vol": 18.4628, "yield": 1.2239}, {"return": 18.1587, "vol": 17.1526, "yield": 0.9051}, {"return": 17.979, "vol": 16.8403, "yield": 0.9944}, {"return": 17.9296, "vol": 15.7297, "yield": 0.4171}, {"return": 17.915, "vol": 15.4174, "yield": 0.617}, {"return": 17.907, "vol": 16.8197, "yield": 0.9233}, {"return": 17.8443, "vol": 15.2609, "yield": 0.4699}, {"return": 17.6773, "vol": 17.7178, "yield": 1.2052}, {"return": 17.6563, "vol": 16.0726, "yield": 0.861}, {"return": 17.5505, "vol": 15.1154, "yield": 0.7506}, {"return": 17.4085, "vol": 16.4418, "yield": 1.1886}, {"return": 17.4037, "vol": 16.2897, "yield": 1.1037}, {"return": 17.287, "vol": 17.0707, "yield": 1.193}, {"return": 17.232, "vol": 16.9607, "yield": 1.266}, {"return": 17.147, "vol": 15.477, "yield": 0.8281}, {"return": 17.0425, "vol": 16.2319, "yield": 1.2406}, {"return": 16.9378, "vol": 18.7586, "yield": 1.725}, {"return": 16.7916, "vol": 14.9367, "yield": 0.9815}, {"return": 16.6922, "vol": 16.6063, "yield": 1.3097}, {"return": 16.4899, "vol": 16.4035, "yield": 1.6524}, {"return": 16.366, "vol": 14.7459, "yield": 1.1525}, {"return": 16.2745, "vol": 17.455, "yield": 1.7885}, {"return": 16.1367, "vol": 14.5625, "yield": 1.0442}, {"return": 15.8056, "vol": 14.381, "yield": 1.3148}, {"return": 15.7084, "vol": 14.9569, "yield": 1.5034}, {"return": 15.68, "vol": 14.87, "yield": 1.53}, {"return": 15.5184, "vol": 14.8102, "yield": 1.4496}, {"return": 15.4795, "vol": 14.6762, "yield": 1.3354}, {"return": 15.452, "vol": 14.8765, "yield": 1.6219}, {"return": 15.3426, "vol": 14.0226, "yield": 1.4298}, {"return": 15.1387, "vol": 14.4722, "yield": 1.4487}, {"return": 15.1075, "vol": 12.8136, "yield": 1.0748}, {"return": 15.033, "vol": 14.0131, "yield": 1.6033}, {"return": 14.8837, "vol": 17.4796, "yield": 2.3172}, {"return": 14.847, "vol": 13.0227, "yield": 1.2562}, {"return": 14.8353, "vol": 15.6797, "yield": 2.1274}, {"return": 14.7092, "vol": 14.1466, "yield": 1.7581}, {"return": 14.598, "vol": 14.1883, "yield": 1.9016}, {"return": 14.5372, "vol": 13.1938, "yield": 1.3731}, {"return": 14.4869, "vol": 14.3943, "yield": 1.9584}, {"return": 14.387, "vol": 15.6898, "yield": 2.2996}, {"return": 14.3137, "vol": 15.93, "yield": 2.4951}, {"return": 14.3002, "vol": 14.4986, "yield": 2.0094}, {"return": 14.1213, "vol": 13.7277, "yield": 1.9307}, {"return": 13.9845, "vol": 13.2824, "yield": 1.6988}, {"return": 13.9025, "vol": 12.0774, "yield": 1.2964}, {"return": 13.7418, "vol": 13.2485, "yield": 2.1426}, {"return": 13.6612, "vol": 13.4155, "yield": 2.1531}, {"return": 13.6371, "vol": 12.1889, "yield": 1.5625}, {"return": 13.5492, "vol": 15.1943, "yield": 2.5746}, {"return": 13.437, "vol": 11.6315, "yield": 1.5112}, {"return": 13.3248, "vol": 14.8042, "yield": 2.2542}, {"return": 13.1928, "vol": 13.5363, "yield": 2.4551}, {"return": 13.1641, "vol": 12.1388, "yield": 1.7754}, {"return": 12.9563, "vol": 12.4304, "yield": 1.8748}, {"return": 12.9078, "vol": 12.3428, "yield": 1.8399}, {"return": 12.7439, "vol": 11.3608, "yield": 1.8101}, {"return": 12.6742, "vol": 13.3067, "yield": 2.3573}, {"return": 12.5965, "vol": 11.6105, "yield": 1.8562}, {"return": 12.4806, "vol": 12.0693, "yield": 2.0767}, {"return": 12.414, "vol": 13.8256, "yield": 2.6487}, {"return": 12.2921, "vol": 12.4647, "yield": 2.5262}, {"return": 12.2493, "vol": 13.9103, "yield": 3.0393}, {"return": 12.0604, "vol": 13.9224, "yield": 3.0716}, {"return": 12.0597, "vol": 12.2719, "yield": 2.198}, {"return": 11.9134, "vol": 11.7554, "yield": 2.403}, {"return": 11.8366, "vol": 12.3771, "yield": 2.8159}, {"return": 11.7925, "vol": 13.9587, "yield": 3.1637}, {"return": 11.6855, "vol": 11.7401, "yield": 2.5932}, {"return": 11.6356, "vol": 11.9933, "yield": 2.8393}, {"return": 11.4668, "vol": 10.3407, "yield": 2.1046}, {"return": 11.2898, "vol": 11.2835, "yield": 2.374}, {"return": 11.1836, "vol": 11.4188, "yield": 2.614}, {"return": 11.1682, "vol": 12.7836, "yield": 3.3446}, {"return": 11.0321, "vol": 11.1933, "yield": 2.6989}, {"return": 10.8732, "vol": 12.6562, "yield": 3.1816}, {"return": 10.7481, "vol": 9.5962, "yield": 2.0403}, {"return": 10.5825, "vol": 9.9501, "yield": 2.2442}, {"return": 10.4649, "vol": 10.8526, "yield": 2.7766}, {"return": 10.4053, "vol": 11.382, "yield": 3.3091}, {"return": 10.3004, "vol": 12.6977, "yield": 3.4296}, {"return": 10.2273, "vol": 10.778, "yield": 2.8526}, {"return": 10.0727, "vol": 10.2171, "yield": 2.7236}, {"return": 10.0101, "vol": 9.5278, "yield": 2.429}, {"return": 9.8857, "vol": 11.0682, "yield": 3.516}, {"return": 9.689, "vol": 10.9735, "yield": 3.4115}, {"return": 9.5781, "vol": 10.7578, "yield": 3.4978}, {"return": 9.4296, "vol": 9.6464, "yield": 2.7091}, {"return": 9.3918, "vol": 10.0426, "yield": 2.8334}, {"return": 9.3189, "vol": 13.6781, "yield": 4.4892}, {"return": 9.2684, "vol": 10.1163, "yield": 2.8936}, {"return": 9.2056, "vol": 9.8937, "yield": 2.9227}, {"return": 9.1163, "vol": 8.7903, "yield": 2.7478}, {"return": 9.0408, "vol": 12.9101, "yield": 3.8159}, {"return": 8.9863, "vol": 12.8737, "yield": 3.8128}, {"return": 8.8091, "vol": 10.6787, "yield": 3.7196}, {"return": 8.7309, "vol": 10.4605, "yield": 3.7764}, {"return": 8.687, "vol": 10.2503, "yield": 3.6912}, {"return": 8.5998, "vol": 7.7347, "yield": 2.5121}, {"return": 8.4738, "vol": 9.3652, "yield": 3.0531}, {"return": 8.3345, "vol": 8.8823, "yield": 2.9985}, {"return": 8.26, "vol": 8.3044, "yield": 2.6277}, {"return": 8.2267, "vol": 8.871, "yield": 3.0258}, {"return": 8.1085, "vol": 11.1785, "yield": 4.165}, {"return": 7.9283, "vol": 8.4855, "yield": 3.2119}, {"return": 7.8518, "vol": 11.853, "yield": 4.6138}, {"return": 7.5081, "vol": 11.5606, "yield": 4.2946}, {"return": 7.4397, "vol": 10.6556, "yield": 4.3423}, {"return": 7.329, "vol": 11.4746, "yield": 4.4636}, {"return": 7.114, "vol": 9.139, "yield": 3.8902}, {"return": 6.8486, "vol": 8.6304, "yield": 3.58}, {"return": 6.7994, "vol": 10.5831, "yield": 4.5424}, {"return": 6.7186, "vol": 7.868, "yield": 3.6256}, {"return": 6.6024, "vol": 9.2944, "yield": 4.2115}, {"return": 6.493, "vol": 6.9954, "yield": 3.276}, {"return": 6.4353, "vol": 7.1058, "yield": 3.2806}, {"return": 6.3719, "vol": 8.1371, "yield": 3.8372}, {"return": 6.2359, "vol": 10.1423, "yield": 5.0075}, {"return": 6.1816, "vol": 8.1815, "yield": 3.9673}, {"return": 6.1387, "vol": 7.899, "yield": 4.0203}, {"return": 6.104, "vol": 7.1481, "yield": 3.4613}, {"return": 6.0312, "vol": 7.2375, "yield": 3.5968}, {"return": 5.837, "vol": 9.584, "yield": 4.6107}, {"return": 5.7576, "vol": 7.3221, "yield": 4.0997}, {"return": 5.6811, "vol": 9.7902, "yield": 5.035}, {"return": 5.5938, "vol": 6.8301, "yield": 3.7165}, {"return": 5.5806, "vol": 9.3925, "yield": 4.9449}, {"return": 5.4878, "vol": 9.178, "yield": 4.2909}, {"return": 5.3165, "vol": 9.3045, "yield": 4.8042}, {"return": 5.3084, "vol": 9.1473, "yield": 5.1787}, {"return": 5.1533, "vol": 7.8395, "yield": 4.2616}, {"return": 5.1124, "vol": 8.8924, "yield": 5.2731}, {"return": 5.0777, "vol": 6.6005, "yield": 3.6674}, {"return": 4.9741, "vol": 8.9269, "yield": 5.3308}, {"return": 4.9381, "vol": 6.4312, "yield": 4.0803}, {"return": 4.8878, "vol": 8.2421, "yield": 4.7707}, {"return": 4.6425, "vol": 8.6927, "yield": 5.3522}, {"return": 4.4939, "vol": 8.5564, "yield": 5.3841}, {"return": 4.3265, "vol": 8.4283, "yield": 5.4158}, {"return": 4.3224, "vol": 8.585, "yield": 5.463}, {"return": 4.2678, "vol": 8.4637, "yield": 5.5013}, {"return": 4.2042, "vol": 7.7147, "yield": 4.8782}, {"return": 4.1286, "vol": 6.7434, "yield": 4.5513}, {"return": 4.0766, "vol": 7.5157, "yield": 5.0387}, {"return": 4.0411, "vol": 6.0262, "yield": 4.326}, {"return": 3.9972, "vol": 5.4308, "yield": 3.8906}, {"return": 3.9905, "vol": 7.3829, "yield": 5.0651}, {"return": 3.95, "vol": 6.3653, "yield": 4.6425}, {"return": 3.9438, "vol": 6.2054, "yield": 4.5566}, {"return": 3.9194, "vol": 5.5786, "yield": 4.0712}, {"return": 3.8091, "vol": 6.9291, "yield": 4.9662}, {"return": 3.7575, "vol": 5.3386, "yield": 4.0349}, {"return": 3.6287, "vol": 6.244, "yield": 4.7198}, {"return": 3.6014, "vol": 6.1254, "yield": 4.6702}, {"return": 3.5318, "vol": 5.1779, "yield": 4.1529}, {"return": 3.4352, "vol": 4.9621, "yield": 4.1289}, {"return": 3.3964, "vol": 5.7638, "yield": 4.6987}, {"return": 3.3802, "vol": 5.6808, "yield": 4.7108}, {"return": 3.1721, "vol": 4.6866, "yield": 4.2168}, {"return": 3.151, "vol": 5.0852, "yield": 4.4136}, {"return": 3.1111, "vol": 5.0432, "yield": 4.4126}, {"return": 2.9746, "vol": 4.4588, "yield": 4.1351}, {"return": 2.9257, "vol": 4.1248, "yield": 4.0562}, {"return": 2.8091, "vol": 4.3389, "yield": 4.1906}, {"return": 2.7076, "vol": 3.7449, "yield": 3.7994}, {"return": 2.582, "vol": 3.6865, "yield": 3.8445}, {"return": 2.5146, "vol": 3.5275, "yield": 3.8812}, {"return": 2.4141, "vol": 3.356, "yield": 3.927}, {"return": 2.3778, "vol": 3.1455, "yield": 3.9069}, {"return": 2.3102, "vol": 3.055, "yield": 3.914}]}
```

# Portfolio Optimization: Cross-Scenario Analysis and Interpretation

## Executive Summary

Across 4 macroeconomic scenarios, the optimizer generated 1,200 Pareto-optimal portfolios (300 per scenario). The analysis reveals a clear set of all-weather portfolio building blocks and distinct scenario-specific tilts.

**Key finding:** No single ETF appears in >50% of solutions across ALL scenarios (no "core" tier). However, HYG, GLD, and DBA form the closest thing to an all-weather backbone, appearing frequently across all scenarios but with varying intensity.

## Robustness Analysis

### All-Weather Building Blocks (Common Tier: >25% average frequency)

| ETF | Avg Freq | Min Freq | Role |
|-----|----------|----------|------|
| HYG | 66.7% | 48.0% | Yield anchor across all scenarios |
| GLD | 64.6% | 39.0% | Return driver + inflation/recession hedge |
| DBA | 59.5% | 9.0% | Commodity diversifier, inflation hedge |
| VDE | 50.8% | 1.3% | High-return equity, energy exposure |
| VGSH | 48.1% | 26.7% | Safety anchor, low-vol foundation |
| VGLT | 32.5% | 0.3% | Duration play, recession hedge |
| EWJ | 30.4% | 2.7% | International yield, rate-cuts play |
| VGT | 28.6% | 0.7% | Growth/tech, rate-cuts beneficiary |

### Scenario-Specific ETFs

| ETF | Scenario | Frequency | Why |
|-----|----------|-----------|-----|
| BND | Recession | 64.0% | Override to 5.0% return makes it attractive |
| VGLT | Recession | 81.3% | Override to 7.0% return; highest freq in any scenario |
| DBA | Inflation | 92.0% | 2x return multiplier; highest freq in any scenario |
| EWJ | Rate Cuts | 77.0% | 1.5x equity return + 4.3% yield + 0.8x vol |

### Scenario Regime Signatures

**Base Case:** Commodity-equity-yield blend. VDE/GLD/DBA/HYG form the backbone.

**Rate Cuts:** Equity rotation. EWJ/VGT/VDE surge. VGLT rallies to 10%. Bond yields halve, pushing income toward equities.

**Recession:** Flight to quality. VGLT/VGSH/BND dominate. GLD as safe haven. Equities nearly absent. The only scenario where growth portfolios contain zero equity.

**Inflation:** Commodity supercycle. DBA/GLD/GSG/VDE dominate. TIPS rise but bonds collapse. Highest achievable returns (33.5%) and highest yields (6.3%).

## Cross-Scenario Strategy Comparison

### Growth Strategy Across Scenarios

| Scenario | Return | Vol | Holdings |
|----------|--------|-----|----------|
| Base | 19.0% | 15.9% | VDE, GLD, VGT, GSG |
| Rate Cuts | 25.8% | 16.0% | VGT, VDE, GLD, VOO, VUG |
| Recession | 12.7% | 10.4% | VGLT, GLD, GSG, VGSH, IGF, BND |
| Inflation | 33.5% | 15.7% | VDE, GLD, GSG, DBA |

Growth portfolios pivot dramatically: equities in base/rate-cuts, treasuries+gold in recession, pure commodities in inflation. GLD appears in all 4, making it the single most robust growth holding.

### Safety Strategy Across Scenarios

| Scenario | Return | Vol | Holdings |
|----------|--------|-----|----------|
| Base | 2.4% | 2.7% | VGSH, HYG, DBA, EWJ |
| Rate Cuts | 2.4% | 2.6% | VGSH, HYG, VO, DBA |
| Recession | 1.9% | 2.4% | VGSH, BND, TIP, VNQI |
| Inflation | 1.4% | 2.7% | VGSH, HYG, VEA, DBA |

Safety portfolios are remarkably consistent: VGSH anchors all 4 at 30%. Vol stays in the 2.4-2.7% band regardless of scenario. The trade-off: returns are compressed (1.4-2.4%).

### Balanced Strategy Across Scenarios

| Scenario | Return | Vol | Yield | Holdings |
|----------|--------|-----|-------|----------|
| Base | 9.3% | 6.6% | 3.5% | HYG, DBA, VGSH, GLD, VDE |
| Rate Cuts | 12.1% | 8.8% | 3.0% | EWJ, VGLT, HYG, VDE, VPU, VTV, VDC |
| Recession | 4.8% | 4.4% | 4.0% | VGSH, HYG, GLD, VGLT |
| Inflation | 16.4% | 7.5% | 4.0% | HYG, DBA, GLD, VGSH, VDE |

Balanced portfolios show the clearest regime-dependent behavior. HYG appears in all 4 as the yield-vol compromise anchor.

## Practical Implications

### Probability-Weighted Expected Outcomes

Using scenario probabilities (Base 30%, Rate Cuts 25%, Recession 20%, Inflation 25%):

**Balanced strategy expected return:** 0.30 * 9.33 + 0.25 * 12.05 + 0.20 * 4.78 + 0.25 * 16.40 = **10.87%**

**Balanced strategy expected vol:** ~6.0-7.5% range across scenarios

### Portfolio Construction Recommendations

1. **All-weather core (60-70%):** VGSH + HYG + GLD + DBA. These four appear consistently and provide safety, yield, and inflation hedging.

2. **Scenario tilts (30-40%):**
   - If rates cut: add EWJ, VGT, VGLT
   - If recession: increase VGLT, add BND, reduce equity
   - If inflation: increase DBA, add VDE/GSG, reduce bonds
   - If continuation: maintain VDE, VGT exposure

3. **Avoid in most scenarios:** MCHI, VOX, VHT, VB, VO have minimal presence across all scenarios. Their risk-return profiles are dominated by better alternatives.

### Key Trade-offs

- **Return vs. Safety:** The frontier spans from ~2% return / ~2.5% vol to ~19-34% return / ~16% vol depending on scenario. The jump from safety to balanced captures most of the return with moderate vol increase.

- **Yield vs. Return:** Income-maximizing portfolios sacrifice 70-80% of achievable return. The balanced strategy captures 3-4% yield without extreme return sacrifice.

- **Robustness vs. Optimality:** A portfolio optimized for one scenario may perform poorly in others. The balanced curated strategies show the best cross-scenario consistency.

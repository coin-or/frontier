# LLM-Only Scenario Portfolio Optimization

## 1. Approach

I tackled this problem through pure reasoning without any optimization solver, calculator, or code execution. My method:

1. **Computed adjusted scores** for each of the 4 scenarios by applying the multipliers and overrides specified in the assignment to each ETF's base-case return, volatility, and yield.
2. **Ranked ETFs** within each scenario by return-to-volatility ratio (a rough Sharpe-like measure), yield, and absolute return to identify candidates for each strategy.
3. **Constructed portfolios** for each strategy (Growth, Balanced, Income, Safety) by selecting 4-12 ETFs that best serve the strategy's objective while satisfying constraints (vol <= 20%, max 3 Sectors, max 3 Alternatives).
4. **Verified constraints** by computing weighted-average metrics using mental arithmetic (showing the work).
5. **Compared across scenarios** to identify robust and scenario-specific holdings.

Key heuristic: I used a "core + satellite" approach -- anchor each portfolio around the strongest candidates, then fill in with complementary ETFs that either boost the target metric or reduce risk.

---

## 2. Adjusted Scores

### Scenario 1: Base Case (no changes)

| Ticker | Group | Return (%) | Vol (%) | Yield (%) | Ret/Vol |
|--------|-------|-----------|---------|-----------|---------|
| VOO | US Eq | 11.98 | 15.63 | 1.19 | 0.77 |
| VUG | US Eq | 12.23 | 19.84 | 0.46 | 0.62 |
| VTV | US Eq | 10.35 | 14.46 | 2.02 | 0.72 |
| SCHD | US Eq | 7.45 | 15.35 | 3.44 | 0.49 |
| VEA | Intl Eq | 8.82 | 16.76 | 2.94 | 0.53 |
| EWJ | Intl Eq | 7.78 | 15.64 | 4.33 | 0.50 |
| BND | Bonds | 0.23 | 6.51 | 3.91 | 0.04 |
| VGSH | Bonds | 1.83 | 2.20 | 3.95 | 0.83 |
| HYG | Bonds | 3.91 | 7.89 | 5.88 | 0.50 |
| VGT | Sectors | 16.19 | 21.47 | 0.44 | 0.75 |
| VDE | Sectors | 22.08 | 26.59 | 2.27 | 0.83 |
| VPU | Sectors | 10.60 | 16.83 | 2.57 | 0.63 |
| VDC | Sectors | 6.52 | 13.92 | 2.15 | 0.47 |
| GLD | Alts | 19.88 | 15.91 | 0.00 | 1.25 |
| DBA | Alts | 10.71 | 12.20 | 3.35 | 0.88 |
| IGF | Alts | 11.11 | 15.32 | 2.96 | 0.73 |

Top return/vol ratios: GLD (1.25), DBA (0.88), VDE (0.83), VGSH (0.83), VOO (0.77), VGT (0.75), IGF (0.73).

### Scenario 2: Rate Cuts / Risk-On

Adjustments: Equity returns x1.3, equity vol x0.9, bond yields x0.7, VGLT return -> 8.0%

| Ticker | Group | Return (%) | Vol (%) | Yield (%) | Notes |
|--------|-------|-----------|---------|-----------|-------|
| VOO | US Eq | 15.57 | 14.07 | 1.19 | 11.98*1.3=15.574 |
| VUG | US Eq | 15.90 | 17.86 | 0.46 | 12.23*1.3=15.899 |
| VTV | US Eq | 13.46 | 13.01 | 2.02 | 10.35*1.3=13.455 |
| VO | US Eq | 8.74 | 15.43 | 1.51 | 6.72*1.3=8.736 |
| VB | US Eq | 7.75 | 17.15 | 1.34 | 5.96*1.3=7.748 |
| SCHD | US Eq | 9.69 | 13.82 | 3.44 | 7.45*1.3=9.685 |
| VEA | Intl Eq | 11.47 | 15.08 | 2.94 | 8.82*1.3=11.466 |
| VWO | Intl Eq | 5.84 | 13.84 | 2.71 | 4.49*1.3=5.837 |
| VGK | Intl Eq | 11.01 | 16.33 | 3.01 | 8.47*1.3=11.011 |
| EWJ | Intl Eq | 10.11 | 14.08 | 4.33 | 7.78*1.3=10.114 |
| MCHI | Intl Eq | -6.45 | 25.79 | 2.27 | -4.96*1.3=-6.448 |
| BND | Bonds | 0.23 | 6.51 | 2.74 | yield: 3.91*0.7=2.737 |
| VGSH | Bonds | 1.83 | 2.20 | 2.77 | yield: 3.95*0.7=2.765 |
| VGLT | Bonds | **8.00** | 13.82 | 3.14 | override; yield: 4.49*0.7=3.143 |
| TIP | Bonds | 1.06 | 6.63 | 2.42 | yield: 3.45*0.7=2.415 |
| HYG | Bonds | 3.91 | 7.89 | 4.12 | yield: 5.88*0.7=4.116 |
| EMB | Bonds | 1.85 | 10.46 | 3.58 | yield: 5.11*0.7=3.577 |
| VGT | Sectors | 16.19 | 21.47 | 0.44 | unchanged |
| VDE | Sectors | 22.08 | 26.59 | 2.27 | unchanged |
| GLD | Alts | 19.88 | 15.91 | 0.00 | unchanged |
| DBA | Alts | 10.71 | 12.20 | 3.35 | unchanged |
| IGF | Alts | 11.11 | 15.32 | 2.96 | unchanged |

Key changes: Equities become much more attractive (higher returns, lower vol). Bonds yields compress. VGLT becomes interesting with 8% return. Top candidates: VDE (22.08), GLD (19.88), VUG (15.90), VOO (15.57), VGT (16.19), VTV (13.46).

### Scenario 3: Recession / Risk-Off

Adjustments: Equity returns x0.4, equity vol x1.5, sector returns x0.4, sector vol x1.5, plus overrides for VGSH/BND/HYG/EMB.

| Ticker | Group | Return (%) | Vol (%) | Yield (%) | Notes |
|--------|-------|-----------|---------|-----------|-------|
| VOO | US Eq | 4.79 | 23.45 | 1.19 | 11.98*0.4=4.792; vol*1.5=23.445 |
| VUG | US Eq | 4.89 | 29.76 | 0.46 | |
| VTV | US Eq | 4.14 | 21.69 | 2.02 | |
| VO | US Eq | 2.69 | 25.71 | 1.51 | |
| VB | US Eq | 2.38 | 28.58 | 1.34 | |
| SCHD | US Eq | 2.98 | 23.03 | 3.44 | |
| VEA | Intl Eq | 3.53 | 25.14 | 2.94 | |
| VWO | Intl Eq | 1.80 | 23.07 | 2.71 | |
| VGK | Intl Eq | 3.39 | 27.21 | 3.01 | |
| EWJ | Intl Eq | 3.11 | 23.46 | 4.33 | |
| MCHI | Intl Eq | -1.98 | 42.98 | 2.27 | |
| BND | Bonds | **4.00** | 6.51 | 3.91 | override |
| VGSH | Bonds | **4.00** | 2.20 | 3.95 | override |
| VGLT | Bonds | -5.00 | 13.82 | 4.49 | unchanged |
| TIP | Bonds | 1.06 | 6.63 | 3.45 | unchanged |
| HYG | Bonds | **-2.00** | **10.30** | 5.88 | overrides (vol=7.89*1.3~10.26, assignment says 10.3) |
| EMB | Bonds | **-2.00** | **13.60** | 5.11 | overrides (vol=10.46*1.3~13.6) |
| VGT | Sectors | 6.48 | 32.21 | 0.44 | 16.19*0.4=6.476; vol*1.5=32.205 |
| VHT | Sectors | 1.70 | 22.25 | 1.72 | 4.24*0.4=1.696 |
| VDE | Sectors | 8.83 | 39.89 | 2.27 | 22.08*0.4=8.832 |
| VPU | Sectors | 4.24 | 25.25 | 2.57 | 10.60*0.4=4.24 |
| VDC | Sectors | 2.61 | 20.88 | 2.15 | |
| VFH | Sectors | 3.36 | 28.65 | 1.61 | |
| GLD | Alts | 19.88 | 15.91 | 0.00 | unchanged |
| DBA | Alts | 10.71 | 12.20 | 3.35 | unchanged |
| IGF | Alts | 11.11 | 15.32 | 2.96 | unchanged |
| VNQ | Alts | 2.39 | 19.67 | 3.93 | unchanged |

Key insight: Equities and sectors become terrible (low returns, very high vol). Bonds and alternatives dominate. VGSH is king: 4% return, 2.2% vol, 3.95% yield. GLD still strong. DBA and IGF remain solid.

### Scenario 4: Inflation Surge

Adjustments: Equity returns x0.8, bond yields x1.1, plus overrides for GLD/GSG/DBA/TIP/BND/VGLT.

| Ticker | Group | Return (%) | Vol (%) | Yield (%) | Notes |
|--------|-------|-----------|---------|-----------|-------|
| VOO | US Eq | 9.58 | 15.63 | 1.19 | 11.98*0.8=9.584 |
| VUG | US Eq | 9.78 | 19.84 | 0.46 | 12.23*0.8=9.784 |
| VTV | US Eq | 8.28 | 14.46 | 2.02 | 10.35*0.8=8.28 |
| VO | US Eq | 5.38 | 17.14 | 1.51 | |
| VB | US Eq | 4.77 | 19.05 | 1.34 | |
| SCHD | US Eq | 5.96 | 15.35 | 3.44 | 7.45*0.8=5.96 |
| VEA | Intl Eq | 7.06 | 16.76 | 2.94 | 8.82*0.8=7.056 |
| VWO | Intl Eq | 3.59 | 15.38 | 2.71 | |
| VGK | Intl Eq | 6.78 | 18.14 | 3.01 | |
| EWJ | Intl Eq | 6.22 | 15.64 | 4.33 | |
| MCHI | Intl Eq | -3.97 | 28.65 | 2.27 | |
| BND | Bonds | **-3.00** | 6.51 | 4.30 | override; yield: 3.91*1.1=4.301 |
| VGSH | Bonds | 1.83 | 2.20 | 4.35 | yield: 3.95*1.1=4.345 |
| VGLT | Bonds | **-8.00** | 13.82 | 4.94 | override; yield: 4.49*1.1=4.939 |
| TIP | Bonds | **6.00** | 6.63 | 3.80 | override; yield: 3.45*1.1=3.795 |
| HYG | Bonds | 3.91 | 7.89 | 6.47 | yield: 5.88*1.1=6.468 |
| EMB | Bonds | 1.85 | 10.46 | 5.62 | yield: 5.11*1.1=5.621 |
| VGT | Sectors | 16.19 | 21.47 | 0.44 | unchanged |
| VDE | Sectors | 22.08 | 26.59 | 2.27 | unchanged |
| VPU | Sectors | 10.60 | 16.83 | 2.57 | unchanged |
| GLD | Alts | **29.82** | 15.91 | 0.00 | override |
| GSG | Alts | **23.79** | 19.40 | 0.00 | override |
| DBA | Alts | **16.07** | 12.20 | 3.35 | override |
| IGF | Alts | 11.11 | 15.32 | 2.96 | unchanged |

Key insight: Commodities and gold dominate. GLD at 29.82% return with 15.91% vol is exceptional. TIP becomes valuable. Nominal bonds (BND, VGLT) are crushed.

---

## 3. Issues

1. **Arithmetic precision**: All multiplication was done mentally. I rounded to 2 decimal places but may have small errors (e.g., 8.82 * 1.3 = 11.466, I used 11.47). These errors are on the order of 0.01-0.05% and should not materially affect portfolio construction.

2. **Constraint verification difficulty**: Computing weighted averages across 4-12 holdings mentally is error-prone. I show my arithmetic but acknowledge I may have made carrying/addition errors, particularly for the volatility constraint which is critical.

3. **No correlation data**: Portfolio volatility is NOT the weighted average of individual volatilities -- it depends on correlations. The assignment uses weighted-average volatility as a simplified constraint, which I follow, but this overstates true portfolio risk for diversified portfolios.

4. **Solution space**: With 30 ETFs, integer percentages summing to 100, and 4-12 holdings, the feasible space is astronomically large. I am exploring maybe 4-5 candidates per strategy per scenario. A solver would evaluate thousands.

5. **Pareto optimality**: I cannot verify that my portfolios are actually Pareto-optimal. They are "reasonable" portfolios constructed from heuristic reasoning, but there almost certainly exist portfolios that dominate mine on at least one objective without sacrificing the others.

6. **Sector/Alternative constraints**: I need to track that at most 3 from each group are held. This is straightforward but easy to miss when constructing many portfolios quickly.

7. **Integer allocation**: Minimum 1% per holding, integers only, sum to 100%. This constrains granularity, especially for portfolios with many holdings.

8. **I could not evaluate all 30 ETFs equally**: I focused on the ~15-18 most promising candidates per scenario and may have missed non-obvious good combinations.

9. **Yield-return tradeoff**: Some high-yield bonds (HYG at 5.88%) have modest returns. In a multi-objective setting, the solver would find the exact tradeoff frontier; I can only estimate.

10. **Scenario 3 vol explosion**: Many equities exceed 20% vol individually in the recession scenario, making them nearly unusable as significant holdings without large bond allocations to offset.

---

## 4. Per-Scenario Results

### Scenario 1: Base Case

#### Growth Portfolio
**Goal**: Maximize return, accept higher vol (but stay under 20%).

Holdings:
- GLD: 30% (return 19.88, vol 15.91, yield 0.00)
- VDE: 10% (return 22.08, vol 26.59, yield 2.27) [Sector 1]
- VGT: 10% (return 16.19, vol 21.47, yield 0.44) [Sector 2]
- VOO: 20% (return 11.98, vol 15.63, yield 1.19)
- IGF: 15% (return 11.11, vol 15.32, yield 2.96) [Alt 2]
- DBA: 15% (return 10.71, vol 12.20, yield 3.35) [Alt 3]

Holdings: 6 (OK). Sectors: 2 (OK). Alternatives: 3 (OK).

Weighted return: 0.30*19.88 + 0.10*22.08 + 0.10*16.19 + 0.20*11.98 + 0.15*11.11 + 0.15*10.71
= 5.964 + 2.208 + 1.619 + 2.396 + 1.667 + 1.607
= 15.46%

Weighted vol: 0.30*15.91 + 0.10*26.59 + 0.10*21.47 + 0.20*15.63 + 0.15*15.32 + 0.15*12.20
= 4.773 + 2.659 + 2.147 + 3.126 + 2.298 + 1.830
= 16.83%

Weighted yield: 0.30*0.00 + 0.10*2.27 + 0.10*0.44 + 0.20*1.19 + 0.15*2.96 + 0.15*3.35
= 0 + 0.227 + 0.044 + 0.238 + 0.444 + 0.503
= 1.46%

**Return: 15.46% | Vol: 16.83% | Yield: 1.46%** -- constraints satisfied.

#### Balanced Portfolio
**Goal**: Good return with moderate vol, reasonable yield.

Holdings:
- GLD: 20% (Alt 1)
- VOO: 20%
- DBA: 15% (Alt 2)
- IGF: 15% (Alt 3)
- VTV: 15%
- VGSH: 15%

Holdings: 6. Sectors: 0. Alternatives: 3.

Weighted return: 0.20*19.88 + 0.20*11.98 + 0.15*10.71 + 0.15*11.11 + 0.15*10.35 + 0.15*1.83
= 3.976 + 2.396 + 1.607 + 1.667 + 1.553 + 0.275
= 11.47%

Weighted vol: 0.20*15.91 + 0.20*15.63 + 0.15*12.20 + 0.15*15.32 + 0.15*14.46 + 0.15*2.20
= 3.182 + 3.126 + 1.830 + 2.298 + 2.169 + 0.330
= 12.94%

Weighted yield: 0.20*0.00 + 0.20*1.19 + 0.15*3.35 + 0.15*2.96 + 0.15*2.02 + 0.15*3.95
= 0 + 0.238 + 0.503 + 0.444 + 0.303 + 0.593
= 2.08%

**Return: 11.47% | Vol: 12.94% | Yield: 2.08%** -- constraints satisfied.

#### Income Portfolio
**Goal**: Maximize yield, decent return.

Holdings:
- HYG: 25% (yield 5.88)
- EWJ: 20% (yield 4.33)
- VGSH: 20% (yield 3.95)
- DBA: 15% (yield 3.35, Alt 1)
- SCHD: 10% (yield 3.44)
- IGF: 10% (yield 2.96, Alt 2)

Holdings: 6. Sectors: 0. Alternatives: 2.

Weighted return: 0.25*3.91 + 0.20*7.78 + 0.20*1.83 + 0.15*10.71 + 0.10*7.45 + 0.10*11.11
= 0.978 + 1.556 + 0.366 + 1.607 + 0.745 + 1.111
= 6.36%

Weighted vol: 0.25*7.89 + 0.20*15.64 + 0.20*2.20 + 0.15*12.20 + 0.10*15.35 + 0.10*15.32
= 1.973 + 3.128 + 0.440 + 1.830 + 1.535 + 1.532
= 10.44%

Weighted yield: 0.25*5.88 + 0.20*4.33 + 0.20*3.95 + 0.15*3.35 + 0.10*3.44 + 0.10*2.96
= 1.470 + 0.866 + 0.790 + 0.503 + 0.344 + 0.296
= 4.27%

**Return: 6.36% | Vol: 10.44% | Yield: 4.27%** -- constraints satisfied.

#### Safety Portfolio
**Goal**: Minimize vol, acceptable return.

Holdings:
- VGSH: 40% (vol 2.20)
- BND: 20% (vol 6.51)
- TIP: 15% (vol 6.63)
- DBA: 15% (vol 12.20, Alt 1)
- HYG: 10% (vol 7.89)

Holdings: 5. Sectors: 0. Alternatives: 1.

Weighted return: 0.40*1.83 + 0.20*0.23 + 0.15*1.06 + 0.15*10.71 + 0.10*3.91
= 0.732 + 0.046 + 0.159 + 1.607 + 0.391
= 2.94%

Weighted vol: 0.40*2.20 + 0.20*6.51 + 0.15*6.63 + 0.15*12.20 + 0.10*7.89
= 0.880 + 1.302 + 0.995 + 1.830 + 0.789
= 5.80%

Weighted yield: 0.40*3.95 + 0.20*3.91 + 0.15*3.45 + 0.15*3.35 + 0.10*5.88
= 1.580 + 0.782 + 0.518 + 0.503 + 0.588
= 3.97%

**Return: 2.94% | Vol: 5.80% | Yield: 3.97%** -- constraints satisfied.

---

### Scenario 2: Rate Cuts / Risk-On

#### Growth Portfolio

Holdings:
- VDE: 10% (22.08, 26.59) [Sector 1]
- GLD: 25% (19.88, 15.91) [Alt 1]
- VGT: 10% (16.19, 21.47) [Sector 2]
- VOO: 25% (15.57, 14.07)
- VUG: 15% (15.90, 17.86)
- VTV: 15% (13.46, 13.01)

Holdings: 6. Sectors: 2. Alternatives: 1.

Weighted return: 0.10*22.08 + 0.25*19.88 + 0.10*16.19 + 0.25*15.57 + 0.15*15.90 + 0.15*13.46
= 2.208 + 4.970 + 1.619 + 3.893 + 2.385 + 2.019
= 17.09%

Weighted vol: 0.10*26.59 + 0.25*15.91 + 0.10*21.47 + 0.25*14.07 + 0.15*17.86 + 0.15*13.01
= 2.659 + 3.978 + 2.147 + 3.518 + 2.679 + 1.952
= 16.93%

Weighted yield: 0.10*2.27 + 0.25*0.00 + 0.10*0.44 + 0.25*1.19 + 0.15*0.46 + 0.15*2.02
= 0.227 + 0 + 0.044 + 0.298 + 0.069 + 0.303
= 0.94%

**Return: 17.09% | Vol: 16.93% | Yield: 0.94%**

#### Balanced Portfolio

Holdings:
- VOO: 25% (15.57, 14.07)
- GLD: 15% (19.88, 15.91) [Alt 1]
- VEA: 15% (11.47, 15.08)
- VTV: 15% (13.46, 13.01)
- SCHD: 10% (9.69, 13.82)
- DBA: 10% (10.71, 12.20) [Alt 2]
- VGLT: 10% (8.00, 13.82)

Holdings: 7. Sectors: 0. Alternatives: 2.

Weighted return: 0.25*15.57 + 0.15*19.88 + 0.15*11.47 + 0.15*13.46 + 0.10*9.69 + 0.10*10.71 + 0.10*8.00
= 3.893 + 2.982 + 1.721 + 2.019 + 0.969 + 1.071 + 0.800
= 13.45%

Weighted vol: 0.25*14.07 + 0.15*15.91 + 0.15*15.08 + 0.15*13.01 + 0.10*13.82 + 0.10*12.20 + 0.10*13.82
= 3.518 + 2.387 + 2.262 + 1.952 + 1.382 + 1.220 + 1.382
= 14.10%

Weighted yield: 0.25*1.19 + 0.15*0.00 + 0.15*2.94 + 0.15*2.02 + 0.10*3.44 + 0.10*3.35 + 0.10*3.14
= 0.298 + 0 + 0.441 + 0.303 + 0.344 + 0.335 + 0.314
= 2.03%

**Return: 13.45% | Vol: 14.10% | Yield: 2.03%**

#### Income Portfolio

Holdings:
- EWJ: 20% (10.11, 14.08, yield 4.33)
- HYG: 20% (3.91, 7.89, yield 4.12)
- VGSH: 15% (1.83, 2.20, yield 2.77)
- SCHD: 15% (9.69, 13.82, yield 3.44)
- VGLT: 15% (8.00, 13.82, yield 3.14)
- DBA: 15% (10.71, 12.20, yield 3.35) [Alt 1]

Holdings: 6. Sectors: 0. Alternatives: 1.

Weighted return: 0.20*10.11 + 0.20*3.91 + 0.15*1.83 + 0.15*9.69 + 0.15*8.00 + 0.15*10.71
= 2.022 + 0.782 + 0.275 + 1.454 + 1.200 + 1.607
= 7.34%

Weighted vol: 0.20*14.08 + 0.20*7.89 + 0.15*2.20 + 0.15*13.82 + 0.15*13.82 + 0.15*12.20
= 2.816 + 1.578 + 0.330 + 2.073 + 2.073 + 1.830
= 10.70%

Weighted yield: 0.20*4.33 + 0.20*4.12 + 0.15*2.77 + 0.15*3.44 + 0.15*3.14 + 0.15*3.35
= 0.866 + 0.824 + 0.416 + 0.516 + 0.471 + 0.503
= 3.60%

**Return: 7.34% | Vol: 10.70% | Yield: 3.60%**

Note: Yields are lower in this scenario because bond yields compressed (x0.7). This makes it harder to construct high-yield portfolios.

#### Safety Portfolio

Holdings:
- VGSH: 40% (1.83, 2.20, yield 2.77)
- BND: 15% (0.23, 6.51, yield 2.74)
- TIP: 15% (1.06, 6.63, yield 2.42)
- VGLT: 15% (8.00, 13.82, yield 3.14)
- HYG: 15% (3.91, 7.89, yield 4.12)

Holdings: 5. Sectors: 0. Alternatives: 0.

Weighted return: 0.40*1.83 + 0.15*0.23 + 0.15*1.06 + 0.15*8.00 + 0.15*3.91
= 0.732 + 0.035 + 0.159 + 1.200 + 0.587
= 2.71%

Weighted vol: 0.40*2.20 + 0.15*6.51 + 0.15*6.63 + 0.15*13.82 + 0.15*7.89
= 0.880 + 0.977 + 0.995 + 2.073 + 1.184
= 6.11%

Weighted yield: 0.40*2.77 + 0.15*2.74 + 0.15*2.42 + 0.15*3.14 + 0.15*4.12
= 1.108 + 0.411 + 0.363 + 0.471 + 0.618
= 2.97%

**Return: 2.71% | Vol: 6.11% | Yield: 2.97%**

---

### Scenario 3: Recession / Risk-Off

This is the most constrained scenario. Most equities have vol >20%, making them nearly unusable in large allocations.

#### Growth Portfolio
**Goal**: Best return possible while keeping vol under 20%. This is very hard in a recession.

Holdings:
- GLD: 35% (19.88, 15.91) [Alt 1]
- DBA: 20% (10.71, 12.20) [Alt 2]
- IGF: 15% (11.11, 15.32) [Alt 3]
- VGSH: 15% (4.00, 2.20)
- BND: 15% (4.00, 6.51)

Holdings: 5. Sectors: 0. Alternatives: 3.

Weighted return: 0.35*19.88 + 0.20*10.71 + 0.15*11.11 + 0.15*4.00 + 0.15*4.00
= 6.958 + 2.142 + 1.667 + 0.600 + 0.600
= 11.97%

Weighted vol: 0.35*15.91 + 0.20*12.20 + 0.15*15.32 + 0.15*2.20 + 0.15*6.51
= 5.569 + 2.440 + 2.298 + 0.330 + 0.977
= 11.61%

Weighted yield: 0.35*0.00 + 0.20*3.35 + 0.15*2.96 + 0.15*3.95 + 0.15*3.91
= 0 + 0.670 + 0.444 + 0.593 + 0.587
= 2.29%

**Return: 11.97% | Vol: 11.61% | Yield: 2.29%**

#### Balanced Portfolio

Holdings:
- GLD: 25% (19.88, 15.91) [Alt 1]
- VGSH: 25% (4.00, 2.20)
- DBA: 15% (10.71, 12.20) [Alt 2]
- BND: 15% (4.00, 6.51)
- IGF: 10% (11.11, 15.32) [Alt 3]
- HYG: 10% (-2.00, 10.30)

Holdings: 6. Sectors: 0. Alternatives: 3.

Weighted return: 0.25*19.88 + 0.25*4.00 + 0.15*10.71 + 0.15*4.00 + 0.10*11.11 + 0.10*(-2.00)
= 4.970 + 1.000 + 1.607 + 0.600 + 1.111 - 0.200
= 9.09%

Weighted vol: 0.25*15.91 + 0.25*2.20 + 0.15*12.20 + 0.15*6.51 + 0.10*15.32 + 0.10*10.30
= 3.978 + 0.550 + 1.830 + 0.977 + 1.532 + 1.030
= 9.90%

Weighted yield: 0.25*0.00 + 0.25*3.95 + 0.15*3.35 + 0.15*3.91 + 0.10*2.96 + 0.10*5.88
= 0 + 0.988 + 0.503 + 0.587 + 0.296 + 0.588
= 2.96%

**Return: 9.09% | Vol: 9.90% | Yield: 2.96%**

Wait -- HYG has -2% return, which drags this down. Let me reconsider. Actually the yield of 5.88% is valuable for a balanced portfolio. Let me keep it but note the tradeoff.

#### Income Portfolio

Holdings:
- HYG: 10% (-2.00, 10.30, yield 5.88) -- negative return but highest yield
- VGSH: 30% (4.00, 2.20, yield 3.95)
- BND: 15% (4.00, 6.51, yield 3.91)
- EWJ: 10% (3.11, 23.46, yield 4.33)
- DBA: 15% (10.71, 12.20, yield 3.35) [Alt 1]
- VGLT: 10% (-5.00, 13.82, yield 4.49)
- TIP: 10% (1.06, 6.63, yield 3.45)

Holdings: 7. Sectors: 0. Alternatives: 1.

Weighted return: 0.10*(-2.00) + 0.30*4.00 + 0.15*4.00 + 0.10*3.11 + 0.15*10.71 + 0.10*(-5.00) + 0.10*1.06
= -0.200 + 1.200 + 0.600 + 0.311 + 1.607 - 0.500 + 0.106
= 3.12%

Weighted vol: 0.10*10.30 + 0.30*2.20 + 0.15*6.51 + 0.10*23.46 + 0.15*12.20 + 0.10*13.82 + 0.10*6.63
= 1.030 + 0.660 + 0.977 + 2.346 + 1.830 + 1.382 + 0.663
= 8.89%

Weighted yield: 0.10*5.88 + 0.30*3.95 + 0.15*3.91 + 0.10*4.33 + 0.15*3.35 + 0.10*4.49 + 0.10*3.45
= 0.588 + 1.185 + 0.587 + 0.433 + 0.503 + 0.449 + 0.345
= 4.09%

**Return: 3.12% | Vol: 8.89% | Yield: 4.09%**

Note: EWJ has high vol (23.46%) but only 10% allocation so contributes ~2.35% to weighted vol. Manageable.

#### Safety Portfolio

Holdings:
- VGSH: 50% (4.00, 2.20, yield 3.95)
- BND: 20% (4.00, 6.51, yield 3.91)
- TIP: 15% (1.06, 6.63, yield 3.45)
- DBA: 15% (10.71, 12.20, yield 3.35) [Alt 1]

Holdings: 4 (minimum). Sectors: 0. Alternatives: 1.

Weighted return: 0.50*4.00 + 0.20*4.00 + 0.15*1.06 + 0.15*10.71
= 2.000 + 0.800 + 0.159 + 1.607
= 4.57%

Weighted vol: 0.50*2.20 + 0.20*6.51 + 0.15*6.63 + 0.15*12.20
= 1.100 + 1.302 + 0.995 + 1.830
= 5.23%

Weighted yield: 0.50*3.95 + 0.20*3.91 + 0.15*3.45 + 0.15*3.35
= 1.975 + 0.782 + 0.518 + 0.503
= 3.78%

**Return: 4.57% | Vol: 5.23% | Yield: 3.78%**

---

### Scenario 4: Inflation Surge

#### Growth Portfolio

Holdings:
- GLD: 30% (29.82, 15.91) [Alt 1]
- GSG: 15% (23.79, 19.40) [Alt 2]
- DBA: 15% (16.07, 12.20) [Alt 3]
- VGT: 10% (16.19, 21.47) [Sector 1]
- VDE: 5% (22.08, 26.59) [Sector 2]
- VOO: 15% (9.58, 15.63)
- TIP: 10% (6.00, 6.63)

Holdings: 7. Sectors: 2. Alternatives: 3.

Weighted return: 0.30*29.82 + 0.15*23.79 + 0.15*16.07 + 0.10*16.19 + 0.05*22.08 + 0.15*9.58 + 0.10*6.00
= 8.946 + 3.569 + 2.411 + 1.619 + 1.104 + 1.437 + 0.600
= 19.69%

Weighted vol: 0.30*15.91 + 0.15*19.40 + 0.15*12.20 + 0.10*21.47 + 0.05*26.59 + 0.15*15.63 + 0.10*6.63
= 4.773 + 2.910 + 1.830 + 2.147 + 1.330 + 2.345 + 0.663
= 16.00%

Weighted yield: 0.30*0.00 + 0.15*0.00 + 0.15*3.35 + 0.10*0.44 + 0.05*2.27 + 0.15*1.19 + 0.10*3.80
= 0 + 0 + 0.503 + 0.044 + 0.114 + 0.179 + 0.380
= 1.22%

**Return: 19.69% | Vol: 16.00% | Yield: 1.22%**

#### Balanced Portfolio

Holdings:
- GLD: 25% (29.82, 15.91) [Alt 1]
- DBA: 15% (16.07, 12.20) [Alt 2]
- IGF: 10% (11.11, 15.32) [Alt 3]
- VOO: 15% (9.58, 15.63)
- TIP: 15% (6.00, 6.63)
- VGSH: 10% (1.83, 2.20)
- VTV: 10% (8.28, 14.46)

Holdings: 7. Sectors: 0. Alternatives: 3.

Weighted return: 0.25*29.82 + 0.15*16.07 + 0.10*11.11 + 0.15*9.58 + 0.15*6.00 + 0.10*1.83 + 0.10*8.28
= 7.455 + 2.411 + 1.111 + 1.437 + 0.900 + 0.183 + 0.828
= 14.33%

Weighted vol: 0.25*15.91 + 0.15*12.20 + 0.10*15.32 + 0.15*15.63 + 0.15*6.63 + 0.10*2.20 + 0.10*14.46
= 3.978 + 1.830 + 1.532 + 2.345 + 0.995 + 0.220 + 1.446
= 12.35%

Weighted yield: 0.25*0.00 + 0.15*3.35 + 0.10*2.96 + 0.15*1.19 + 0.15*3.80 + 0.10*4.35 + 0.10*2.02
= 0 + 0.503 + 0.296 + 0.179 + 0.570 + 0.435 + 0.202
= 2.18%

**Return: 14.33% | Vol: 12.35% | Yield: 2.18%**

#### Income Portfolio

Holdings:
- HYG: 20% (3.91, 7.89, yield 6.47)
- EWJ: 15% (6.22, 15.64, yield 4.33)
- VGSH: 20% (1.83, 2.20, yield 4.35)
- DBA: 15% (16.07, 12.20, yield 3.35) [Alt 1]
- TIP: 15% (6.00, 6.63, yield 3.80)
- SCHD: 15% (5.96, 15.35, yield 3.44)

Holdings: 6. Sectors: 0. Alternatives: 1.

Weighted return: 0.20*3.91 + 0.15*6.22 + 0.20*1.83 + 0.15*16.07 + 0.15*6.00 + 0.15*5.96
= 0.782 + 0.933 + 0.366 + 2.411 + 0.900 + 0.894
= 6.29%

Weighted vol: 0.20*7.89 + 0.15*15.64 + 0.20*2.20 + 0.15*12.20 + 0.15*6.63 + 0.15*15.35
= 1.578 + 2.346 + 0.440 + 1.830 + 0.995 + 2.303
= 9.49%

Weighted yield: 0.20*6.47 + 0.15*4.33 + 0.20*4.35 + 0.15*3.35 + 0.15*3.80 + 0.15*3.44
= 1.294 + 0.650 + 0.870 + 0.503 + 0.570 + 0.516
= 4.40%

**Return: 6.29% | Vol: 9.49% | Yield: 4.40%**

#### Safety Portfolio

Holdings:
- VGSH: 40% (1.83, 2.20, yield 4.35)
- TIP: 25% (6.00, 6.63, yield 3.80)
- DBA: 15% (16.07, 12.20, yield 3.35) [Alt 1]
- HYG: 10% (3.91, 7.89, yield 6.47)
- SCHD: 10% (5.96, 15.35, yield 3.44)

Holdings: 5. Sectors: 0. Alternatives: 1.

Weighted return: 0.40*1.83 + 0.25*6.00 + 0.15*16.07 + 0.10*3.91 + 0.10*5.96
= 0.732 + 1.500 + 2.411 + 0.391 + 0.596
= 5.63%

Weighted vol: 0.40*2.20 + 0.25*6.63 + 0.15*12.20 + 0.10*7.89 + 0.10*15.35
= 0.880 + 1.658 + 1.830 + 0.789 + 1.535
= 6.69%

Weighted yield: 0.40*4.35 + 0.25*3.80 + 0.15*3.35 + 0.10*6.47 + 0.10*3.44
= 1.740 + 0.950 + 0.503 + 0.647 + 0.344
= 4.18%

**Return: 5.63% | Vol: 6.69% | Yield: 4.18%**

---

## 5. Robustness Analysis

### ETFs that appear across ALL or nearly all scenarios (robust holdings):

| ETF | Scenarios Present | Strategies | Why Robust |
|-----|------------------|------------|------------|
| **VGSH** | All 4 | Safety, Income, Balanced | Ultra-low vol (2.2%) anchors any portfolio. Decent yield. Acts as ballast. |
| **GLD** | All 4 | Growth, Balanced | Exceptional return/vol ratio in all scenarios (and even better in inflation). Only drawback: zero yield. |
| **DBA** | All 4 | Growth, Balanced, Income, Safety | Strong across the board: decent return (~10-16%), moderate vol (12.2%), good yield (3.35%). Best risk-adjusted alternative. |
| **VOO** | 3 of 4 (not Recession) | Growth, Balanced | Core US equity. Good return/vol. Becomes unusable in recession due to vol explosion. |
| **HYG** | 3 of 4 | Income, Safety | Highest yield bond. Return varies by scenario but yield is always attractive. |
| **TIP** | 3 of 4 | Safety, Balanced, Income | Low vol, decent yield. Star performer in inflation scenario (6% return override). |
| **IGF** | 3 of 4 | Growth, Balanced | Solid return (11.11%), moderate vol, good yield. Infrastructure is a diversifier. |

### Scenario-specific holdings:

| ETF | Scenario | Why |
|-----|----------|-----|
| **VGLT** | Scenario 2 (Rate Cuts) | Return jumps from -5% to +8% on duration benefit. Worthless or harmful in other scenarios. |
| **VDE** | Scenario 1 & 4 (Growth) | Highest base return (22%) but extreme vol (26.6%). Only usable in small doses. |
| **VGT** | Scenario 1, 2, 4 (Growth) | High return but high vol. Not usable in recession. |
| **GSG** | Scenario 4 (Inflation) | Commodities rally (23.79%) makes this a strong growth holding, but zero yield and high vol. |
| **EWJ** | Income portfolios | Highest equity yield (4.33%) makes it an income play across scenarios, but recession vol hurts. |
| **BND** | Scenario 3 (Recession) | Override to 4% return makes it attractive. Normally mediocre. |

### Core "all-weather" trio: VGSH + GLD + DBA
These three ETFs appear in portfolios across every scenario and every strategy (in various weights). They offer:
- VGSH: safety anchor (2.2% vol)
- GLD: return engine (15.9-29.8% return depending on scenario)
- DBA: balanced profile (10.7-16.1% return, 12.2% vol, 3.35% yield)

---

## 6. Interpretation Response

### Cross-Scenario Portfolio Analysis: What Changes, What Persists, and Why It Matters

**The Core Finding: Three ETFs Form a Robust Foundation**

Across all four macro scenarios -- from a benign continuation of current trends to a severe recession or inflation surge -- three ETFs consistently appear in well-constructed portfolios: VGSH (short-term Treasuries), GLD (gold), and DBA (agriculture commodities). This trio provides complementary characteristics: VGSH contributes ultra-low volatility (2.2%) and steady yield (~3.5-4.4%), GLD delivers strong risk-adjusted returns (return/vol ratio of 1.25 in the base case, rising to 1.88 under inflation), and DBA offers a balanced profile combining above-average returns, below-average volatility, and meaningful yield. Any portfolio strategy benefits from some combination of these three.

**How Strategies Shift Across Scenarios**

*Growth portfolios* show the widest return dispersion across scenarios. In the base case, the growth portfolio achieves 15.5% return at 16.8% vol. Under rate cuts, equities get a significant boost (returns x1.3, vol x0.9), pushing the growth portfolio to 17.1% return. In the inflation scenario, GLD's override to 29.8% return powers the growth portfolio to 19.7%. But in a recession, even the "growth" portfolio maxes out at 12.0% return because equities become effectively unusable (vol exceeds 20-30%), forcing the portfolio into alternatives and bonds. The growth portfolio's return range across scenarios: **12.0% to 19.7%**, a 7.7 percentage point spread.

*Safety portfolios* are far more stable. Returns range from 2.7% (rate cuts, where bond yields compress) to 5.6% (inflation, where TIP's 6% return override helps), and volatility stays in the narrow 5.2-6.7% band across all scenarios. The tradeoff is clear: stability comes at the cost of ~10-14 percentage points of return versus growth.

*Income portfolios* face an interesting scenario dependency. In the base case and inflation scenarios, yields reach 4.3-4.4%. But under rate cuts, bond yield compression (x0.7 multiplier) drops the income portfolio's yield to 3.6% -- an 18% reduction. This quantifies the income investor's rate-cut risk. In a recession, yields hold up at 4.1% because the high-yield ETFs maintain their yields even as their returns suffer.

*Balanced portfolios* occupy the middle ground predictably, with returns of 9.1% (recession) to 14.3% (inflation) and vol of 9.9-14.1%.

**The Marginal Cost of Return**

Across scenarios, gaining an additional percentage point of expected return above the balanced portfolio typically costs 1.0-1.5 percentage points of additional volatility. For example, in the base case, moving from Balanced (11.5% return, 12.9% vol) to Growth (15.5% return, 16.8% vol) trades 4 points of return for 3.9 points of vol -- roughly 1:1. In the inflation scenario, the tradeoff is more favorable: Growth gains 5.4 points of return over Balanced for only 3.7 points of additional vol.

**Scenario-Specific Opportunities**

The most dramatic scenario-specific opportunity is VGLT under rate cuts: its return jumps from -5% (base) to +8%, a 13 percentage point swing. This is a pure duration bet -- if rate cuts materialize, long Treasuries are a strong addition to any portfolio. Conversely, VGLT drops to -8% under inflation, making it the single worst ETF in that scenario. This 16 percentage point spread between rate-cut and inflation scenarios perfectly illustrates why scenario analysis matters.

Commodity ETFs (GLD, GSG, DBA) all get significant return boosts under inflation (1.5x multiplier), making them the dominant asset class in that scenario. Under recession, they are unaffected (no multiplier), which makes them relatively more attractive as equities deteriorate.

**Key Tradeoffs for an Investor**

1. **If you believe rates will be cut**: Overweight VGLT and equities (especially large-cap growth like VUG and VOO). Accept lower yields.
2. **If you fear recession**: Concentrate in VGSH, GLD, DBA, and BND. Avoid equities and sector bets entirely. Accept modest returns (4-12% range).
3. **If you expect inflation**: Load up on GLD, GSG, DBA, and TIP. Avoid nominal bonds (BND, VGLT). This scenario offers the highest growth potential (19.7%) with manageable risk.
4. **If you want to be robust across all scenarios**: Anchor in VGSH (20-40%), GLD (15-25%), and DBA (10-15%), then add scenario-tilted satellites. This gives up 3-5% of return versus the scenario-optimal growth portfolio but avoids catastrophic positioning under any regime.

---

## 7. Limitations

1. **Not Pareto-optimal**: My portfolios are heuristically constructed, not mathematically optimized. A solver exploring the full combinatorial space would almost certainly find portfolios that dominate mine on at least one objective. The gap is likely largest for the growth portfolios, where the tradeoff frontier between return and volatility is most sensitive to allocation precision.

2. **No correlation modeling**: I used weighted-average volatility as a simplified risk measure. In reality, portfolio volatility depends on asset correlations. A diversified portfolio's true volatility would be lower than its weighted-average volatility, which means my "risky" portfolios may actually be safer than they appear, and the vol constraint may be less binding than I assumed.

3. **Arithmetic error risk**: All computations were done mentally. I showed my work to allow verification, but with ~16 portfolios each requiring 3 weighted-average calculations across 4-7 holdings, there are ~150+ individual multiplications and additions. I estimate a 10-20% chance of at least one material arithmetic error (>0.5% impact on a metric).

4. **Explored tiny solution space**: With 30 ETFs, I effectively considered 15-18 candidates per scenario and tried 1-2 allocation patterns per strategy. A solver would evaluate thousands to millions of combinations.

5. **No sensitivity analysis on allocations**: I did not systematically test whether shifting 5% from one holding to another would improve the portfolio. My allocations are "round number" approximations (multiples of 5%) rather than optimized integer solutions.

6. **Missing inter-scenario consistency**: In a real portfolio construction process, you would want to minimize turnover across scenarios (if you're building a robust portfolio rather than scenario-specific ones). I treated each scenario independently.

7. **Yield compression handling**: In Scenario 2, I may have underexplored alternatives to traditional bonds for income generation. The 0.7x yield multiplier makes it structurally harder to hit high yield targets, and a solver might find non-obvious combinations.

8. **Cannot verify constraint feasibility boundaries**: I don't know how close to the theoretical maximum return I am for a given vol constraint, or the maximum yield for a given return level. My portfolios are feasible but I cannot quantify how far from optimal they are.

---

## 8. Raw Data

```json
{
  "scenario_1_base_case": {
    "growth": {
      "allocations": {"GLD": 30, "VDE": 10, "VGT": 10, "VOO": 20, "IGF": 15, "DBA": 15},
      "metrics": {"return_pct": 15.46, "volatility_pct": 16.83, "yield_pct": 1.46}
    },
    "balanced": {
      "allocations": {"GLD": 20, "VOO": 20, "DBA": 15, "IGF": 15, "VTV": 15, "VGSH": 15},
      "metrics": {"return_pct": 11.47, "volatility_pct": 12.94, "yield_pct": 2.08}
    },
    "income": {
      "allocations": {"HYG": 25, "EWJ": 20, "VGSH": 20, "DBA": 15, "SCHD": 10, "IGF": 10},
      "metrics": {"return_pct": 6.36, "volatility_pct": 10.44, "yield_pct": 4.27}
    },
    "safety": {
      "allocations": {"VGSH": 40, "BND": 20, "TIP": 15, "DBA": 15, "HYG": 10},
      "metrics": {"return_pct": 2.94, "volatility_pct": 5.80, "yield_pct": 3.97}
    }
  },
  "scenario_2_rate_cuts": {
    "growth": {
      "allocations": {"VDE": 10, "GLD": 25, "VGT": 10, "VOO": 25, "VUG": 15, "VTV": 15},
      "metrics": {"return_pct": 17.09, "volatility_pct": 16.93, "yield_pct": 0.94}
    },
    "balanced": {
      "allocations": {"VOO": 25, "GLD": 15, "VEA": 15, "VTV": 15, "SCHD": 10, "DBA": 10, "VGLT": 10},
      "metrics": {"return_pct": 13.45, "volatility_pct": 14.10, "yield_pct": 2.03}
    },
    "income": {
      "allocations": {"EWJ": 20, "HYG": 20, "VGSH": 15, "SCHD": 15, "VGLT": 15, "DBA": 15},
      "metrics": {"return_pct": 7.34, "volatility_pct": 10.70, "yield_pct": 3.60}
    },
    "safety": {
      "allocations": {"VGSH": 40, "BND": 15, "TIP": 15, "VGLT": 15, "HYG": 15},
      "metrics": {"return_pct": 2.71, "volatility_pct": 6.11, "yield_pct": 2.97}
    }
  },
  "scenario_3_recession": {
    "growth": {
      "allocations": {"GLD": 35, "DBA": 20, "IGF": 15, "VGSH": 15, "BND": 15},
      "metrics": {"return_pct": 11.97, "volatility_pct": 11.61, "yield_pct": 2.29}
    },
    "balanced": {
      "allocations": {"GLD": 25, "VGSH": 25, "DBA": 15, "BND": 15, "IGF": 10, "HYG": 10},
      "metrics": {"return_pct": 9.09, "volatility_pct": 9.90, "yield_pct": 2.96}
    },
    "income": {
      "allocations": {"HYG": 10, "VGSH": 30, "BND": 15, "EWJ": 10, "DBA": 15, "VGLT": 10, "TIP": 10},
      "metrics": {"return_pct": 3.12, "volatility_pct": 8.89, "yield_pct": 4.09}
    },
    "safety": {
      "allocations": {"VGSH": 50, "BND": 20, "TIP": 15, "DBA": 15},
      "metrics": {"return_pct": 4.57, "volatility_pct": 5.23, "yield_pct": 3.78}
    }
  },
  "scenario_4_inflation": {
    "growth": {
      "allocations": {"GLD": 30, "GSG": 15, "DBA": 15, "VGT": 10, "VDE": 5, "VOO": 15, "TIP": 10},
      "metrics": {"return_pct": 19.69, "volatility_pct": 16.00, "yield_pct": 1.22}
    },
    "balanced": {
      "allocations": {"GLD": 25, "DBA": 15, "IGF": 10, "VOO": 15, "TIP": 15, "VGSH": 10, "VTV": 10},
      "metrics": {"return_pct": 14.33, "volatility_pct": 12.35, "yield_pct": 2.18}
    },
    "income": {
      "allocations": {"HYG": 20, "EWJ": 15, "VGSH": 20, "DBA": 15, "TIP": 15, "SCHD": 15},
      "metrics": {"return_pct": 6.29, "volatility_pct": 9.49, "yield_pct": 4.40}
    },
    "safety": {
      "allocations": {"VGSH": 40, "TIP": 25, "DBA": 15, "HYG": 10, "SCHD": 10},
      "metrics": {"return_pct": 5.63, "volatility_pct": 6.69, "yield_pct": 4.18}
    }
  }
}
```

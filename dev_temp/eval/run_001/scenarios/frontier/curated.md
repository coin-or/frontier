# Curated Strategies — ETF Portfolio

Four strategies per scenario: Growth (max return), Balanced (ideal-point closest), Income (max yield), Safety (min volatility). Allocations sum to 100%. Binding constraints noted when max_allocation (30%) is hit.

## Base Case

### Growth
- **Return 18.74% · Vol 15.74 · Yield 0.82**
- VGT 13, VDE 30*, GLD 30*, GSG 24, IGF 3
- Binds: max_allocation on VDE and GLD, Sector cap (1 used)
- Cardinality 5 — compact high-conviction bet on energy + tech + gold/commodities

### Balanced (ideal-point closest)
- **Return 10.08% · Vol 7.30 · Yield 3.32**
- VGSH 26, HYG 27, GLD 19, VDE 16, IGF 6, VGT 2, VEA 2, EWJ 2
- No binds; cardinality 8 — diversified across short Treasuries, credit, gold, energy

### Income
- **Return 4.50% · Vol 7.01 · Yield 4.90**
- EWJ 29, HYG 30*, EMB 30*, TIP 3, BND 2, VGSH 2, VGK 2, VGLT 1, IGF 1
- Binds: max_allocation on HYG and EMB
- Cardinality 9 — credit-heavy with Japan and diversified Treasuries

### Safety
- **Return 3.64% · Vol 4.17 · Yield 4.06**
- BND 10, VGSH 30*, TIP 15, HYG 23, DBA 9, VDC 6, VTV 3, VEA 2, VNQ 2
- Binds: max_allocation on VGSH; Volatility constraint (≤20) non-binding (vol is only 4.17)
- Cardinality 9 — short Treasuries backbone, HYG for yield, sprinkle of equity for return

## Scenario: Rate Cuts / Risk-On (prob 25%)

### Growth
- **Return 25.28% · Vol 15.61 · Yield 1.05**
- VGT 30*, VDE 30*, GLD 30*, VOO 4, VTV 3, DBA 3
- Binds: max_allocation on VGT, VDE, GLD; Sector cap (2 used: VGT, VDE)
- Cardinality 6 — leveraged into the rate-cut-juiced tech and energy

### Balanced
- **Return 12.86% · Vol 9.42 · Yield 2.88**
- DBA 25, VDE 18, EWJ 17, VGLT 16, BND 10, HYG 9, VGT 3, GLD 2
- Binds: none
- Cardinality 8 — bond duration (VGLT at +10% override), commodities, energy

### Income
- **Return 7.85% · Vol 12.01 · Yield 3.85**
- EWJ 30*, VNQ 30*, DBA 23, VNQI 7, SCHD 4, VTV 2, VEA 1, HYG 2, VGT 1
- Binds: max_allocation on EWJ, VNQ; Alternative cap (2 used: VNQ, VNQI, DBA = 3, hits cap)
- Cardinality 9 — Japan + REITs for yield (compressed bond yields push allocation to equity income)

### Safety
- **Return 3.86% · Vol 4.15 · Yield 2.28**
- BND 28, VGSH 30*, HYG 24, VTV 6, SCHD 2, EWJ 2, VDC 2, VGLT 1, VGT 1, VOX 1, DBA 3
- Binds: max_allocation on VGSH
- Cardinality 11 — short Treasury + broad credit, modest equity sprinkle

## Scenario: Recession / Risk-Off (prob 20%)

### Growth
- **Return 12.58% · Vol 10.20 · Yield 1.83**
- BND 13, VGLT 30*, GLD 30*, GSG 27
- Binds: max_allocation on VGLT, GLD
- Cardinality 4 (at minimum) — flight to safety: long Treasuries rally + gold + commodities hedge

### Balanced
- **Return 6.69% · Vol 5.14 · Yield 3.59**
- BND 30*, VGSH 30*, VGLT 15, GLD 11, HYG 6, VOO 3, VEA 3, EWJ 2
- Binds: max_allocation on BND and VGSH
- Cardinality 8 — heavy Treasuries, gold hedge, minimal equity

### Income
- **Return -1.50% · Vol 7.75 · Yield 5.02**
- BND 13, VGSH 3, VGLT 3, HYG 30*, EMB 25, VNQI 26
- Binds: max_allocation on HYG
- Cardinality 6 — but note negative return: recession shock to credit (HYG=-4, EMB=-5 overrides) pulls this down

### Safety
- **Return 2.02% · Vol 4.16 · Yield 4.25**
- BND 25, VGSH 30*, VGLT 2, TIP 1, HYG 26, SCHD 7, DBA 2, VDC 4, VWO 2, VHT 1
- Binds: max_allocation on VGSH
- Cardinality 10 — broad bond/credit exposure, small defensive equity

## Scenario: Inflation Surge (prob 25%)

### Growth
- **Return 30.05% · Vol 13.75 · Yield 1.87**
- EMB 5, VDE 30*, GLD 30*, GSG 5, DBA 30*
- Binds: max_allocation on VDE, GLD, DBA; Alternative cap (2 used: GLD, GSG, DBA = 3, at cap)
- Cardinality 5 — commodities trade dominates: gold + agri + energy all juiced by inflation overrides

### Balanced
- **Return 11.54% · Vol 6.44 · Yield 4.46**
- VUG 2, BND 2, VGSH 10, TIP 3, HYG 23, EMB 23, VDE 2, GLD 14, DBA 21
- Binds: none
- Cardinality 9 — gold + agri + credit, small TIP + VGSH barbell

### Income
- **Return -2.65% · Vol 8.10 · Yield 5.95**
- SCHD 2, VGK 1, BND 2, VGSH 3, VGLT 30*, HYG 30*, EMB 30*, VDE 1, DBA 1
- Binds: max_allocation on VGLT, HYG, EMB
- Cardinality 9 — pushing credit yield hard but VGLT=-12% drags return negative

### Safety
- **Return 2.14% · Vol 4.14 · Yield 4.40**
- VTV 2, SCHD 3, VGK 2, BND 30*, VGSH 30*, TIP 20, HYG 5, VDE 2, VFH 1, DBA 4, IGF 1
- Binds: max_allocation on BND and VGSH
- Cardinality 11 — TIP-anchored inflation hedge, defensive equity sprinkle

## Cross-Scenario Notes

- **Safety portfolios are remarkably stable** — all four land at ~4.15% vol with 4-5% yield. The covariance matrix (held constant) drives this floor.
- **Growth portfolios diverge wildly** — from 30% (inflation, commodities) to 12% (recession, Treasury duration).
- **Income portfolios are scenario-fragile** — in recession and inflation, the max-yield corner posts negative returns because the high-yield credit overrides go sharply negative.
- **HYG and GLD are the backbone** — present in every curated portfolio except Growth variants where they compete with higher-return alternatives.

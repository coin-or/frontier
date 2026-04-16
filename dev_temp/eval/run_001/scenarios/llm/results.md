# LLM Pure Reasoning: ETF Portfolio Optimization Results

## Method: Pure LLM reasoning with manual arithmetic

---

## BASE DATA REFERENCE

| Ticker | Group | Return% | Vol% | Yield% |
|--------|-------|---------|------|--------|
| VOO | US Equity | 11.98 | 15.63 | 1.19 |
| VUG | US Equity | 12.23 | 19.84 | 0.46 |
| VTV | US Equity | 10.35 | 14.46 | 2.02 |
| VO | US Equity | 6.72 | 17.14 | 1.51 |
| VB | US Equity | 5.96 | 19.05 | 1.34 |
| SCHD | US Equity | 7.45 | 15.35 | 3.44 |
| VEA | Intl Equity | 8.82 | 16.76 | 2.94 |
| VWO | Intl Equity | 4.49 | 15.38 | 2.71 |
| VGK | Intl Equity | 8.47 | 18.14 | 3.01 |
| EWJ | Intl Equity | 7.78 | 15.64 | 4.33 |
| MCHI | Intl Equity | -4.96 | 28.65 | 2.27 |
| BND | Bonds | 0.23 | 6.51 | 3.91 |
| VGSH | Bonds | 1.83 | 2.20 | 3.95 |
| VGLT | Bonds | -5.00 | 13.82 | 4.49 |
| TIP | Bonds | 1.06 | 6.63 | 3.45 |
| HYG | Bonds | 3.91 | 7.89 | 5.88 |
| EMB | Bonds | 1.85 | 10.46 | 5.11 |
| VGT | Sectors | 16.19 | 21.47 | 0.44 |
| VHT | Sectors | 4.24 | 14.83 | 1.72 |
| VDE | Sectors | 22.08 | 26.59 | 2.27 |
| VFH | Sectors | 8.41 | 19.10 | 1.61 |
| VPU | Sectors | 10.60 | 16.83 | 2.57 |
| VDC | Sectors | 6.52 | 13.92 | 2.15 |
| VOX | Sectors | 7.69 | 19.08 | 1.05 |
| VNQ | Alternatives | 2.39 | 19.67 | 3.93 |
| VNQI | Alternatives | -0.58 | 18.22 | 4.87 |
| GLD | Alternatives | 19.88 | 15.91 | 0.00 |
| GSG | Alternatives | 15.86 | 19.40 | 0.00 |
| DBA | Alternatives | 10.71 | 12.20 | 3.35 |
| IGF | Alternatives | 11.11 | 15.32 | 2.96 |

Group classification:
- **Equity** (US Equity + Intl Equity): VOO, VUG, VTV, VO, VB, SCHD, VEA, VWO, VGK, EWJ, MCHI
- **Bonds**: BND, VGSH, VGLT, TIP, HYG, EMB
- **Sectors**: VGT, VHT, VDE, VFH, VPU, VDC, VOX
- **Alternatives**: VNQ, VNQI, GLD, GSG, DBA, IGF

---

## SCENARIO 1: BASE CASE (Continuation) — Probability 30%

### Adjusted Scores
No adjustments. All scores are base values from the table above.

### Portfolio Construction

#### Growth Portfolio
Target: maximize return, accept higher vol, yield unimportant.
Best return ETFs: VDE (22.08), GLD (19.88), VGT (16.19), GSG (15.86), VUG (12.23), VOO (11.98), IGF (11.11)

Holdings: VGT 25%, VOO 20%, VUG 20%, VDE 15%, GLD 10%, IGF 10%

**Constraint check:**
- Max single: 25% <= 30% OK
- Holdings: 6 (4-12 OK)
- Sector ETFs: VGT, VDE = 2 <= 3 OK
- Alt ETFs: GLD, IGF = 2 <= 3 OK
- Volatility: 0.25*21.47 + 0.20*15.63 + 0.20*19.84 + 0.15*26.59 + 0.10*15.91 + 0.10*15.32
  = 5.37 + 3.13 + 3.97 + 3.99 + 1.59 + 1.53 = 19.58 ~= 19.6% <= 20% OK

**Return:** 0.25*16.19 + 0.20*11.98 + 0.20*12.23 + 0.15*22.08 + 0.10*19.88 + 0.10*11.11
  = 4.05 + 2.40 + 2.45 + 3.31 + 1.99 + 1.11 = 15.31%

**Yield:** 0.25*0.44 + 0.20*1.19 + 0.20*0.46 + 0.15*2.27 + 0.10*0.00 + 0.10*2.96
  = 0.11 + 0.24 + 0.09 + 0.34 + 0.00 + 0.30 = 1.08%

**Vol:** 19.58% (computed above)

#### Balanced Portfolio
Target: moderate return with moderate vol and some yield.

Holdings: VOO 25%, GLD 15%, VTV 10%, VEA 10%, SCHD 10%, BND 10%, DBA 10%, IGF 10%

**Constraint check:**
- Max single: 25% <= 30% OK
- Holdings: 8 (4-12 OK)
- Sector ETFs: 0 <= 3 OK
- Alt ETFs: GLD, DBA, IGF = 3 <= 3 OK
- Volatility: 0.25*15.63 + 0.15*15.91 + 0.10*14.46 + 0.10*16.76 + 0.10*15.35 + 0.10*6.51 + 0.10*12.20 + 0.10*15.32
  = 3.91 + 2.39 + 1.45 + 1.68 + 1.54 + 0.65 + 1.22 + 1.53 = 14.37% <= 20% OK

**Return:** 0.25*11.98 + 0.15*19.88 + 0.10*10.35 + 0.10*8.82 + 0.10*7.45 + 0.10*0.23 + 0.10*10.71 + 0.10*11.11
  = 3.00 + 2.98 + 1.04 + 0.88 + 0.75 + 0.02 + 1.07 + 1.11 = 10.85%

**Yield:** 0.25*1.19 + 0.15*0.00 + 0.10*2.02 + 0.10*2.94 + 0.10*3.44 + 0.10*3.91 + 0.10*3.35 + 0.10*2.96
  = 0.30 + 0.00 + 0.20 + 0.29 + 0.34 + 0.39 + 0.34 + 0.30 = 2.16%

**Vol:** 14.37%

#### Income Portfolio
Target: maximize yield, acceptable return, lower vol.
Best yield ETFs: HYG (5.88), EMB (5.11), VNQI (4.87), VGLT (4.49), EWJ (4.33), VGSH (3.95), VNQ (3.93), BND (3.91), SCHD (3.44), TIP (3.45), DBA (3.35)

Holdings: SCHD 20%, HYG 15%, VTV 15%, EWJ 10%, EMB 10%, DBA 15%, VPU 10%, VNQI 5%

**Constraint check:**
- Max single: 20% <= 30% OK
- Holdings: 8 (4-12 OK)
- Sector ETFs: VPU = 1 <= 3 OK
- Alt ETFs: DBA, VNQI = 2 <= 3 OK
- Volatility: 0.20*15.35 + 0.15*7.89 + 0.15*14.46 + 0.10*15.64 + 0.10*10.46 + 0.15*12.20 + 0.10*16.83 + 0.05*18.22
  = 3.07 + 1.18 + 2.17 + 1.56 + 1.05 + 1.83 + 1.68 + 0.91 = 13.45% <= 20% OK

**Return:** 0.20*7.45 + 0.15*3.91 + 0.15*10.35 + 0.10*7.78 + 0.10*1.85 + 0.15*10.71 + 0.10*10.60 + 0.05*(-0.58)
  = 1.49 + 0.59 + 1.55 + 0.78 + 0.19 + 1.61 + 1.06 + (-0.03) = 7.24%

**Yield:** 0.20*3.44 + 0.15*5.88 + 0.15*2.02 + 0.10*4.33 + 0.10*5.11 + 0.15*3.35 + 0.10*2.57 + 0.05*4.87
  = 0.69 + 0.88 + 0.30 + 0.43 + 0.51 + 0.50 + 0.26 + 0.24 = 3.81%

**Vol:** 13.45%

#### Safety Portfolio
Target: minimize vol, decent yield, return secondary.

Holdings: VGSH 30%, BND 25%, TIP 20%, SCHD 15%, VTV 10%

**Constraint check:**
- Max single: 30% <= 30% OK
- Holdings: 5 (4-12 OK)
- Sector ETFs: 0 <= 3 OK
- Alt ETFs: 0 <= 3 OK
- Volatility: 0.30*2.20 + 0.25*6.51 + 0.20*6.63 + 0.15*15.35 + 0.10*14.46
  = 0.66 + 1.63 + 1.33 + 2.30 + 1.45 = 7.37% <= 20% OK

**Return:** 0.30*1.83 + 0.25*0.23 + 0.20*1.06 + 0.15*7.45 + 0.10*10.35
  = 0.55 + 0.06 + 0.21 + 1.12 + 1.04 = 2.98%

**Yield:** 0.30*3.95 + 0.25*3.91 + 0.20*3.45 + 0.15*3.44 + 0.10*2.02
  = 1.19 + 0.98 + 0.69 + 0.52 + 0.20 = 3.58%

**Vol:** 7.37%

#### Max-Return Portfolio
Push return as high as possible while staying at vol <= 20%.

Holdings: VDE 30%, VGT 25%, GLD 20%, VOO 15%, VUG 10%

**Constraint check:**
- Max single: 30% <= 30% OK
- Holdings: 5 (4-12 OK)
- Sector ETFs: VDE, VGT = 2 <= 3 OK
- Alt ETFs: GLD = 1 <= 3 OK
- Volatility: 0.30*26.59 + 0.25*21.47 + 0.20*15.91 + 0.15*15.63 + 0.10*19.84
  = 7.98 + 5.37 + 3.18 + 2.34 + 1.98 = 20.85%

That exceeds 20%. Adjust: reduce VDE to 25%, add DBA 5%.
Holdings: VDE 25%, VGT 25%, GLD 20%, VOO 15%, VUG 10%, DBA 5%

**Vol:** 0.25*26.59 + 0.25*21.47 + 0.20*15.91 + 0.15*15.63 + 0.10*19.84 + 0.05*12.20
  = 6.65 + 5.37 + 3.18 + 2.34 + 1.98 + 0.61 = 20.13%

Still slightly over. Adjust: VDE 20%, VGT 25%, GLD 20%, VOO 20%, VUG 10%, DBA 5%

**Vol:** 0.20*26.59 + 0.25*21.47 + 0.20*15.91 + 0.20*15.63 + 0.10*19.84 + 0.05*12.20
  = 5.32 + 5.37 + 3.18 + 3.13 + 1.98 + 0.61 = 19.59% <= 20% OK

**Return:** 0.20*22.08 + 0.25*16.19 + 0.20*19.88 + 0.20*11.98 + 0.10*12.23 + 0.05*10.71
  = 4.42 + 4.05 + 3.98 + 2.40 + 1.22 + 0.54 = 16.61%

**Yield:** 0.20*2.27 + 0.25*0.44 + 0.20*0.00 + 0.20*1.19 + 0.10*0.46 + 0.05*3.35
  = 0.45 + 0.11 + 0.00 + 0.24 + 0.05 + 0.17 = 1.02%

#### Max-Yield Portfolio

Holdings: HYG 25%, EWJ 15%, EMB 15%, SCHD 15%, VNQI 10%, VGLT 10%, DBA 10%

**Constraint check:**
- Max single: 25% <= 30% OK
- Holdings: 7 (4-12 OK)
- Sector ETFs: 0 <= 3 OK
- Alt ETFs: VNQI, DBA = 2 <= 3 OK
- Volatility: 0.25*7.89 + 0.15*15.64 + 0.15*10.46 + 0.15*15.35 + 0.10*18.22 + 0.10*13.82 + 0.10*12.20
  = 1.97 + 2.35 + 1.57 + 2.30 + 1.82 + 1.38 + 1.22 = 12.61% <= 20% OK

**Return:** 0.25*3.91 + 0.15*7.78 + 0.15*1.85 + 0.15*7.45 + 0.10*(-0.58) + 0.10*(-5.00) + 0.10*10.71
  = 0.98 + 1.17 + 0.28 + 1.12 + (-0.06) + (-0.50) + 1.07 = 4.06%

**Yield:** 0.25*5.88 + 0.15*4.33 + 0.15*5.11 + 0.15*3.44 + 0.10*4.87 + 0.10*4.49 + 0.10*3.35
  = 1.47 + 0.65 + 0.77 + 0.52 + 0.49 + 0.45 + 0.34 = 4.69%

---

## SCENARIO 2: RATE CUTS / RISK-ON — Probability 25%

### Score Adjustments

Rules:
- Equity returns x 1.5, equity vol x 0.8
- Bond yields x 0.5 (note: "yields" here means dividend_yield for bonds)
- Sector returns x 1.4
- Override: VGLT return -> +10.0%, VGT return -> base x 1.8

**Equity (US Equity + Intl Equity) — returns x1.5, vol x0.8:**

| Ticker | Base Ret | Adj Ret | Base Vol | Adj Vol | Yield |
|--------|----------|---------|----------|---------|-------|
| VOO | 11.98 | 17.97 | 15.63 | 12.50 | 1.19 |
| VUG | 12.23 | 18.35 | 19.84 | 15.87 | 0.46 |
| VTV | 10.35 | 15.53 | 14.46 | 11.57 | 2.02 |
| VO | 6.72 | 10.08 | 17.14 | 13.71 | 1.51 |
| VB | 5.96 | 8.94 | 19.05 | 15.24 | 1.34 |
| SCHD | 7.45 | 11.18 | 15.35 | 12.28 | 3.44 |
| VEA | 8.82 | 13.23 | 16.76 | 13.41 | 2.94 |
| VWO | 4.49 | 6.74 | 15.38 | 12.30 | 2.71 |
| VGK | 8.47 | 12.71 | 18.14 | 14.51 | 3.01 |
| EWJ | 7.78 | 11.67 | 15.64 | 12.51 | 4.33 |
| MCHI | -4.96 | -7.44 | 28.65 | 22.92 | 2.27 |

**Bonds — yields x0.5 (dividend yield halved):**

| Ticker | Base Ret | Adj Ret | Vol | Base Yld | Adj Yld |
|--------|----------|---------|-----|----------|---------|
| BND | 0.23 | 0.23 | 6.51 | 3.91 | 1.96 |
| VGSH | 1.83 | 1.83 | 2.20 | 3.95 | 1.98 |
| VGLT | -5.00 | **10.00** (override) | 13.82 | 4.49 | 2.25 |
| TIP | 1.06 | 1.06 | 6.63 | 3.45 | 1.73 |
| HYG | 3.91 | 3.91 | 7.89 | 5.88 | 2.94 |
| EMB | 1.85 | 1.85 | 10.46 | 5.11 | 2.56 |

**Sectors — returns x1.4, then VGT override:**

| Ticker | Base Ret | x1.4 | Final Ret | Vol | Yield |
|--------|----------|------|-----------|-----|-------|
| VGT | 16.19 | 22.67 | **29.14** (base x1.8 = 16.19*1.8) | 21.47 | 0.44 |
| VHT | 4.24 | 5.94 | 5.94 | 14.83 | 1.72 |
| VDE | 22.08 | 30.91 | 30.91 | 26.59 | 2.27 |
| VFH | 8.41 | 11.77 | 11.77 | 19.10 | 1.61 |
| VPU | 10.60 | 14.84 | 14.84 | 16.83 | 2.57 |
| VDC | 6.52 | 9.13 | 9.13 | 13.92 | 2.15 |
| VOX | 7.69 | 10.77 | 10.77 | 19.08 | 1.05 |

**Alternatives — unchanged:**

| Ticker | Return | Vol | Yield |
|--------|--------|-----|-------|
| VNQ | 2.39 | 19.67 | 3.93 |
| VNQI | -0.58 | 18.22 | 4.87 |
| GLD | 19.88 | 15.91 | 0.00 |
| GSG | 15.86 | 19.40 | 0.00 |
| DBA | 10.71 | 12.20 | 3.35 |
| IGF | 11.11 | 15.32 | 2.96 |

### Portfolio Construction — Scenario 2

Top returns: VDE 30.91, VGT 29.14, GLD 19.88, VUG 18.35, VOO 17.97, GSG 15.86, VTV 15.53, VPU 14.84, VEA 13.23, VGK 12.71, SCHD 11.18, EWJ 11.67, IGF 11.11, DBA 10.71, VGLT 10.00

#### Growth Portfolio (S2)

Holdings: VGT 30%, VOO 20%, VUG 20%, VGLT 15%, VDE 15%

**Vol:** 0.30*21.47 + 0.20*12.50 + 0.20*15.87 + 0.15*13.82 + 0.15*26.59
  = 6.44 + 2.50 + 3.17 + 2.07 + 3.99 = 18.17% <= 20% OK

**Return:** 0.30*29.14 + 0.20*17.97 + 0.20*18.35 + 0.15*10.00 + 0.15*30.91
  = 8.74 + 3.59 + 3.67 + 1.50 + 4.64 = 22.14%

**Yield:** 0.30*0.44 + 0.20*1.19 + 0.20*0.46 + 0.15*2.25 + 0.15*2.27
  = 0.13 + 0.24 + 0.09 + 0.34 + 0.34 = 1.14%

**Constraints:** Sectors: VGT, VDE = 2 OK; Alts: 0 OK; Holdings: 5 OK

#### Balanced Portfolio (S2)

Holdings: VOO 25%, VGT 15%, GLD 15%, VGLT 15%, VEA 10%, SCHD 10%, IGF 10%

**Vol:** 0.25*12.50 + 0.15*21.47 + 0.15*15.91 + 0.15*13.82 + 0.10*13.41 + 0.10*12.28 + 0.10*15.32
  = 3.13 + 3.22 + 2.39 + 2.07 + 1.34 + 1.23 + 1.53 = 14.91% <= 20% OK

**Return:** 0.25*17.97 + 0.15*29.14 + 0.15*19.88 + 0.15*10.00 + 0.10*13.23 + 0.10*11.18 + 0.10*11.11
  = 4.49 + 4.37 + 2.98 + 1.50 + 1.32 + 1.12 + 1.11 = 16.89%

**Yield:** 0.25*1.19 + 0.15*0.44 + 0.15*0.00 + 0.15*2.25 + 0.10*2.94 + 0.10*3.44 + 0.10*2.96
  = 0.30 + 0.07 + 0.00 + 0.34 + 0.29 + 0.34 + 0.30 = 1.64%

**Constraints:** Sectors: VGT = 1 OK; Alts: GLD, IGF = 2 OK; Holdings: 7 OK

#### Income Portfolio (S2)

Holdings: SCHD 20%, EWJ 15%, VTV 15%, HYG 15%, VGLT 10%, DBA 15%, VPU 10%

**Vol:** 0.20*12.28 + 0.15*12.51 + 0.15*11.57 + 0.15*7.89 + 0.10*13.82 + 0.15*12.20 + 0.10*16.83
  = 2.46 + 1.88 + 1.74 + 1.18 + 1.38 + 1.83 + 1.68 = 12.15% <= 20% OK

**Return:** 0.20*11.18 + 0.15*11.67 + 0.15*15.53 + 0.15*3.91 + 0.10*10.00 + 0.15*10.71 + 0.10*14.84
  = 2.24 + 1.75 + 2.33 + 0.59 + 1.00 + 1.61 + 1.48 = 11.00%

**Yield:** 0.20*3.44 + 0.15*4.33 + 0.15*2.02 + 0.15*2.94 + 0.10*2.25 + 0.15*3.35 + 0.10*2.57
  = 0.69 + 0.65 + 0.30 + 0.44 + 0.23 + 0.50 + 0.26 = 3.07%

**Constraints:** Sectors: VPU = 1 OK; Alts: DBA = 1 OK; Holdings: 7 OK

#### Safety Portfolio (S2)

Holdings: VGSH 30%, BND 20%, VGLT 20%, TIP 15%, SCHD 15%

**Vol:** 0.30*2.20 + 0.20*6.51 + 0.20*13.82 + 0.15*6.63 + 0.15*12.28
  = 0.66 + 1.30 + 2.76 + 0.99 + 1.84 = 7.55% <= 20% OK

**Return:** 0.30*1.83 + 0.20*0.23 + 0.20*10.00 + 0.15*1.06 + 0.15*11.18
  = 0.55 + 0.05 + 2.00 + 0.16 + 1.68 = 4.44%

**Yield:** 0.30*1.98 + 0.20*1.96 + 0.20*2.25 + 0.15*1.73 + 0.15*3.44
  = 0.59 + 0.39 + 0.45 + 0.26 + 0.52 = 2.21%

**Constraints:** Sectors: 0 OK; Alts: 0 OK; Holdings: 5 OK

#### Max-Return Portfolio (S2)

Holdings: VGT 30%, VDE 25%, VOO 20%, VUG 15%, VGLT 10%

**Vol:** 0.30*21.47 + 0.25*26.59 + 0.20*12.50 + 0.15*15.87 + 0.10*13.82
  = 6.44 + 6.65 + 2.50 + 2.38 + 1.38 = 19.35% <= 20% OK

**Return:** 0.30*29.14 + 0.25*30.91 + 0.20*17.97 + 0.15*18.35 + 0.10*10.00
  = 8.74 + 7.73 + 3.59 + 2.75 + 1.00 = 23.81%

**Yield:** 0.30*0.44 + 0.25*2.27 + 0.20*1.19 + 0.15*0.46 + 0.10*2.25
  = 0.13 + 0.57 + 0.24 + 0.07 + 0.23 = 1.24%

**Constraints:** Sectors: VGT, VDE = 2 OK; Alts: 0 OK; Holdings: 5 OK

---

## SCENARIO 3: RECESSION / RISK-OFF — Probability 20%

### Score Adjustments

Rules:
- Equity returns x 0.2, equity vol x 1.8
- Sector returns x 0.2, sector vol x 1.8
- Alternative returns x 0.5
- Overrides: VGSH ret -> +4.5%, BND ret -> +5.0%, VGLT ret -> +7.0%, HYG ret -> -4.0%, HYG vol -> base x 1.8, EMB ret -> -5.0%, EMB vol -> base x 1.8, GLD ret -> base x 1.3

**Equity — returns x0.2, vol x1.8:**

| Ticker | Base Ret | Adj Ret | Base Vol | Adj Vol | Yield |
|--------|----------|---------|----------|---------|-------|
| VOO | 11.98 | 2.40 | 15.63 | 28.13 | 1.19 |
| VUG | 12.23 | 2.45 | 19.84 | 35.71 | 0.46 |
| VTV | 10.35 | 2.07 | 14.46 | 26.03 | 2.02 |
| VO | 6.72 | 1.34 | 17.14 | 30.85 | 1.51 |
| VB | 5.96 | 1.19 | 19.05 | 34.29 | 1.34 |
| SCHD | 7.45 | 1.49 | 15.35 | 27.63 | 3.44 |
| VEA | 8.82 | 1.76 | 16.76 | 30.17 | 2.94 |
| VWO | 4.49 | 0.90 | 15.38 | 27.68 | 2.71 |
| VGK | 8.47 | 1.69 | 18.14 | 32.65 | 3.01 |
| EWJ | 7.78 | 1.56 | 15.64 | 28.15 | 4.33 |
| MCHI | -4.96 | -0.99 | 28.65 | 51.57 | 2.27 |

**Bonds — overrides applied:**

| Ticker | Base Ret | Adj Ret | Base Vol | Adj Vol | Yield |
|--------|----------|---------|----------|---------|-------|
| BND | 0.23 | **5.00** | 6.51 | 6.51 | 3.91 |
| VGSH | 1.83 | **4.50** | 2.20 | 2.20 | 3.95 |
| VGLT | -5.00 | **7.00** | 13.82 | 13.82 | 4.49 |
| TIP | 1.06 | 1.06 | 6.63 | 6.63 | 3.45 |
| HYG | 3.91 | **-4.00** | 7.89 | **14.20** (7.89x1.8) | 5.88 |
| EMB | 1.85 | **-5.00** | 10.46 | **18.83** (10.46x1.8) | 5.11 |

**Sectors — returns x0.2, vol x1.8:**

| Ticker | Base Ret | Adj Ret | Base Vol | Adj Vol | Yield |
|--------|----------|---------|----------|---------|-------|
| VGT | 16.19 | 3.24 | 21.47 | 38.65 | 0.44 |
| VHT | 4.24 | 0.85 | 14.83 | 26.69 | 1.72 |
| VDE | 22.08 | 4.42 | 26.59 | 47.86 | 2.27 |
| VFH | 8.41 | 1.68 | 19.10 | 34.38 | 1.61 |
| VPU | 10.60 | 2.12 | 16.83 | 30.29 | 2.57 |
| VDC | 6.52 | 1.30 | 13.92 | 25.06 | 2.15 |
| VOX | 7.69 | 1.54 | 19.08 | 34.34 | 1.05 |

**Alternatives — returns x0.5, then GLD override:**

| Ticker | Base Ret | x0.5 | Final Ret | Vol | Yield |
|--------|----------|------|-----------|-----|-------|
| VNQ | 2.39 | 1.20 | 1.20 | 19.67 | 3.93 |
| VNQI | -0.58 | -0.29 | -0.29 | 18.22 | 4.87 |
| GLD | 19.88 | 9.94 | **25.84** (base x1.3 = 19.88*1.3) | 15.91 | 0.00 |
| GSG | 15.86 | 7.93 | 7.93 | 19.40 | 0.00 |
| DBA | 10.71 | 5.36 | 5.36 | 12.20 | 3.35 |
| IGF | 11.11 | 5.56 | 5.56 | 15.32 | 2.96 |

### Portfolio Construction — Scenario 3

In recession, equities and sectors are devastated. Best returns: GLD (25.84), VGLT (7.00), GSG (7.93), IGF (5.56), DBA (5.36), BND (5.00), VGSH (4.50)

#### Growth Portfolio (S3)

Holdings: GLD 25%, VGLT 20%, DBA 15%, IGF 10%, BND 15%, VGSH 15%

**Vol:** 0.25*15.91 + 0.20*13.82 + 0.15*12.20 + 0.10*15.32 + 0.15*6.51 + 0.15*2.20
  = 3.98 + 2.76 + 1.83 + 1.53 + 0.98 + 0.33 = 11.41% <= 20% OK

**Return:** 0.25*25.84 + 0.20*7.00 + 0.15*5.36 + 0.10*5.56 + 0.15*5.00 + 0.15*4.50
  = 6.46 + 1.40 + 0.80 + 0.56 + 0.75 + 0.68 = 10.65%

**Yield:** 0.25*0.00 + 0.20*4.49 + 0.15*3.35 + 0.10*2.96 + 0.15*3.91 + 0.15*3.95
  = 0.00 + 0.90 + 0.50 + 0.30 + 0.59 + 0.59 = 2.88%

**Constraints:** Sectors: 0 OK; Alts: GLD, DBA, IGF = 3 OK; Holdings: 6 OK

#### Balanced Portfolio (S3)

Holdings: VGSH 25%, BND 20%, GLD 20%, TIP 15%, DBA 10%, VDC 10%

**Vol:** 0.25*2.20 + 0.20*6.51 + 0.20*15.91 + 0.15*6.63 + 0.10*12.20 + 0.10*25.06
  = 0.55 + 1.30 + 3.18 + 0.99 + 1.22 + 2.51 = 9.75% <= 20% OK

**Return:** 0.25*4.50 + 0.20*5.00 + 0.20*25.84 + 0.15*1.06 + 0.10*5.36 + 0.10*1.30
  = 1.13 + 1.00 + 5.17 + 0.16 + 0.54 + 0.13 = 8.13%

**Yield:** 0.25*3.95 + 0.20*3.91 + 0.20*0.00 + 0.15*3.45 + 0.10*3.35 + 0.10*2.15
  = 0.99 + 0.78 + 0.00 + 0.52 + 0.34 + 0.22 = 2.85%

**Constraints:** Sectors: VDC = 1 OK; Alts: GLD, DBA = 2 OK; Holdings: 6 OK

#### Income Portfolio (S3)

Holdings: VGSH 25%, BND 20%, VGLT 15%, TIP 15%, SCHD 10%, EWJ 10%, DBA 5%

**Vol:** 0.25*2.20 + 0.20*6.51 + 0.15*13.82 + 0.15*6.63 + 0.10*27.63 + 0.10*28.15 + 0.05*12.20
  = 0.55 + 1.30 + 2.07 + 0.99 + 2.76 + 2.82 + 0.61 = 11.10% <= 20% OK

**Return:** 0.25*4.50 + 0.20*5.00 + 0.15*7.00 + 0.15*1.06 + 0.10*1.49 + 0.10*1.56 + 0.05*5.36
  = 1.13 + 1.00 + 1.05 + 0.16 + 0.15 + 0.16 + 0.27 = 3.92%

**Yield:** 0.25*3.95 + 0.20*3.91 + 0.15*4.49 + 0.15*3.45 + 0.10*3.44 + 0.10*4.33 + 0.05*3.35
  = 0.99 + 0.78 + 0.67 + 0.52 + 0.34 + 0.43 + 0.17 = 3.90%

**Constraints:** Sectors: 0 OK; Alts: DBA = 1 OK; Holdings: 7 OK

#### Safety Portfolio (S3)

Holdings: VGSH 30%, BND 30%, TIP 25%, VGLT 15%

**Vol:** 0.30*2.20 + 0.30*6.51 + 0.25*6.63 + 0.15*13.82
  = 0.66 + 1.95 + 1.66 + 2.07 = 6.34% <= 20% OK

**Return:** 0.30*4.50 + 0.30*5.00 + 0.25*1.06 + 0.15*7.00
  = 1.35 + 1.50 + 0.27 + 1.05 = 4.17%

**Yield:** 0.30*3.95 + 0.30*3.91 + 0.25*3.45 + 0.15*4.49
  = 1.19 + 1.17 + 0.86 + 0.67 = 3.89%

**Constraints:** Sectors: 0 OK; Alts: 0 OK; Holdings: 4 OK (minimum)

#### Max-Return Portfolio (S3)

Holdings: GLD 30%, VGLT 25%, DBA 15%, IGF 15%, BND 15%

**Vol:** 0.30*15.91 + 0.25*13.82 + 0.15*12.20 + 0.15*15.32 + 0.15*6.51
  = 4.77 + 3.46 + 1.83 + 2.30 + 0.98 = 13.34% <= 20% OK

**Return:** 0.30*25.84 + 0.25*7.00 + 0.15*5.36 + 0.15*5.56 + 0.15*5.00
  = 7.75 + 1.75 + 0.80 + 0.83 + 0.75 = 11.88%

**Yield:** 0.30*0.00 + 0.25*4.49 + 0.15*3.35 + 0.15*2.96 + 0.15*3.91
  = 0.00 + 1.12 + 0.50 + 0.44 + 0.59 = 2.65%

**Constraints:** Sectors: 0 OK; Alts: GLD, DBA, IGF = 3 OK; Holdings: 5 OK

---

## SCENARIO 4: INFLATION SURGE — Probability 25%

### Score Adjustments

Rules:
- Equity returns x 0.6, equity vol x 1.3
- Bond returns x 0.3, bond yields x 1.2
- Overrides: GLD ret -> base x 2.0, GSG ret -> base x 2.0, DBA ret -> base x 2.0, TIP ret -> +8.0%, BND ret -> -5.0%, VGLT ret -> -12.0%, VDE ret -> base x 1.5

**Equity — returns x0.6, vol x1.3:**

| Ticker | Base Ret | Adj Ret | Base Vol | Adj Vol | Yield |
|--------|----------|---------|----------|---------|-------|
| VOO | 11.98 | 7.19 | 15.63 | 20.32 | 1.19 |
| VUG | 12.23 | 7.34 | 19.84 | 25.79 | 0.46 |
| VTV | 10.35 | 6.21 | 14.46 | 18.80 | 2.02 |
| VO | 6.72 | 4.03 | 17.14 | 22.28 | 1.51 |
| VB | 5.96 | 3.58 | 19.05 | 24.77 | 1.34 |
| SCHD | 7.45 | 4.47 | 15.35 | 19.96 | 3.44 |
| VEA | 8.82 | 5.29 | 16.76 | 21.79 | 2.94 |
| VWO | 4.49 | 2.69 | 15.38 | 19.99 | 2.71 |
| VGK | 8.47 | 5.08 | 18.14 | 23.58 | 3.01 |
| EWJ | 7.78 | 4.67 | 15.64 | 20.33 | 4.33 |
| MCHI | -4.96 | -2.98 | 28.65 | 37.25 | 2.27 |

**Bonds — returns x0.3, yields x1.2, then overrides:**

| Ticker | Base Ret | x0.3 | Final Ret | Vol | Base Yld | Adj Yld |
|--------|----------|------|-----------|-----|----------|---------|
| BND | 0.23 | 0.07 | **-5.00** | 6.51 | 3.91 | 4.69 |
| VGSH | 1.83 | 0.55 | 0.55 | 2.20 | 3.95 | 4.74 |
| VGLT | -5.00 | -1.50 | **-12.00** | 13.82 | 4.49 | 5.39 |
| TIP | 1.06 | 0.32 | **8.00** | 6.63 | 3.45 | 4.14 |
| HYG | 3.91 | 1.17 | 1.17 | 7.89 | 5.88 | 7.06 |
| EMB | 1.85 | 0.56 | 0.56 | 10.46 | 5.11 | 6.13 |

**Sectors — no sector-specific adjustments specified, so unchanged, except VDE override:**

| Ticker | Ret | Final Ret | Vol | Yield |
|--------|-----|-----------|-----|-------|
| VGT | 16.19 | 16.19 | 21.47 | 0.44 |
| VHT | 4.24 | 4.24 | 14.83 | 1.72 |
| VDE | 22.08 | **33.12** (base x 1.5) | 26.59 | 2.27 |
| VFH | 8.41 | 8.41 | 19.10 | 1.61 |
| VPU | 10.60 | 10.60 | 16.83 | 2.57 |
| VDC | 6.52 | 6.52 | 13.92 | 2.15 |
| VOX | 7.69 | 7.69 | 19.08 | 1.05 |

**Alternatives — commodity overrides:**

| Ticker | Base Ret | Final Ret | Vol | Yield |
|--------|----------|-----------|-----|-------|
| VNQ | 2.39 | 2.39 | 19.67 | 3.93 |
| VNQI | -0.58 | -0.58 | 18.22 | 4.87 |
| GLD | 19.88 | **39.76** (base x 2.0) | 15.91 | 0.00 |
| GSG | 15.86 | **31.72** (base x 2.0) | 19.40 | 0.00 |
| DBA | 10.71 | **21.42** (base x 2.0) | 12.20 | 3.35 |
| IGF | 11.11 | 11.11 | 15.32 | 2.96 |

### Portfolio Construction — Scenario 4

Top returns: GLD (39.76), VDE (33.12), GSG (31.72), DBA (21.42), VGT (16.19), IGF (11.11), VPU (10.60), TIP (8.00)

#### Growth Portfolio (S4)

Holdings: GLD 30%, GSG 20%, VDE 20%, DBA 15%, TIP 15%

**Vol:** 0.30*15.91 + 0.20*19.40 + 0.20*26.59 + 0.15*12.20 + 0.15*6.63
  = 4.77 + 3.88 + 5.32 + 1.83 + 0.99 = 16.79% <= 20% OK

**Return:** 0.30*39.76 + 0.20*31.72 + 0.20*33.12 + 0.15*21.42 + 0.15*8.00
  = 11.93 + 6.34 + 6.62 + 3.21 + 1.20 = 29.30%

**Yield:** 0.30*0.00 + 0.20*0.00 + 0.20*2.27 + 0.15*3.35 + 0.15*4.14
  = 0.00 + 0.00 + 0.45 + 0.50 + 0.62 = 1.57%

**Constraints:** Sectors: VDE = 1 OK; Alts: GLD, GSG, DBA = 3 OK; Holdings: 5 OK

#### Balanced Portfolio (S4)

Holdings: GLD 25%, TIP 20%, DBA 15%, VDE 15%, SCHD 10%, VGSH 15%

**Vol:** 0.25*15.91 + 0.20*6.63 + 0.15*12.20 + 0.15*26.59 + 0.10*19.96 + 0.15*2.20
  = 3.98 + 1.33 + 1.83 + 3.99 + 2.00 + 0.33 = 13.46% <= 20% OK

**Return:** 0.25*39.76 + 0.20*8.00 + 0.15*21.42 + 0.15*33.12 + 0.10*4.47 + 0.15*0.55
  = 9.94 + 1.60 + 3.21 + 4.97 + 0.45 + 0.08 = 20.25%

**Yield:** 0.25*0.00 + 0.20*4.14 + 0.15*3.35 + 0.15*2.27 + 0.10*3.44 + 0.15*4.74
  = 0.00 + 0.83 + 0.50 + 0.34 + 0.34 + 0.71 = 2.72%

**Constraints:** Sectors: VDE = 1 OK; Alts: GLD, DBA = 2 OK; Holdings: 6 OK

#### Income Portfolio (S4)

Holdings: TIP 25%, DBA 20%, SCHD 15%, EWJ 10%, VGSH 15%, VPU 15%

**Vol:** 0.25*6.63 + 0.20*12.20 + 0.15*19.96 + 0.10*20.33 + 0.15*2.20 + 0.15*16.83
  = 1.66 + 2.44 + 2.99 + 2.03 + 0.33 + 2.52 = 11.97% <= 20% OK

**Return:** 0.25*8.00 + 0.20*21.42 + 0.15*4.47 + 0.10*4.67 + 0.15*0.55 + 0.15*10.60
  = 2.00 + 4.28 + 0.67 + 0.47 + 0.08 + 1.59 = 9.09%

**Yield:** 0.25*4.14 + 0.20*3.35 + 0.15*3.44 + 0.10*4.33 + 0.15*4.74 + 0.15*2.57
  = 1.04 + 0.67 + 0.52 + 0.43 + 0.71 + 0.39 = 3.76%

**Constraints:** Sectors: VPU = 1 OK; Alts: DBA = 1 OK; Holdings: 6 OK

#### Safety Portfolio (S4)

Holdings: VGSH 30%, TIP 30%, DBA 15%, BND 10%, SCHD 15%

**Vol:** 0.30*2.20 + 0.30*6.63 + 0.15*12.20 + 0.10*6.51 + 0.15*19.96
  = 0.66 + 1.99 + 1.83 + 0.65 + 2.99 = 8.12% <= 20% OK

**Return:** 0.30*0.55 + 0.30*8.00 + 0.15*21.42 + 0.10*(-5.00) + 0.15*4.47
  = 0.17 + 2.40 + 3.21 + (-0.50) + 0.67 = 5.95%

**Yield:** 0.30*4.74 + 0.30*4.14 + 0.15*3.35 + 0.10*4.69 + 0.15*3.44
  = 1.42 + 1.24 + 0.50 + 0.47 + 0.52 = 4.15%

**Constraints:** Sectors: 0 OK; Alts: DBA = 1 OK; Holdings: 5 OK

#### Max-Return Portfolio (S4)

Holdings: GLD 30%, GSG 25%, VDE 25%, DBA 20%

**Vol:** 0.30*15.91 + 0.25*19.40 + 0.25*26.59 + 0.20*12.20
  = 4.77 + 4.85 + 6.65 + 2.44 = 18.71% <= 20% OK

**Return:** 0.30*39.76 + 0.25*31.72 + 0.25*33.12 + 0.20*21.42
  = 11.93 + 7.93 + 8.28 + 4.28 = 32.42%

**Yield:** 0.30*0.00 + 0.25*0.00 + 0.25*2.27 + 0.20*3.35
  = 0.00 + 0.00 + 0.57 + 0.67 = 1.24%

**Constraints:** Sectors: VDE = 1 OK; Alts: GLD, GSG, DBA = 3 OK; Holdings: 4 OK (minimum)

---

## Summary Table — All Scenarios

### Scenario 1: Base Case
| Portfolio | Return% | Vol% | Yield% | Holdings |
|-----------|---------|------|--------|----------|
| Growth | 15.31 | 19.58 | 1.08 | 6 |
| Balanced | 10.85 | 14.37 | 2.16 | 8 |
| Income | 7.24 | 13.45 | 3.81 | 8 |
| Safety | 2.98 | 7.37 | 3.58 | 5 |
| Max-Return | 16.61 | 19.59 | 1.02 | 6 |
| Max-Yield | 4.06 | 12.61 | 4.69 | 7 |

### Scenario 2: Rate Cuts / Risk-On
| Portfolio | Return% | Vol% | Yield% | Holdings |
|-----------|---------|------|--------|----------|
| Growth | 22.14 | 18.17 | 1.14 | 5 |
| Balanced | 16.89 | 14.91 | 1.64 | 7 |
| Income | 11.00 | 12.15 | 3.07 | 7 |
| Safety | 4.44 | 7.55 | 2.21 | 5 |
| Max-Return | 23.81 | 19.35 | 1.24 | 5 |

### Scenario 3: Recession / Risk-Off
| Portfolio | Return% | Vol% | Yield% | Holdings |
|-----------|---------|------|--------|----------|
| Growth | 10.65 | 11.41 | 2.88 | 6 |
| Balanced | 8.13 | 9.75 | 2.85 | 6 |
| Income | 3.92 | 11.10 | 3.90 | 7 |
| Safety | 4.17 | 6.34 | 3.89 | 4 |
| Max-Return | 11.88 | 13.34 | 2.65 | 5 |

### Scenario 4: Inflation Surge
| Portfolio | Return% | Vol% | Yield% | Holdings |
|-----------|---------|------|--------|----------|
| Growth | 29.30 | 16.79 | 1.57 | 5 |
| Balanced | 20.25 | 13.46 | 2.72 | 6 |
| Income | 9.09 | 11.97 | 3.76 | 6 |
| Safety | 5.95 | 8.12 | 4.15 | 5 |
| Max-Return | 32.42 | 18.71 | 1.24 | 4 |

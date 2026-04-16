# Curated Portfolio Strategies

## Growth

**Objective**: Maximize capital appreciation, accepting higher volatility.

| Metric | Value |
|--------|-------|
| Expected Return | 16.34% |
| Volatility | 13.27% |
| Dividend Yield | 2.09% |
| Holdings | 8 |

### Allocations

| ETF | Ticker | Weight | Group |
|-----|--------|--------|-------|
| Energy | VDE | 30% | Sectors |
| Gold | GLD | 30% | Alternatives |
| Infrastructure | IGF | 21% | Alternatives |
| High Yield Bond | HYG | 7% | Bonds |
| Agriculture | DBA | 5% | Alternatives |
| Japan | EWJ | 4% | Intl Equity |
| Dividend Quality | SCHD | 2% | US Equity |
| Technology | VGT | 1% | Sectors |

### Binding Constraints
- **Max allocation (30%)**: VDE and GLD both at cap
- **Alternative ETFs <= 3**: GLD, DBA, IGF = 3 alternatives (at limit)
- **Sector ETFs <= 3**: VDE, VGT = 2 sectors (not binding)

### Strategy Notes
- Concentrated in energy (VDE) and gold (GLD), both top performers over the 5-year period
- IGF (Infrastructure) provides a strong return backbone with moderate volatility
- HYG adds a small fixed-income buffer while preserving return
- Volatility at 13.27% is well below the 20% constraint, reflecting the diversification benefit from low-correlation assets (gold vs energy)

---

## Balanced

**Objective**: Near the ideal point -- good return, moderate risk, decent income.

| Metric | Value |
|--------|-------|
| Expected Return | 9.38% |
| Volatility | 7.52% |
| Dividend Yield | 3.66% |
| Holdings | 9 |

### Allocations

| ETF | Ticker | Weight | Group |
|-----|--------|--------|-------|
| High Yield Bond | HYG | 30% | Bonds |
| Short-Term Treasury | VGSH | 26% | Bonds |
| Energy | VDE | 20% | Sectors |
| Gold | GLD | 11% | Alternatives |
| US Large Cap Value | VTV | 3% | US Equity |
| Japan | EWJ | 3% | Intl Equity |
| Infrastructure | IGF | 3% | Alternatives |
| Dividend Quality | SCHD | 2% | US Equity |
| Agriculture | DBA | 2% | Alternatives |

### Binding Constraints
- **Max allocation (30%)**: HYG at cap
- **Alternative ETFs <= 3**: GLD, IGF, DBA = 3 alternatives (at limit)
- **Sector ETFs <= 3**: VDE = 1 sector (not binding)

### Strategy Notes
- This is the "ideal point closest" solution identified by Frontier's balanced-solution algorithm
- VGSH (26%) provides a large low-volatility anchor, reducing portfolio risk dramatically
- HYG (30%) contributes yield (5.88%) while keeping volatility moderate (7.89% standalone)
- VDE (20%) is the primary return engine
- The quadratic volatility of 7.52% is much lower than the weighted-average of the individual ETFs, demonstrating significant diversification benefit from the negative equity-bond correlations

---

## Income

**Objective**: Maximize dividend yield while keeping volatility reasonable.

| Metric | Value |
|--------|-------|
| Expected Return | 4.43% |
| Volatility | 7.02% |
| Dividend Yield | 4.95% |
| Holdings | 9 |

### Allocations

| ETF | Ticker | Weight | Group |
|-----|--------|--------|-------|
| Japan | EWJ | 30% | Intl Equity |
| High Yield Bond | HYG | 30% | Bonds |
| EM Bond | EMB | 30% | Bonds |
| US Aggregate Bond | BND | 2% | Bonds |
| Short-Term Treasury | VGSH | 2% | Bonds |
| Long-Term Treasury | VGLT | 2% | Bonds |
| Intl REITs | VNQI | 2% | Alternatives |
| Financials | VFH | 1% | Sectors |
| Agriculture | DBA | 1% | Alternatives |

### Binding Constraints
- **Max allocation (30%)**: EWJ, HYG, and EMB all at cap
- **Alternative ETFs <= 3**: VNQI, DBA = 2 alternatives (not binding)
- **Sector ETFs <= 3**: VFH = 1 sector (not binding)

### Strategy Notes
- Triple 30% allocation to the three highest-yielding accessible ETFs: EWJ (4.33%), HYG (5.88%), EMB (5.11%)
- The remaining 10% goes to bonds and small satellite positions
- Volatility at 7.02% is moderate despite the heavy EWJ position, because EWJ has negative correlation with the bond positions
- This is the maximum yield solution on the entire Pareto frontier at 4.95%
- Return at 4.43% is relatively low -- the cost of maximizing income

---

## Safety

**Objective**: Minimize portfolio volatility (capital preservation).

| Metric | Value |
|--------|-------|
| Expected Return | 3.35% |
| Volatility | 4.23% |
| Dividend Yield | 4.39% |
| Holdings | 10 |

### Allocations

| ETF | Ticker | Weight | Group |
|-----|--------|--------|-------|
| Short-Term Treasury | VGSH | 30% | Bonds |
| High Yield Bond | HYG | 30% | Bonds |
| US Aggregate Bond | BND | 23% | Bonds |
| Japan | EWJ | 7% | Intl Equity |
| US Large Cap Value | VTV | 4% | US Equity |
| Agriculture | DBA | 2% | Alternatives |
| Dividend Quality | SCHD | 1% | US Equity |
| Consumer Staples | VDC | 1% | Sectors |
| Gold | GLD | 1% | Alternatives |
| Infrastructure | IGF | 1% | Alternatives |

### Binding Constraints
- **Max allocation (30%)**: VGSH and HYG at cap
- **Alternative ETFs <= 3**: DBA, GLD, IGF = 3 alternatives (at limit)
- **Sector ETFs <= 3**: VDC = 1 sector (not binding)

### Strategy Notes
- 83% in fixed income (VGSH 30%, HYG 30%, BND 23%), the primary volatility reduction mechanism
- VGSH has the lowest standalone volatility at 2.2% and negligible correlation with equities
- The 4.23% portfolio volatility is a remarkable result -- well below the weighted average, thanks to the negative covariance between bonds and the small equity positions
- Despite the safety focus, yield is strong at 4.39% because bond ETFs (VGSH 3.95%, HYG 5.88%, BND 3.91%) are high-yielding
- Return is the main sacrifice at 3.35%

---

## Shared Holdings Across All Four Strategies

Three ETFs appear in all four curated strategies:
- **EWJ** (Japan): High yield (4.33%), moderate return (7.78%), and negative correlation with bonds make it a universal diversifier
- **HYG** (High Yield Bond): Highest yield in the universe (5.88%) with moderate volatility (7.89%)
- **DBA** (Agriculture): Low correlation with other asset classes and decent yield (3.35%)

## Key Differentiators

- **VDE** (Energy): Present in Growth and Balanced but absent from Income and Safety. It is the primary return driver.
- **GLD** (Gold): Present in Growth, Balanced, and Safety but absent from Income. It provides uncorrelated returns.
- **VGSH/BND** (Short/Aggregate Bonds): Dominant in Safety and Balanced, absent from Growth. They are the volatility anchors.
- **EMB** (EM Bonds): Present in Income but not in Growth or Balanced. High yield (5.11%) but negative return correlation with equities.

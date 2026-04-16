# Curated Portfolio Strategies

## Growth

**Objective:** Maximize expected return while staying within the 20% vol ceiling.

| Metric | Value |
|--------|-------|
| Expected Return | 16.28% |
| Volatility (wtd avg) | 17.86% |
| Dividend Yield | 1.28% |
| Holdings | 6 |

| ETF | Allocation | Group | Return% | Vol% | Yield% |
|-----|-----------|-------|---------|------|--------|
| GLD | 30% | Alternatives | 19.88 | 15.91 | 0.00 |
| VOO | 20% | US Equity | 11.98 | 15.63 | 1.19 |
| VDE | 15% | Sectors | 22.08 | 26.59 | 2.27 |
| VGT | 15% | Sectors | 16.19 | 21.47 | 0.44 |
| IGF | 10% | Alternatives | 11.11 | 15.32 | 2.96 |
| DBA | 10% | Alternatives | 10.71 | 12.20 | 3.35 |

**Binding constraints:**
- Max allocation (GLD at 30% cap)
- Vol ceiling has moderate headroom (17.86 vs 20.00)
- Alternatives at 3/3 limit

**Arithmetic verification:**
- Return: 0.30x19.88 + 0.20x11.98 + 0.15x22.08 + 0.15x16.19 + 0.10x11.11 + 0.10x10.71 = 5.964 + 2.396 + 3.312 + 2.4285 + 1.111 + 1.071 = 16.28
- Vol: 0.30x15.91 + 0.20x15.63 + 0.15x26.59 + 0.15x21.47 + 0.10x15.32 + 0.10x12.20 = 4.773 + 3.126 + 3.9885 + 3.2205 + 1.532 + 1.220 = 17.86
- Yield: 0.30x0.00 + 0.20x1.19 + 0.15x2.27 + 0.15x0.44 + 0.10x2.96 + 0.10x3.35 = 0 + 0.238 + 0.3405 + 0.066 + 0.296 + 0.335 = 1.28

---

## Balanced

**Objective:** Moderate return with diversification across asset classes and reasonable yield.

| Metric | Value |
|--------|-------|
| Expected Return | 10.47% |
| Volatility (wtd avg) | 13.02% |
| Dividend Yield | 2.55% |
| Holdings | 8 |

| ETF | Allocation | Group | Return% | Vol% | Yield% |
|-----|-----------|-------|---------|------|--------|
| VOO | 20% | US Equity | 11.98 | 15.63 | 1.19 |
| GLD | 15% | Alternatives | 19.88 | 15.91 | 0.00 |
| IGF | 15% | Alternatives | 11.11 | 15.32 | 2.96 |
| DBA | 10% | Alternatives | 10.71 | 12.20 | 3.35 |
| VTV | 10% | US Equity | 10.35 | 14.46 | 2.02 |
| SCHD | 10% | US Equity | 7.45 | 15.35 | 3.44 |
| HYG | 10% | Bonds | 3.91 | 7.89 | 5.88 |
| VGSH | 10% | Bonds | 1.83 | 2.20 | 3.95 |

**Binding constraints:**
- Alternatives at 3/3 limit
- No other constraints are close to binding

**Arithmetic verification:**
- Return: 0.20x11.98 + 0.15x19.88 + 0.15x11.11 + 0.10x10.71 + 0.10x10.35 + 0.10x7.45 + 0.10x3.91 + 0.10x1.83 = 2.396 + 2.982 + 1.6665 + 1.071 + 1.035 + 0.745 + 0.391 + 0.183 = 10.47
- Vol: 0.20x15.63 + 0.15x15.91 + 0.15x15.32 + 0.10x12.20 + 0.10x14.46 + 0.10x15.35 + 0.10x7.89 + 0.10x2.20 = 3.126 + 2.3865 + 2.298 + 1.220 + 1.446 + 1.535 + 0.789 + 0.220 = 13.02
- Yield: 0.20x1.19 + 0.15x0.00 + 0.15x2.96 + 0.10x3.35 + 0.10x2.02 + 0.10x3.44 + 0.10x5.88 + 0.10x3.95 = 0.238 + 0 + 0.444 + 0.335 + 0.202 + 0.344 + 0.588 + 0.395 = 2.55

---

## Income

**Objective:** Maximize dividend yield while maintaining positive expected returns.

| Metric | Value |
|--------|-------|
| Expected Return | 2.69% |
| Volatility (wtd avg) | 10.57% |
| Dividend Yield | 4.84% |
| Holdings | 7 |

| ETF | Allocation | Group | Return% | Vol% | Yield% |
|-----|-----------|-------|---------|------|--------|
| HYG | 30% | Bonds | 3.91 | 7.89 | 5.88 |
| EMB | 15% | Bonds | 1.85 | 10.46 | 5.11 |
| VGSH | 15% | Bonds | 1.83 | 2.20 | 3.95 |
| EWJ | 10% | Intl Equity | 7.78 | 15.64 | 4.33 |
| VNQI | 10% | Alternatives | -0.58 | 18.22 | 4.87 |
| SCHD | 10% | US Equity | 7.45 | 15.35 | 3.44 |
| VGLT | 10% | Bonds | -5.00 | 13.82 | 4.49 |

**Binding constraints:**
- Max allocation (HYG at 30% cap)
- Yield would benefit from more HYG but cap prevents it

**Arithmetic verification:**
- Return: 0.30x3.91 + 0.15x1.85 + 0.15x1.83 + 0.10x7.78 + 0.10x(-0.58) + 0.10x7.45 + 0.10x(-5.00) = 1.173 + 0.2775 + 0.2745 + 0.778 - 0.058 + 0.745 - 0.500 = 2.69
- Vol: 0.30x7.89 + 0.15x10.46 + 0.15x2.20 + 0.10x15.64 + 0.10x18.22 + 0.10x15.35 + 0.10x13.82 = 2.367 + 1.569 + 0.330 + 1.564 + 1.822 + 1.535 + 1.382 = 10.57
- Yield: 0.30x5.88 + 0.15x5.11 + 0.15x3.95 + 0.10x4.33 + 0.10x4.87 + 0.10x3.44 + 0.10x4.49 = 1.764 + 0.7665 + 0.5925 + 0.433 + 0.487 + 0.344 + 0.449 = 4.84

---

## Safety

**Objective:** Minimize volatility while earning meaningful yield and keeping return positive.

| Metric | Value |
|--------|-------|
| Expected Return | 2.80% |
| Volatility (wtd avg) | 6.45% |
| Dividend Yield | 4.07% |
| Holdings | 6 |

| ETF | Allocation | Group | Return% | Vol% | Yield% |
|-----|-----------|-------|---------|------|--------|
| VGSH | 30% | Bonds | 1.83 | 2.20 | 3.95 |
| BND | 25% | Bonds | 0.23 | 6.51 | 3.91 |
| TIP | 15% | Bonds | 1.06 | 6.63 | 3.45 |
| HYG | 15% | Bonds | 3.91 | 7.89 | 5.88 |
| DBA | 10% | Alternatives | 10.71 | 12.20 | 3.35 |
| SCHD | 5% | US Equity | 7.45 | 15.35 | 3.44 |

**Binding constraints:**
- Max allocation (VGSH at 30% cap) -- vol would be even lower with more VGSH
- Near minimum holdings (6 vs minimum of 4)

**Arithmetic verification:**
- Return: 0.30x1.83 + 0.25x0.23 + 0.15x1.06 + 0.15x3.91 + 0.10x10.71 + 0.05x7.45 = 0.549 + 0.0575 + 0.159 + 0.5865 + 1.071 + 0.3725 = 2.80
- Vol: 0.30x2.20 + 0.25x6.51 + 0.15x6.63 + 0.15x7.89 + 0.10x12.20 + 0.05x15.35 = 0.660 + 1.6275 + 0.9945 + 1.1835 + 1.220 + 0.7675 = 6.45
- Yield: 0.30x3.95 + 0.25x3.91 + 0.15x3.45 + 0.15x5.88 + 0.10x3.35 + 0.05x3.44 = 1.185 + 0.9775 + 0.5175 + 0.882 + 0.335 + 0.172 = 4.07

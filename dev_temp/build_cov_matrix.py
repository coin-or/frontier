"""Build an estimated 30×30 covariance matrix for the ETF portfolio demo.

Uses asset-class-level correlation estimates + individual ETF volatilities.
Σ = diag(σ) × R × diag(σ) where R is the correlation matrix.

Within-group correlations are high (0.85-0.95), cross-group correlations
reflect well-known asset class relationships.
"""

import json
from pathlib import Path

# Load ETF data
data_path = Path(__file__).parent / "etf_cache" / "etf_30_consolidated.json"
etfs = json.loads(data_path.read_text())

tickers = [e["ticker"] for e in etfs]
groups = {e["ticker"]: e["group"] for e in etfs}
vols = {e["ticker"]: e["ann_volatility_5yr_pct"] for e in etfs}
categories = {e["ticker"]: e["category"] for e in etfs}

# --- Correlation structure ---
# Cross-group correlation estimates (symmetric)
# Based on typical long-run relationships
GROUP_CORR = {
    ("US Equity", "US Equity"): 0.90,
    ("US Equity", "Intl Equity"): 0.75,
    ("US Equity", "Bonds"): -0.15,
    ("US Equity", "Sectors"): 0.80,
    ("US Equity", "Alternatives"): 0.35,
    ("Intl Equity", "Intl Equity"): 0.85,
    ("Intl Equity", "Bonds"): -0.10,
    ("Intl Equity", "Sectors"): 0.65,
    ("Intl Equity", "Alternatives"): 0.40,
    ("Bonds", "Bonds"): 0.70,
    ("Bonds", "Sectors"): -0.10,
    ("Bonds", "Alternatives"): 0.10,
    ("Sectors", "Sectors"): 0.65,
    ("Sectors", "Alternatives"): 0.30,
    ("Alternatives", "Alternatives"): 0.40,
}

# Category-level overrides for known special cases
CATEGORY_OVERRIDES = {
    # Gold is a diversifier — low/negative correlation with equities
    ("Gold", "US Large Cap Blend"): 0.05,
    ("Gold", "US Large Cap Growth"): 0.00,
    ("Gold", "US Large Cap Value"): 0.10,
    ("Gold", "Technology"): -0.05,
    # Short-term treasuries are nearly uncorrelated with everything
    ("Short-Term Treasury", "US Large Cap Blend"): -0.05,
    ("Short-Term Treasury", "US Large Cap Growth"): -0.05,
    ("Short-Term Treasury", "Gold"): 0.05,
    ("Short-Term Treasury", "Commodities"): 0.00,
    # High yield bonds correlate more with equities than with treasuries
    ("High Yield Bond", "US Large Cap Blend"): 0.55,
    ("High Yield Bond", "Short-Term Treasury"): 0.15,
    ("High Yield Bond", "Long-Term Treasury"): 0.10,
    # TIPS have moderate positive correlation with commodities
    ("TIPS", "Commodities"): 0.35,
    ("TIPS", "Gold"): 0.25,
    # Energy sector correlates with commodities
    ("Energy", "Commodities"): 0.65,
    ("Energy", "Agriculture"): 0.45,
    # REITs behave somewhat like equities
    ("US REITs", "US Large Cap Blend"): 0.60,
    ("Intl REITs", "Intl Developed"): 0.55,
}


def get_correlation(ticker_a: str, ticker_b: str) -> float:
    if ticker_a == ticker_b:
        return 1.0

    cat_a, cat_b = categories[ticker_a], categories[ticker_b]
    grp_a, grp_b = groups[ticker_a], groups[ticker_b]

    # Check category overrides (both directions)
    for key in [(cat_a, cat_b), (cat_b, cat_a)]:
        if key in CATEGORY_OVERRIDES:
            return CATEGORY_OVERRIDES[key]

    # Same group: high within-group correlation
    if grp_a == grp_b:
        key = (grp_a, grp_b)
        return GROUP_CORR.get(key, 0.80)

    # Cross-group
    for key in [(grp_a, grp_b), (grp_b, grp_a)]:
        if key in GROUP_CORR:
            return GROUP_CORR[key]

    return 0.20  # default


# Build covariance matrix: cov(i,j) = corr(i,j) * vol(i) * vol(j)
# Note: volatilities are in percentage units (e.g., 15.63), so
# covariance will be in %² units. sqrt(w^T Σ w) will give % units.
cov_matrix = {}
for a in tickers:
    cov_matrix[a] = {}
    for b in tickers:
        corr = get_correlation(a, b)
        # Convert vol from % to decimal for covariance, then back
        # Actually keep in % units: cov = corr * vol_a * vol_b (both in %)
        # This way sqrt(w^T Σ w) gives portfolio vol in %
        cov_matrix[a][b] = round(corr * vols[a] * vols[b], 4)

# Save
out_path = Path(__file__).parent / "etf_cov_matrix.json"
out_path.write_text(json.dumps(cov_matrix, indent=2))
print(f"Wrote {len(tickers)}×{len(tickers)} covariance matrix to {out_path}")

# Quick sanity check: 50/50 Stock/Bond should have lower vol than either
import numpy as np
t = tickers
n = len(t)
M = np.array([[cov_matrix[t[i]][t[j]] for j in range(n)] for i in range(n)])

# Equal-weight portfolio
w_equal = np.ones(n) / n
vol_equal = np.sqrt(w_equal @ M @ w_equal)
avg_vol = sum(vols[t] for t in tickers) / n
print(f"Equal-weight portfolio vol: {vol_equal:.2f}% (vs avg individual vol: {avg_vol:.2f}%)")
print(f"Diversification benefit: {avg_vol - vol_equal:.2f}% reduction")

# 50/50 VOO/BND
w = np.zeros(n)
w[tickers.index("VOO")] = 0.5
w[tickers.index("BND")] = 0.5
vol_5050 = np.sqrt(w @ M @ w)
print(f"50/50 VOO/BND vol: {vol_5050:.2f}% (VOO: {vols['VOO']}%, BND: {vols['BND']}%)")

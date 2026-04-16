#!/usr/bin/env python3
"""Lightweight portfolio volatility calculator using the covariance matrix.
Usage: python vol_calculator.py '{"VOO": 25, "GLD": 30, "VGSH": 20, "DBA": 25}'
Returns: portfolio volatility (%) computed as sqrt(w^T @ Cov @ w)
"""
import json, sys, math

with open("/Users/cameronafzal/Documents/frontier/dev_temp/etf_cov_matrix.json") as f:
    cov = json.load(f)

allocs = json.loads(sys.argv[1])
tickers = list(allocs.keys())
weights = {t: allocs[t] / 100.0 for t in tickers}

# Compute w^T @ Cov @ w
variance = 0.0
for i in tickers:
    for j in tickers:
        variance += weights[i] * weights[j] * cov[i][j]

vol = math.sqrt(max(variance, 0.0))

# Also compute weighted-average return and yield
with open("/Users/cameronafzal/Documents/frontier/dev_temp/etf_cache/etf_30_consolidated.json") as f:
    etfs = {e["ticker"]: e for e in json.load(f)}

ret = sum(weights[t] * etfs[t]["ann_return_5yr_pct"] for t in tickers)
yld = sum(weights[t] * etfs[t]["dividend_yield_pct"] for t in tickers) / sum(weights[t] for t in tickers)

print(json.dumps({
    "volatility_pct": round(vol, 2),
    "return_pct": round(ret, 2),
    "yield_pct": round(yld, 2),
    "holdings": len(tickers),
    "max_alloc": max(allocs.values()),
    "sum_alloc": sum(allocs.values()),
}, indent=2))

#!/usr/bin/env python3
"""Fetch ETF data from Alpha Vantage for Frontier demo.

Pulls ETF_PROFILE (expense ratio, dividend yield, sectors) and
TIME_SERIES_MONTHLY_ADJUSTED (for computing 5yr return + volatility)
for a universe of 25 ETFs.

Rate limit: free tier = 25 req/day, 1 req/sec.
Strategy: fetch in two batches — profiles first, then time series.
Cache results to JSON so we don't re-fetch.
"""

import json
import os
import time
import math
import requests
from pathlib import Path

API_KEY = "E70BTTMT657BLIHB"
BASE_URL = "https://www.alphavantage.co/query"
CACHE_DIR = Path(__file__).parent / "etf_cache"
CACHE_DIR.mkdir(exist_ok=True)

TICKERS = [
    # US Equity
    "VOO", "VTV", "VUG", "VO", "VB",
    # International Equity
    "VXUS", "VEA", "VWO",
    # Bonds
    "BND", "VGSH", "VGLT", "LQD", "TIP", "HYG", "BNDX", "EMB",
    # REITs, Commodities
    "VNQ", "GLD", "GSG",
    # Sectors
    "VGT", "VHT", "VDE", "VFH",
    # Dividend/Income
    "VYM", "SCHD",
]


def fetch_with_cache(function: str, symbol: str) -> dict:
    """Fetch from Alpha Vantage with local file cache."""
    cache_file = CACHE_DIR / f"{symbol}_{function}.json"
    if cache_file.exists():
        with open(cache_file) as f:
            data = json.load(f)
            # Check it's not an error/rate-limit response
            if "Information" not in data and "Error Message" not in data:
                return data

    params = {"function": function, "symbol": symbol, "apikey": API_KEY}
    print(f"  Fetching {function} for {symbol}...")
    resp = requests.get(BASE_URL, params=params)
    data = resp.json()

    if "Information" in data:
        print(f"  !! Rate limited: {data['Information'][:80]}")
        return data
    if "Error Message" in data:
        print(f"  !! Error: {data['Error Message'][:80]}")
        return data

    with open(cache_file, "w") as f:
        json.dump(data, f, indent=2)
    return data


def compute_returns_and_volatility(monthly_data: dict, years: int = 5) -> dict:
    """Compute annualized return and volatility from monthly adjusted close."""
    ts = monthly_data.get("Monthly Adjusted Time Series", {})
    if not ts:
        return {"error": "no time series data"}

    # Sort by date descending, take last N years of monthly data
    dates = sorted(ts.keys(), reverse=True)
    n_months = years * 12

    if len(dates) < n_months + 1:
        # Use whatever we have
        n_months = len(dates) - 1

    # Monthly returns from adjusted close
    monthly_returns = []
    for i in range(n_months):
        if i + 1 >= len(dates):
            break
        price_now = float(ts[dates[i]]["5. adjusted close"])
        price_prev = float(ts[dates[i + 1]]["5. adjusted close"])
        if price_prev > 0:
            monthly_returns.append(price_now / price_prev - 1)

    if len(monthly_returns) < 12:
        return {"error": f"only {len(monthly_returns)} months of data"}

    # Annualized return (geometric)
    cumulative = 1.0
    for r in monthly_returns:
        cumulative *= (1 + r)
    n_years = len(monthly_returns) / 12.0
    ann_return = cumulative ** (1.0 / n_years) - 1

    # Annualized volatility (std dev of monthly returns * sqrt(12))
    mean_r = sum(monthly_returns) / len(monthly_returns)
    variance = sum((r - mean_r) ** 2 for r in monthly_returns) / (len(monthly_returns) - 1)
    monthly_std = math.sqrt(variance)
    ann_volatility = monthly_std * math.sqrt(12)

    return {
        "annualized_return_pct": round(ann_return * 100, 2),
        "annualized_volatility_pct": round(ann_volatility * 100, 2),
        "months_used": len(monthly_returns),
        "period_start": dates[min(n_months, len(dates) - 1)],
        "period_end": dates[0],
    }


def extract_profile(profile_data: dict) -> dict:
    """Extract key fields from ETF_PROFILE response."""
    if "Information" in profile_data or "Error Message" in profile_data:
        return {"error": str(profile_data.get("Information", profile_data.get("Error Message", "unknown")))}

    expense = profile_data.get("net_expense_ratio", "")
    div_yield = profile_data.get("dividend_yield", "")
    sectors = profile_data.get("sectors", [])

    top_sector = None
    top_weight = 0
    for s in sectors:
        w = float(s.get("weight", 0))
        if w > top_weight:
            top_weight = w
            top_sector = s.get("sector", "")

    return {
        "expense_ratio_pct": round(float(expense) * 100, 3) if expense else None,
        "dividend_yield_pct": round(float(div_yield) * 100, 2) if div_yield else None,
        "top_sector": top_sector,
        "top_sector_weight_pct": round(top_weight * 100, 1),
        "all_sectors": {s["sector"]: round(float(s["weight"]) * 100, 1) for s in sectors},
    }


def main():
    import sys
    # Usage: python fetch_etf_data.py [profiles|timeseries|all]
    # Default: profiles only (to stay within 25/day limit)
    mode = sys.argv[1] if len(sys.argv) > 1 else "profiles"

    results = {}
    rate_limited = []
    api_calls = 0

    def track_fetch(function, symbol):
        nonlocal api_calls
        data = fetch_with_cache(function, symbol)
        # Only count if we actually hit the API (not cached)
        cache_file = CACHE_DIR / f"{symbol}_{function}.json"
        if cache_file.exists():
            with open(cache_file) as f:
                cached = json.load(f)
                if "Information" not in cached and "Error Message" not in cached:
                    return data  # Was cached, no API call
        api_calls += 1
        return data

    if mode in ("profiles", "all"):
        print("=== Phase 1: ETF Profiles ===")
        for ticker in TICKERS:
            profile = fetch_with_cache("ETF_PROFILE", ticker)
            if "Information" in profile:
                rate_limited.append(("ETF_PROFILE", ticker))
                print(f"  !! Rate limited after {api_calls} API calls. Re-run later.")
                break
            else:
                results.setdefault(ticker, {})["profile"] = extract_profile(profile)
            time.sleep(1.5)

    if mode in ("timeseries", "all"):
        print("\n=== Phase 2: Monthly Time Series ===")
        for ticker in TICKERS:
            ts = fetch_with_cache("TIME_SERIES_MONTHLY_ADJUSTED", ticker)
            if "Information" in ts:
                rate_limited.append(("TIME_SERIES_MONTHLY_ADJUSTED", ticker))
                print(f"  !! Rate limited. Re-run later.")
                break
            else:
                results.setdefault(ticker, {})["performance"] = compute_returns_and_volatility(ts)
            time.sleep(1.5)

    # Summary
    print("\n=== Results ===")
    print(f"{'Ticker':<8} {'ExpRatio':>8} {'DivYld':>7} {'5yr Ret':>8} {'5yr Vol':>8} {'Top Sector':<25} {'SctWt':>6}")
    print("-" * 80)
    for ticker in TICKERS:
        if ticker not in results:
            print(f"{ticker:<8} ** MISSING **")
            continue
        p = results[ticker].get("profile", {})
        perf = results[ticker].get("performance", {})
        if "error" in p or "error" in perf:
            err = p.get("error", "") or perf.get("error", "")
            print(f"{ticker:<8} ERROR: {err[:60]}")
            continue
        exp = p.get('expense_ratio_pct')
        div = p.get('dividend_yield_pct')
        ret = perf.get('annualized_return_pct')
        vol = perf.get('annualized_volatility_pct')
        sec = p.get('top_sector', '?')
        sw = p.get('top_sector_weight_pct')
        print(f"{ticker:<8} {exp if exp is not None else '?':>7}% {div if div is not None else '?':>6}% "
              f"{ret if ret is not None else '?':>7}% {vol if vol is not None else '?':>7}% "
              f"{sec:<25} {sw if sw is not None else '?':>5}%")

    if rate_limited:
        print(f"\n!! Rate limited on {len(rate_limited)} requests:")
        for func, sym in rate_limited:
            print(f"   {func} / {sym}")
        print("Re-run script to fetch from cache + retry remaining.")

    # Save full results
    out_file = CACHE_DIR / "etf_summary.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results saved to {out_file}")


if __name__ == "__main__":
    main()

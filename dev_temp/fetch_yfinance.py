#!/usr/bin/env python3
"""Fetch ETF performance data via yfinance + merge with Alpha Vantage profiles.

Computes 5-year annualized return and volatility from monthly adjusted close.
Also fetches dividend yield and info for VYM/SCHD (missing from AV cache).
Outputs a consolidated CSV + JSON ready for Frontier problem setup.
"""

import json
import math
import os
from pathlib import Path

import yfinance as yf
import pandas as pd

CACHE_DIR = Path(__file__).parent / "etf_cache"

TICKERS = [
    "VOO", "VTV", "VUG", "VO", "VB",
    "VXUS", "VEA", "VWO",
    "BND", "VGSH", "VGLT", "LQD", "TIP", "HYG", "BNDX", "EMB",
    "VNQ", "GLD", "GSG",
    "VGT", "VHT", "VDE", "VFH",
    "VYM", "SCHD",
]

CATEGORIES = {
    "VOO": "US Large Cap Blend", "VTV": "US Large Cap Value", "VUG": "US Large Cap Growth",
    "VO": "US Mid Cap", "VB": "US Small Cap",
    "VXUS": "International Total", "VEA": "Intl Developed", "VWO": "Emerging Markets",
    "BND": "US Aggregate Bond", "VGSH": "Short-Term Treasury", "VGLT": "Long-Term Treasury",
    "LQD": "IG Corporate Bond", "TIP": "TIPS", "HYG": "High Yield Bond",
    "BNDX": "Intl Bond", "EMB": "EM Bond",
    "VNQ": "REITs", "GLD": "Gold", "GSG": "Commodities",
    "VGT": "Technology", "VHT": "Healthcare", "VDE": "Energy", "VFH": "Financials",
    "VYM": "High Dividend", "SCHD": "Dividend Quality",
}


def compute_metrics(ticker: str) -> dict:
    """Compute 5yr annualized return and volatility from yfinance monthly data."""
    etf = yf.Ticker(ticker)

    # 5 years of monthly data
    hist = etf.history(period="5y", interval="1mo", auto_adjust=True)
    if hist.empty or len(hist) < 12:
        return {"error": f"insufficient data: {len(hist)} months"}

    # Monthly returns from adjusted close
    monthly_returns = hist["Close"].pct_change().dropna()

    # Annualized return (geometric)
    cumulative = (1 + monthly_returns).prod()
    n_years = len(monthly_returns) / 12.0
    ann_return = cumulative ** (1.0 / n_years) - 1

    # Annualized volatility
    ann_vol = monthly_returns.std() * math.sqrt(12)

    return {
        "annualized_return_pct": round(ann_return * 100, 2),
        "annualized_volatility_pct": round(ann_vol * 100, 2),
        "months_used": len(monthly_returns),
        "period": f"{hist.index[0].strftime('%Y-%m')} to {hist.index[-1].strftime('%Y-%m')}",
    }


def load_av_profile(ticker: str) -> dict:
    """Load Alpha Vantage ETF_PROFILE from cache."""
    cache_file = CACHE_DIR / f"{ticker}_ETF_PROFILE.json"
    if not cache_file.exists():
        return {}
    with open(cache_file) as f:
        d = json.load(f)
    if "Information" in d or "Error Message" in d:
        return {}

    exp = d.get("net_expense_ratio", "")
    div = d.get("dividend_yield", "")
    sectors = d.get("sectors", [])

    # Find top sector with meaningful weight (>1%)
    top_sector = None
    top_weight = 0
    for s in sectors:
        w = float(s.get("weight", 0))
        if w > top_weight:
            top_weight = w
            top_sector = s.get("sector", "")

    return {
        "expense_ratio_pct": round(float(exp) * 100, 3) if exp else None,
        "dividend_yield_pct": round(float(div) * 100, 2) if div else None,
        "top_sector": top_sector if top_weight > 0.01 else None,
        "top_sector_weight_pct": round(top_weight * 100, 1) if top_weight > 0.01 else None,
    }


def get_yf_supplemental(ticker: str) -> dict:
    """Get dividend yield and expense ratio from yfinance for tickers missing AV profile."""
    etf = yf.Ticker(ticker)
    info = etf.info
    return {
        "expense_ratio_pct": round(info.get("annualReportExpenseRatio", 0) * 100, 3) if info.get("annualReportExpenseRatio") else None,
        "dividend_yield_pct": round(info.get("yield", 0) * 100, 2) if info.get("yield") else None,
    }


def main():
    rows = []

    print(f"Fetching 5yr monthly data for {len(TICKERS)} ETFs via yfinance...\n")

    for ticker in TICKERS:
        print(f"  {ticker}...", end=" ", flush=True)

        # Performance from yfinance
        perf = compute_metrics(ticker)
        if "error" in perf:
            print(f"ERROR: {perf['error']}")
            continue

        # Profile from Alpha Vantage cache
        profile = load_av_profile(ticker)

        # Supplement VYM/SCHD (or any missing) from yfinance
        if not profile.get("expense_ratio_pct"):
            supp = get_yf_supplemental(ticker)
            profile["expense_ratio_pct"] = profile.get("expense_ratio_pct") or supp.get("expense_ratio_pct")
            profile["dividend_yield_pct"] = profile.get("dividend_yield_pct") or supp.get("dividend_yield_pct")

        row = {
            "ticker": ticker,
            "category": CATEGORIES.get(ticker, ""),
            "expense_ratio_pct": profile.get("expense_ratio_pct"),
            "dividend_yield_pct": profile.get("dividend_yield_pct"),
            "ann_return_5yr_pct": perf["annualized_return_pct"],
            "ann_volatility_5yr_pct": perf["annualized_volatility_pct"],
            "top_sector": profile.get("top_sector"),
            "top_sector_weight_pct": profile.get("top_sector_weight_pct"),
            "months": perf["months_used"],
            "period": perf["period"],
        }
        rows.append(row)
        print(f"ret={row['ann_return_5yr_pct']:>6}%  vol={row['ann_volatility_5yr_pct']:>6}%  "
              f"exp={row['expense_ratio_pct'] or '?':>6}  div={row['dividend_yield_pct'] or '?':>6}")

    # Summary table
    print(f"\n{'='*100}")
    print(f"{'Ticker':<8} {'Category':<22} {'ExpRatio':>8} {'DivYld':>7} {'5yr Ret':>8} {'5yr Vol':>8} {'Top Sector':<22} {'SctWt':>6}")
    print(f"{'-'*100}")
    for r in rows:
        exp = f"{r['expense_ratio_pct']:.3f}" if r['expense_ratio_pct'] is not None else "?"
        div = f"{r['dividend_yield_pct']:.2f}" if r['dividend_yield_pct'] is not None else "?"
        sec = r['top_sector'] or "-"
        sw = f"{r['top_sector_weight_pct']:.1f}" if r['top_sector_weight_pct'] is not None else "-"
        print(f"{r['ticker']:<8} {r['category']:<22} {exp:>7}% {div:>6}% {r['ann_return_5yr_pct']:>7}% "
              f"{r['ann_volatility_5yr_pct']:>7}% {sec:<22} {sw:>5}%")

    # Save
    out_json = CACHE_DIR / "etf_consolidated.json"
    with open(out_json, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"\nSaved to {out_json}")

    df = pd.DataFrame(rows)
    out_csv = CACHE_DIR / "etf_consolidated.csv"
    df.to_csv(out_csv, index=False)
    print(f"Saved to {out_csv}")


if __name__ == "__main__":
    main()

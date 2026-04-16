#!/usr/bin/env python3
"""Fetch ETF data from yfinance for Frontier demo.

Computes 5yr annualized return, volatility, and dividend yield
for a 30-ETF universe. No API key needed.
"""

import json
import math
from pathlib import Path

import yfinance as yf

CACHE_DIR = Path(__file__).parent / "etf_cache"
CACHE_DIR.mkdir(exist_ok=True)

# 30-ETF universe (MECE across asset classes)
ETFS = {
    # US Equity (6)
    "VOO":  "US Large Cap Blend",
    "VUG":  "US Large Cap Growth",
    "VTV":  "US Large Cap Value",
    "VO":   "US Mid Cap",
    "VB":   "US Small Cap",
    "SCHD": "Dividend Quality",
    # Intl Equity (5)
    "VEA":  "Intl Developed",
    "VWO":  "Emerging Markets",
    "VGK":  "Europe",
    "EWJ":  "Japan",
    "MCHI": "China",
    # Bonds (6)
    "BND":  "US Aggregate Bond",
    "VGSH": "Short-Term Treasury",
    "VGLT": "Long-Term Treasury",
    "TIP":  "TIPS",
    "HYG":  "High Yield Bond",
    "EMB":  "EM Bond",
    # Sectors (7)
    "VGT":  "Technology",
    "VHT":  "Healthcare",
    "VDE":  "Energy",
    "VFH":  "Financials",
    "VPU":  "Utilities",
    "VDC":  "Consumer Staples",
    "VOX":  "Communication Services",
    # Alternatives (6)
    "VNQ":  "US REITs",
    "VNQI": "Intl REITs",
    "GLD":  "Gold",
    "GSG":  "Commodities",
    "DBA":  "Agriculture",
    "IGF":  "Infrastructure",
}

GROUP_MAP = {
    "US Equity": ["VOO", "VUG", "VTV", "VO", "VB", "SCHD"],
    "Intl Equity": ["VEA", "VWO", "VGK", "EWJ", "MCHI"],
    "Bonds": ["BND", "VGSH", "VGLT", "TIP", "HYG", "EMB"],
    "Sectors": ["VGT", "VHT", "VDE", "VFH", "VPU", "VDC", "VOX"],
    "Alternatives": ["VNQ", "VNQI", "GLD", "GSG", "DBA", "IGF"],
}


def compute_metrics(ticker: str, years: int = 5) -> dict:
    """Compute annualized return, volatility, and dividend yield from yfinance."""
    t = yf.Ticker(ticker)

    # Get monthly adjusted close for 5 years
    hist = t.history(period=f"{years}y", interval="1mo", auto_adjust=True)
    if hist.empty or len(hist) < 13:
        return {"error": f"insufficient history: {len(hist)} months"}

    # Monthly returns from adjusted close
    closes = hist["Close"].dropna()
    monthly_returns = closes.pct_change().dropna().tolist()

    if len(monthly_returns) < 12:
        return {"error": f"only {len(monthly_returns)} monthly returns"}

    # Annualized return (geometric)
    cumulative = 1.0
    for r in monthly_returns:
        cumulative *= (1 + r)
    n_years = len(monthly_returns) / 12.0
    ann_return = cumulative ** (1.0 / n_years) - 1

    # Annualized volatility
    mean_r = sum(monthly_returns) / len(monthly_returns)
    variance = sum((r - mean_r) ** 2 for r in monthly_returns) / (len(monthly_returns) - 1)
    ann_vol = math.sqrt(variance) * math.sqrt(12)

    # Dividend yield from info — dividendYield is already in % (e.g. 1.19 = 1.19%)
    info = t.info
    div_yield = info.get("dividendYield")  # already in %, e.g. 1.19
    if div_yield is None:
        # trailingAnnualDividendYield is a decimal (0.0087)
        tady = info.get("trailingAnnualDividendYield", 0.0)
        div_yield = (tady or 0.0) * 100
    if div_yield is None:
        div_yield = 0.0

    # Expense ratio — netExpenseRatio is already in % (e.g. 0.03 = 0.03%)
    expense = info.get("netExpenseRatio")

    # Top sector from sector weights if available
    top_sector = None
    top_sector_wt = None
    try:
        sw = t.funds_data.sector_weightings if hasattr(t, 'funds_data') else None
        if sw:
            for sector_dict in sw:
                for sector_name, weight in sector_dict.items():
                    if top_sector_wt is None or weight > top_sector_wt:
                        top_sector = sector_name
                        top_sector_wt = weight
    except Exception:
        pass

    period_start = closes.index[0].strftime("%Y-%m")
    period_end = closes.index[-1].strftime("%Y-%m")

    return {
        "ticker": ticker,
        "category": ETFS[ticker],
        "group": next(g for g, tickers in GROUP_MAP.items() if ticker in tickers),
        "expense_ratio_pct": round(expense, 3) if expense else None,
        "dividend_yield_pct": round(div_yield, 2),
        "ann_return_5yr_pct": round(ann_return * 100, 2),
        "ann_volatility_5yr_pct": round(ann_vol * 100, 2),
        "top_sector": top_sector,
        "top_sector_weight_pct": round(top_sector_wt * 100, 1) if top_sector_wt else None,
        "months": len(monthly_returns),
        "period": f"{period_start} to {period_end}",
    }


def main():
    results = []
    errors = []

    for ticker in ETFS:
        print(f"Fetching {ticker}...", end=" ", flush=True)
        try:
            data = compute_metrics(ticker)
            if "error" in data:
                print(f"ERROR: {data['error']}")
                errors.append((ticker, data["error"]))
            else:
                print(f"ret={data['ann_return_5yr_pct']}% vol={data['ann_volatility_5yr_pct']}% div={data['dividend_yield_pct']}%")
                results.append(data)
        except Exception as e:
            print(f"EXCEPTION: {e}")
            errors.append((ticker, str(e)))

    # Summary table
    print(f"\n{'Ticker':<8} {'Category':<25} {'Return':>7} {'Vol':>7} {'DivYld':>7} {'Expense':>8}")
    print("-" * 70)
    for r in results:
        exp = f"{r['expense_ratio_pct']:.2f}%" if r['expense_ratio_pct'] else "N/A"
        print(f"{r['ticker']:<8} {r['category']:<25} {r['ann_return_5yr_pct']:>6.1f}% {r['ann_volatility_5yr_pct']:>6.1f}% {r['dividend_yield_pct']:>6.2f}% {exp:>8}")

    if errors:
        print(f"\n{len(errors)} errors:")
        for t, e in errors:
            print(f"  {t}: {e}")

    # Save
    out_file = CACHE_DIR / "etf_30_consolidated.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {len(results)} ETFs to {out_file}")


if __name__ == "__main__":
    main()

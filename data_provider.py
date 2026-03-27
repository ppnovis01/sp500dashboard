"""
Data provider module for S&P 500 dashboard.
Uses yfinance for live data, falls back to sample data when unavailable.
"""

import yfinance as yf
import pandas as pd
import numpy as np

from sample_data import (
    get_sample_index_prices,
    get_sample_mag7_prices,
    get_sample_sector_etf_prices,
    SAMPLE_FUNDAMENTALS,
    SAMPLE_VALUATION,
)

# --- Ticker Definitions ---

MAG7_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]

SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLC": "Communication Services",
    "XLY": "Consumer Discretionary",
    "XLV": "Health Care",
    "XLI": "Industrials",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLU": "Utilities",
    "XLB": "Materials",
    "XLRE": "Real Estate",
}

INDEX_TICKERS = {
    "^GSPC": "S&P 500",
    "RSP": "S&P 500 Equal Weight",
}

# Track whether we're using live or sample data
_using_sample_data = False


def _try_download(tickers: list[str], period: str = "5y") -> pd.DataFrame | None:
    """Try to download from Yahoo Finance, return None on failure."""
    try:
        data = yf.download(tickers, period=period, auto_adjust=True, progress=False)
        if data.empty:
            return None
        if isinstance(data.columns, pd.MultiIndex):
            prices = data["Close"]
        else:
            prices = data[["Close"]]
            prices.columns = tickers
        result = prices.dropna(how="all")
        return result if not result.empty else None
    except Exception:
        return None


def get_price_history(tickers: list[str], period: str = "5y") -> pd.DataFrame:
    """Download adjusted close prices. Falls back to sample data."""
    global _using_sample_data

    live = _try_download(tickers, period)
    if live is not None:
        _using_sample_data = False
        return live

    # Fallback to sample data
    _using_sample_data = True
    all_sample = pd.concat([
        get_sample_index_prices(period),
        get_sample_mag7_prices(period),
        get_sample_sector_etf_prices(period),
    ], axis=1)

    available = [t for t in tickers if t in all_sample.columns]
    if available:
        return all_sample[available]
    return pd.DataFrame()


def get_normalized_prices(tickers: list[str], period: str = "5y") -> pd.DataFrame:
    """Return prices normalized to 100 at the start."""
    prices = get_price_history(tickers, period)
    if prices.empty:
        return prices
    first_valid = prices.apply(lambda s: s.dropna().iloc[0] if not s.dropna().empty else np.nan)
    return (prices / first_valid) * 100


def compute_sp493(period: str = "5y") -> pd.DataFrame:
    """
    Approximate S&P 493 performance:
    S&P 493 = (S&P 500 - Mag7 weighted contribution) rescaled.
    Mag7 weight approximated at ~30% of S&P 500.
    """
    sp500 = get_price_history(["^GSPC"], period)
    mag7 = get_price_history(MAG7_TICKERS, period)

    if sp500.empty or mag7.empty:
        return pd.DataFrame()

    sp500_norm = (sp500 / sp500.iloc[0]) * 100
    mag7_avg = mag7.mean(axis=1)
    mag7_norm = (mag7_avg / mag7_avg.iloc[0]) * 100

    mag7_weight = 0.30
    col = sp500.columns[0]
    sp493_norm = (sp500_norm[col] - mag7_weight * mag7_norm) / (1 - mag7_weight)
    sp493_norm = (sp493_norm / sp493_norm.iloc[0]) * 100

    return pd.DataFrame({"S&P 493 (approx)": sp493_norm})


def _get_live_fundamentals(ticker: str) -> dict | None:
    """Try fetching fundamentals from yfinance."""
    try:
        tk = yf.Ticker(ticker)
        inc = tk.income_stmt
        if inc is None or inc.empty:
            return None
        result = {}
        for key, label in [("revenue", "Total Revenue"), ("ebit", "EBIT"),
                           ("ebitda", "EBITDA"), ("net_income", "Net Income")]:
            result[key] = inc.loc[label] if label in inc.index else None
        return result
    except Exception:
        return None


def build_fundamentals_df(tickers: list[str], metric: str) -> pd.DataFrame:
    """
    Build DataFrame with annual values for a metric across tickers.
    metric: 'revenue', 'ebit', 'ebitda', 'net_income'
    """
    frames = {}
    for ticker in tickers:
        # Try live first
        live = _get_live_fundamentals(ticker)
        if live and live.get(metric) is not None:
            series = live[metric]
            if not series.empty:
                frames[ticker] = series
                continue
        # Fallback to sample
        if ticker in SAMPLE_FUNDAMENTALS and metric in SAMPLE_FUNDAMENTALS[ticker]:
            frames[ticker] = SAMPLE_FUNDAMENTALS[ticker][metric]

    if not frames:
        return pd.DataFrame()
    df = pd.DataFrame(frames)
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def build_growth_df(tickers: list[str], metric: str) -> pd.DataFrame:
    """Build YoY growth rates for a given metric."""
    df = build_fundamentals_df(tickers, metric)
    if df.empty:
        return df
    growth = df.pct_change() * 100
    return growth.dropna(how="all")


def get_key_metrics_table(tickers: list[str]) -> pd.DataFrame:
    """Build a summary table with key valuation metrics."""
    rows = []
    for ticker in tickers:
        info = {}
        try:
            tk = yf.Ticker(ticker)
            info = tk.info or {}
        except Exception:
            pass
        # Fallback to sample
        if not info and ticker in SAMPLE_VALUATION:
            info = SAMPLE_VALUATION[ticker]

        rows.append({
            "Ticker": ticker,
            "Name": info.get("shortName", ticker),
            "Market Cap (B)": round(info.get("marketCap", 0) / 1e9, 1) if info.get("marketCap") else None,
            "P/E (TTM)": info.get("trailingPE"),
            "Forward P/E": info.get("forwardPE"),
            "P/S": info.get("priceToSalesTrailing12Months"),
            "EV/EBITDA": info.get("enterpriseToEbitda"),
            "Dividend Yield %": round((info.get("dividendYield") or 0) * 100, 2),
            "52w High": info.get("fiftyTwoWeekHigh"),
            "52w Low": info.get("fiftyTwoWeekLow"),
        })
    return pd.DataFrame(rows).set_index("Ticker")


def get_earnings_history(ticker: str) -> pd.DataFrame:
    """Get quarterly earnings (EPS actual vs estimate)."""
    try:
        tk = yf.Ticker(ticker)
        earnings = tk.earnings_dates
        if earnings is not None and not earnings.empty:
            return earnings.head(12)
    except Exception:
        pass
    return pd.DataFrame()


def is_using_sample_data() -> bool:
    return _using_sample_data

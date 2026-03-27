"""
Realistic sample data for dashboard demonstration.
Used as fallback when Yahoo Finance API is unavailable.
Based on approximate real market data through early 2026.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _make_date_range(years: int = 5) -> pd.DatetimeIndex:
    end = datetime(2026, 3, 27)
    start = end - timedelta(days=365 * years)
    return pd.bdate_range(start, end)


def _simulate_prices(start: float, annual_return: float, volatility: float, dates: pd.DatetimeIndex) -> pd.Series:
    """Generate realistic price series using geometric Brownian motion."""
    np.random.seed(hash(str(start) + str(annual_return)) % (2**31))
    n = len(dates)
    dt = 1 / 252
    drift = (annual_return - 0.5 * volatility**2) * dt
    shock = volatility * np.sqrt(dt) * np.random.randn(n)
    log_returns = drift + shock
    log_returns[0] = 0
    prices = start * np.exp(np.cumsum(log_returns))
    return pd.Series(prices, index=dates)


def get_sample_index_prices(period: str = "5y") -> pd.DataFrame:
    """Sample price data for S&P 500 and Equal Weight."""
    years = {"1y": 1, "2y": 2, "3y": 3, "5y": 5, "10y": 10, "max": 10}.get(period, 5)
    dates = _make_date_range(years)
    return pd.DataFrame({
        "^GSPC": _simulate_prices(4200, 0.12, 0.16, dates),
        "RSP": _simulate_prices(150, 0.09, 0.15, dates),
    })


def get_sample_mag7_prices(period: str = "5y") -> pd.DataFrame:
    """Sample price data for Magnificent 7."""
    years = {"1y": 1, "2y": 2, "3y": 3, "5y": 5, "10y": 10, "max": 10}.get(period, 5)
    dates = _make_date_range(years)
    configs = {
        "AAPL": (140, 0.15, 0.22),
        "MSFT": (280, 0.18, 0.21),
        "GOOGL": (100, 0.14, 0.24),
        "AMZN": (130, 0.16, 0.26),
        "NVDA": (30, 0.45, 0.40),
        "META": (200, 0.20, 0.30),
        "TSLA": (200, 0.10, 0.45),
    }
    return pd.DataFrame({
        ticker: _simulate_prices(start, ret, vol, dates)
        for ticker, (start, ret, vol) in configs.items()
    })


def get_sample_sector_etf_prices(period: str = "5y") -> pd.DataFrame:
    """Sample price data for sector ETFs."""
    years = {"1y": 1, "2y": 2, "3y": 3, "5y": 5, "10y": 10, "max": 10}.get(period, 5)
    dates = _make_date_range(years)
    configs = {
        "XLK": (140, 0.16, 0.20),
        "XLF": (35, 0.10, 0.18),
        "XLC": (65, 0.14, 0.22),
        "XLY": (170, 0.08, 0.22),
        "XLV": (130, 0.07, 0.15),
        "XLI": (95, 0.10, 0.17),
        "XLP": (72, 0.05, 0.12),
        "XLE": (55, 0.12, 0.25),
        "XLU": (68, 0.04, 0.14),
        "XLB": (80, 0.08, 0.18),
        "XLRE": (42, 0.03, 0.19),
    }
    return pd.DataFrame({
        ticker: _simulate_prices(start, ret, vol, dates)
        for ticker, (start, ret, vol) in configs.items()
    })


# --- Fundamentals sample data (annual, in USD) ---

_ANNUAL_DATES = pd.to_datetime(["2022-12-31", "2023-12-31", "2024-12-31", "2025-12-31"])

SAMPLE_FUNDAMENTALS = {
    "AAPL": {
        "revenue":    pd.Series([394.3e9, 383.3e9, 391.0e9, 410.0e9], index=_ANNUAL_DATES),
        "ebit":       pd.Series([119.4e9, 114.3e9, 118.7e9, 125.0e9], index=_ANNUAL_DATES),
        "ebitda":     pd.Series([130.5e9, 125.8e9, 131.0e9, 138.0e9], index=_ANNUAL_DATES),
        "net_income": pd.Series([99.8e9, 97.0e9, 100.9e9, 106.0e9], index=_ANNUAL_DATES),
    },
    "MSFT": {
        "revenue":    pd.Series([198.3e9, 211.9e9, 245.1e9, 275.0e9], index=_ANNUAL_DATES),
        "ebit":       pd.Series([83.4e9, 88.5e9, 109.4e9, 125.0e9], index=_ANNUAL_DATES),
        "ebitda":     pd.Series([97.9e9, 104.0e9, 125.0e9, 143.0e9], index=_ANNUAL_DATES),
        "net_income": pd.Series([72.7e9, 72.4e9, 88.1e9, 100.0e9], index=_ANNUAL_DATES),
    },
    "GOOGL": {
        "revenue":    pd.Series([282.8e9, 307.4e9, 350.0e9, 390.0e9], index=_ANNUAL_DATES),
        "ebit":       pd.Series([74.8e9, 84.3e9, 105.0e9, 120.0e9], index=_ANNUAL_DATES),
        "ebitda":     pd.Series([90.8e9, 100.0e9, 120.0e9, 138.0e9], index=_ANNUAL_DATES),
        "net_income": pd.Series([59.9e9, 73.8e9, 90.0e9, 102.0e9], index=_ANNUAL_DATES),
    },
    "AMZN": {
        "revenue":    pd.Series([514.0e9, 574.8e9, 638.0e9, 700.0e9], index=_ANNUAL_DATES),
        "ebit":       pd.Series([12.2e9, 36.9e9, 55.0e9, 65.0e9], index=_ANNUAL_DATES),
        "ebitda":     pd.Series([55.3e9, 85.5e9, 110.0e9, 125.0e9], index=_ANNUAL_DATES),
        "net_income": pd.Series([-2.7e9, 30.4e9, 44.0e9, 52.0e9], index=_ANNUAL_DATES),
    },
    "NVDA": {
        "revenue":    pd.Series([27.0e9, 60.9e9, 130.5e9, 175.0e9], index=_ANNUAL_DATES),
        "ebit":       pd.Series([4.2e9, 32.9e9, 82.0e9, 115.0e9], index=_ANNUAL_DATES),
        "ebitda":     pd.Series([5.8e9, 34.8e9, 85.0e9, 120.0e9], index=_ANNUAL_DATES),
        "net_income": pd.Series([4.4e9, 29.8e9, 73.0e9, 100.0e9], index=_ANNUAL_DATES),
    },
    "META": {
        "revenue":    pd.Series([116.6e9, 134.9e9, 162.0e9, 190.0e9], index=_ANNUAL_DATES),
        "ebit":       pd.Series([28.9e9, 46.8e9, 60.0e9, 72.0e9], index=_ANNUAL_DATES),
        "ebitda":     pd.Series([37.7e9, 56.5e9, 72.0e9, 85.0e9], index=_ANNUAL_DATES),
        "net_income": pd.Series([23.2e9, 39.1e9, 50.0e9, 60.0e9], index=_ANNUAL_DATES),
    },
    "TSLA": {
        "revenue":    pd.Series([81.5e9, 96.8e9, 98.0e9, 110.0e9], index=_ANNUAL_DATES),
        "ebit":       pd.Series([13.7e9, 8.9e9, 7.5e9, 10.0e9], index=_ANNUAL_DATES),
        "ebitda":     pd.Series([17.9e9, 13.0e9, 12.0e9, 15.0e9], index=_ANNUAL_DATES),
        "net_income": pd.Series([12.6e9, 7.9e9, 7.0e9, 9.5e9], index=_ANNUAL_DATES),
    },
}

SAMPLE_VALUATION = {
    "AAPL": {"shortName": "Apple Inc.", "marketCap": 3.4e12, "trailingPE": 33.5, "forwardPE": 30.1, "priceToSalesTrailing12Months": 8.7, "enterpriseToEbitda": 25.1, "dividendYield": 0.0045, "fiftyTwoWeekHigh": 260.10, "fiftyTwoWeekLow": 169.21},
    "MSFT": {"shortName": "Microsoft Corp.", "marketCap": 3.1e12, "trailingPE": 35.2, "forwardPE": 29.8, "priceToSalesTrailing12Months": 12.6, "enterpriseToEbitda": 24.3, "dividendYield": 0.0072, "fiftyTwoWeekHigh": 468.35, "fiftyTwoWeekLow": 362.90},
    "GOOGL": {"shortName": "Alphabet Inc.", "marketCap": 2.3e12, "trailingPE": 25.0, "forwardPE": 21.5, "priceToSalesTrailing12Months": 6.5, "enterpriseToEbitda": 17.8, "dividendYield": 0.0045, "fiftyTwoWeekHigh": 207.05, "fiftyTwoWeekLow": 150.22},
    "AMZN": {"shortName": "Amazon.com Inc.", "marketCap": 2.2e12, "trailingPE": 42.0, "forwardPE": 32.5, "priceToSalesTrailing12Months": 3.4, "enterpriseToEbitda": 18.5, "dividendYield": 0.0, "fiftyTwoWeekHigh": 242.52, "fiftyTwoWeekLow": 166.21},
    "NVDA": {"shortName": "NVIDIA Corp.", "marketCap": 3.3e12, "trailingPE": 45.0, "forwardPE": 28.0, "priceToSalesTrailing12Months": 25.0, "enterpriseToEbitda": 38.5, "dividendYield": 0.0002, "fiftyTwoWeekHigh": 153.13, "fiftyTwoWeekLow": 75.61},
    "META": {"shortName": "Meta Platforms Inc.", "marketCap": 1.6e12, "trailingPE": 28.5, "forwardPE": 23.0, "priceToSalesTrailing12Months": 9.8, "enterpriseToEbitda": 19.2, "dividendYield": 0.0035, "fiftyTwoWeekHigh": 740.91, "fiftyTwoWeekLow": 442.55},
    "TSLA": {"shortName": "Tesla Inc.", "marketCap": 1.1e12, "trailingPE": 120.0, "forwardPE": 85.0, "priceToSalesTrailing12Months": 11.2, "enterpriseToEbitda": 72.0, "dividendYield": 0.0, "fiftyTwoWeekHigh": 488.54, "fiftyTwoWeekLow": 138.80},
    "XLK": {"shortName": "Technology Select SPDR", "marketCap": 72e9, "trailingPE": 32.0, "forwardPE": 27.0, "priceToSalesTrailing12Months": None, "enterpriseToEbitda": None, "dividendYield": 0.006, "fiftyTwoWeekHigh": 240.0, "fiftyTwoWeekLow": 185.0},
    "XLF": {"shortName": "Financial Select SPDR", "marketCap": 42e9, "trailingPE": 16.5, "forwardPE": 14.8, "priceToSalesTrailing12Months": None, "enterpriseToEbitda": None, "dividendYield": 0.014, "fiftyTwoWeekHigh": 52.0, "fiftyTwoWeekLow": 38.0},
    "XLC": {"shortName": "Communication Services SPDR", "marketCap": 18e9, "trailingPE": 20.5, "forwardPE": 18.0, "priceToSalesTrailing12Months": None, "enterpriseToEbitda": None, "dividendYield": 0.007, "fiftyTwoWeekHigh": 100.0, "fiftyTwoWeekLow": 72.0},
    "XLY": {"shortName": "Consumer Discretionary SPDR", "marketCap": 20e9, "trailingPE": 28.0, "forwardPE": 22.0, "priceToSalesTrailing12Months": None, "enterpriseToEbitda": None, "dividendYield": 0.008, "fiftyTwoWeekHigh": 230.0, "fiftyTwoWeekLow": 170.0},
    "XLV": {"shortName": "Health Care Select SPDR", "marketCap": 38e9, "trailingPE": 18.5, "forwardPE": 16.2, "priceToSalesTrailing12Months": None, "enterpriseToEbitda": None, "dividendYield": 0.015, "fiftyTwoWeekHigh": 155.0, "fiftyTwoWeekLow": 125.0},
    "XLI": {"shortName": "Industrial Select SPDR", "marketCap": 18e9, "trailingPE": 22.0, "forwardPE": 19.5, "priceToSalesTrailing12Months": None, "enterpriseToEbitda": None, "dividendYield": 0.013, "fiftyTwoWeekHigh": 135.0, "fiftyTwoWeekLow": 100.0},
    "XLP": {"shortName": "Consumer Staples SPDR", "marketCap": 16e9, "trailingPE": 21.0, "forwardPE": 19.0, "priceToSalesTrailing12Months": None, "enterpriseToEbitda": None, "dividendYield": 0.025, "fiftyTwoWeekHigh": 82.0, "fiftyTwoWeekLow": 68.0},
    "XLE": {"shortName": "Energy Select SPDR", "marketCap": 38e9, "trailingPE": 12.5, "forwardPE": 11.0, "priceToSalesTrailing12Months": None, "enterpriseToEbitda": None, "dividendYield": 0.034, "fiftyTwoWeekHigh": 100.0, "fiftyTwoWeekLow": 75.0},
    "XLU": {"shortName": "Utilities Select SPDR", "marketCap": 16e9, "trailingPE": 17.0, "forwardPE": 16.0, "priceToSalesTrailing12Months": None, "enterpriseToEbitda": None, "dividendYield": 0.028, "fiftyTwoWeekHigh": 80.0, "fiftyTwoWeekLow": 60.0},
    "XLB": {"shortName": "Materials Select SPDR", "marketCap": 6e9, "trailingPE": 19.0, "forwardPE": 17.5, "priceToSalesTrailing12Months": None, "enterpriseToEbitda": None, "dividendYield": 0.018, "fiftyTwoWeekHigh": 95.0, "fiftyTwoWeekLow": 75.0},
    "XLRE": {"shortName": "Real Estate Select SPDR", "marketCap": 6e9, "trailingPE": 35.0, "forwardPE": 30.0, "priceToSalesTrailing12Months": None, "enterpriseToEbitda": None, "dividendYield": 0.032, "fiftyTwoWeekHigh": 46.0, "fiftyTwoWeekLow": 35.0},
}

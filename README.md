# S&P 500 Analysis Dashboard

Interactive Streamlit dashboard for analyzing the S&P 500 ecosystem.

## Features

- **Index Comparison**: S&P 500, S&P Equal Weight, S&P 493 (approximated), and Mag7 average
- **Mag7 Analysis**: Individual performance of Apple, Microsoft, Google, Amazon, NVIDIA, Meta, Tesla
- **Sector ETFs**: All 11 GICS sector ETFs (XLK, XLF, XLC, XLY, XLV, XLI, XLP, XLE, XLU, XLB, XLRE)
- **Fundamentals**: Revenue, EBIT, EBITDA, Net Income - absolute values and YoY growth
- **Valuation Metrics**: P/E, Forward P/E, P/S, EV/EBITDA, dividend yield, 52-week range

## Data Source

Uses **Yahoo Finance** via `yfinance` library. Falls back to realistic sample data when the API is unavailable.

For Bloomberg Terminal API integration, replace the data provider functions in `data_provider.py`.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project Structure

```
├── app.py              # Main Streamlit dashboard
├── data_provider.py    # Data fetching layer (yfinance + fallback)
├── sample_data.py      # Sample/simulated data for offline use
├── requirements.txt    # Python dependencies
└── .streamlit/
    └── config.toml     # Dark theme configuration
```

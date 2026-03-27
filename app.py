"""
S&P 500 Analysis Dashboard
Analyzes S&P 500, S&P Equal Weight, S&P 493, Mag7, and Sector ETFs.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from data_provider import (
    MAG7_TICKERS,
    SECTOR_ETFS,
    INDEX_TICKERS,
    get_price_history,
    get_normalized_prices,
    compute_sp493,
    build_fundamentals_df,
    build_growth_df,
    get_key_metrics_table,
    get_earnings_history,
    is_using_sample_data,
)

st.set_page_config(
    page_title="S&P 500 Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("S&P 500 Analysis Dashboard")
st.caption("Data source: Yahoo Finance (yfinance) | Indices, Mag7, and Sector ETFs")

# Sample data banner placeholder - shown after first data load
_sample_banner = st.empty()


# --- Sidebar ---
st.sidebar.header("Settings")

period = st.sidebar.selectbox(
    "Price History Period",
    ["1y", "2y", "3y", "5y", "10y", "max"],
    index=3,
)

analysis_tab = st.sidebar.radio(
    "Analysis Section",
    [
        "Index Comparison",
        "Mag7 Analysis",
        "Sector ETFs",
        "Fundamentals",
        "Valuation Metrics",
    ],
)


# --- Helper: plotly line chart ---
def make_line_chart(df: pd.DataFrame, title: str, yaxis_title: str = "Value") -> go.Figure:
    fig = go.Figure()
    for col in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[col], mode="lines", name=col))
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=yaxis_title,
        template="plotly_dark",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def make_bar_chart(df: pd.DataFrame, title: str, yaxis_title: str = "Value") -> go.Figure:
    fig = go.Figure()
    for col in df.columns:
        fig.add_trace(go.Bar(
            x=df.index.strftime("%Y") if hasattr(df.index, "strftime") else df.index,
            y=df[col],
            name=col,
        ))
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title=yaxis_title,
        template="plotly_dark",
        barmode="group",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


# =====================================================
# TAB 1: INDEX COMPARISON
# =====================================================
if analysis_tab == "Index Comparison":
    st.header("Index Comparison: S&P 500 vs Equal Weight vs S&P 493 vs Mag7")

    with st.spinner("Fetching index and Mag7 price data..."):
        # Normalized index prices
        index_tickers = list(INDEX_TICKERS.keys())
        idx_norm = get_normalized_prices(index_tickers, period)
        idx_norm.columns = [INDEX_TICKERS.get(c, c) for c in idx_norm.columns]

        # Mag7 average normalized
        mag7_norm = get_normalized_prices(MAG7_TICKERS, period)
        mag7_avg = mag7_norm.mean(axis=1)
        mag7_avg = (mag7_avg / mag7_avg.iloc[0]) * 100

        # S&P 493 approximation
        sp493 = compute_sp493(period)

        # Combine
        combined = idx_norm.copy()
        combined["Mag7 (avg)"] = mag7_avg
        combined["S&P 493 (approx)"] = sp493

    st.plotly_chart(
        make_line_chart(combined, "Normalized Performance (Base = 100)", "Index Level"),
        use_container_width=True,
    )

    # Returns table
    st.subheader("Period Returns")
    returns = {}
    for col in combined.columns:
        series = combined[col].dropna()
        if len(series) > 0:
            total_ret = (series.iloc[-1] / series.iloc[0] - 1) * 100
            returns[col] = {"Total Return %": round(total_ret, 2)}
    if returns:
        st.dataframe(pd.DataFrame(returns).T, use_container_width=True)


# =====================================================
# TAB 2: MAG7 ANALYSIS
# =====================================================
elif analysis_tab == "Mag7 Analysis":
    st.header("Magnificent 7 - Individual Performance")

    with st.spinner("Fetching Mag7 data..."):
        mag7_norm = get_normalized_prices(MAG7_TICKERS, period)

    st.plotly_chart(
        make_line_chart(mag7_norm, "Mag7 Normalized Prices (Base = 100)", "Price (normalized)"),
        use_container_width=True,
    )

    # YTD and period returns
    st.subheader("Returns Summary")
    with st.spinner("Computing returns..."):
        mag7_prices = get_price_history(MAG7_TICKERS, period)
        ret_data = []
        for ticker in MAG7_TICKERS:
            if ticker in mag7_prices.columns:
                s = mag7_prices[ticker].dropna()
                if len(s) > 1:
                    total = (s.iloc[-1] / s.iloc[0] - 1) * 100
                    ytd_start = s.loc[s.index >= f"{pd.Timestamp.now().year}-01-01"]
                    ytd = (s.iloc[-1] / ytd_start.iloc[0] - 1) * 100 if len(ytd_start) > 0 else None
                    ret_data.append({
                        "Ticker": ticker,
                        f"Total Return ({period}) %": round(total, 2),
                        "YTD Return %": round(ytd, 2) if ytd else None,
                        "Current Price": round(s.iloc[-1], 2),
                    })
        if ret_data:
            st.dataframe(pd.DataFrame(ret_data).set_index("Ticker"), use_container_width=True)


# =====================================================
# TAB 3: SECTOR ETFs
# =====================================================
elif analysis_tab == "Sector ETFs":
    st.header("S&P 500 Sector ETFs")

    etf_tickers = list(SECTOR_ETFS.keys())

    with st.spinner("Fetching sector ETF data..."):
        etf_norm = get_normalized_prices(etf_tickers, period)
        etf_norm.columns = [f"{t} ({SECTOR_ETFS[t]})" for t in etf_norm.columns if t in SECTOR_ETFS]

    st.plotly_chart(
        make_line_chart(etf_norm, "Sector ETF Performance (Base = 100)", "Index Level"),
        use_container_width=True,
    )

    # Sector returns heatmap
    st.subheader("Sector Returns")
    with st.spinner("Computing sector returns..."):
        etf_prices = get_price_history(etf_tickers, period)
        sector_returns = {}
        for ticker in etf_tickers:
            if ticker in etf_prices.columns:
                s = etf_prices[ticker].dropna()
                if len(s) > 1:
                    total = (s.iloc[-1] / s.iloc[0] - 1) * 100
                    # 1Y return
                    one_yr = s.last("365D")
                    ret_1y = (one_yr.iloc[-1] / one_yr.iloc[0] - 1) * 100 if len(one_yr) > 1 else None
                    sector_returns[f"{ticker} ({SECTOR_ETFS[ticker]})"] = {
                        f"Total ({period})%": round(total, 2),
                        "1Y Return %": round(ret_1y, 2) if ret_1y else None,
                    }
        if sector_returns:
            ret_df = pd.DataFrame(sector_returns).T.sort_values(f"Total ({period})%", ascending=False)
            st.dataframe(ret_df, use_container_width=True)

            # Bar chart of total returns
            fig = px.bar(
                ret_df.reset_index(),
                x="index",
                y=f"Total ({period})%",
                title=f"Sector ETF Total Returns ({period})",
                template="plotly_dark",
                color=f"Total ({period})%",
                color_continuous_scale="RdYlGn",
            )
            fig.update_layout(xaxis_title="Sector", yaxis_title="Return %", height=450)
            st.plotly_chart(fig, use_container_width=True)


# =====================================================
# TAB 4: FUNDAMENTALS
# =====================================================
elif analysis_tab == "Fundamentals":
    st.header("Fundamentals - Revenue, EBIT, EBITDA & Earnings Growth")

    fund_group = st.radio(
        "Select group",
        ["Mag7", "Sector ETFs"],
        horizontal=True,
    )

    tickers = MAG7_TICKERS if fund_group == "Mag7" else list(SECTOR_ETFS.keys())
    selected = st.multiselect(
        "Select tickers",
        tickers,
        default=tickers[:4],
    )

    if not selected:
        st.warning("Please select at least one ticker.")
    else:
        metric = st.selectbox("Metric", ["revenue", "ebit", "ebitda", "net_income"])
        metric_labels = {
            "revenue": "Revenue",
            "ebit": "EBIT",
            "ebitda": "EBITDA",
            "net_income": "Net Income (Earnings)",
        }

        view = st.radio("View", ["Absolute Values", "YoY Growth %"], horizontal=True)

        with st.spinner(f"Fetching {metric_labels[metric]} data..."):
            if view == "Absolute Values":
                df = build_fundamentals_df(selected, metric)
                if not df.empty:
                    # Convert to billions for readability
                    df_display = df / 1e9
                    st.plotly_chart(
                        make_bar_chart(df_display, f"{metric_labels[metric]} (USD Billions)", "USD (B)"),
                        use_container_width=True,
                    )
                    st.dataframe(df_display.round(2), use_container_width=True)
                else:
                    st.info("No data available for selected tickers/metric.")
            else:
                df = build_growth_df(selected, metric)
                if not df.empty:
                    st.plotly_chart(
                        make_bar_chart(df, f"{metric_labels[metric]} YoY Growth (%)", "Growth %"),
                        use_container_width=True,
                    )
                    st.dataframe(df.round(2), use_container_width=True)
                else:
                    st.info("No growth data available.")


# =====================================================
# TAB 5: VALUATION METRICS
# =====================================================
elif analysis_tab == "Valuation Metrics":
    st.header("Key Valuation Metrics")

    val_group = st.radio(
        "Select group",
        ["Mag7", "Sector ETFs", "Custom"],
        horizontal=True,
    )

    if val_group == "Mag7":
        tickers = MAG7_TICKERS
    elif val_group == "Sector ETFs":
        tickers = list(SECTOR_ETFS.keys())
    else:
        tickers_input = st.text_input("Enter tickers (comma-separated)", "AAPL,MSFT,GOOGL")
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

    if tickers:
        with st.spinner("Fetching valuation metrics..."):
            metrics_df = get_key_metrics_table(tickers)
            st.dataframe(
                metrics_df.style.format({
                    "Market Cap (B)": "{:.1f}",
                    "P/E (TTM)": "{:.1f}",
                    "Forward P/E": "{:.1f}",
                    "P/S": "{:.1f}",
                    "EV/EBITDA": "{:.1f}",
                    "Dividend Yield %": "{:.2f}",
                    "52w High": "{:.2f}",
                    "52w Low": "{:.2f}",
                }, na_rep="-"),
                use_container_width=True,
            )

        # Earnings surprise for selected ticker
        st.subheader("Earnings History (EPS)")
        selected_ticker = st.selectbox("Select ticker for earnings detail", tickers)
        if selected_ticker:
            with st.spinner("Fetching earnings data..."):
                earn_df = get_earnings_history(selected_ticker)
                if not earn_df.empty:
                    st.dataframe(earn_df, use_container_width=True)
                else:
                    st.info("No earnings history available.")


# --- Sample data banner ---
if is_using_sample_data():
    _sample_banner.warning(
        "Yahoo Finance API unavailable. Showing **sample/simulated data** for demonstration. "
        "Run locally with internet access for live market data."
    )

# --- Footer ---
st.divider()
st.caption(
    "**Data Source:** Yahoo Finance via yfinance (live data when available, sample data as fallback). "
    "S&P 493 is an approximation (S&P 500 minus estimated Mag7 contribution). "
    "For precise institutional data, consider Bloomberg Terminal API."
)

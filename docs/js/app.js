// ============================================================
// S&P 500 Dashboard - Client-side data fetching & rendering
// ============================================================

const MAG7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"];

// Approximate market caps in USD billions (used for cap-weighted Mag7 index)
const MAG7_MKTCAP = {
    AAPL: 3400, MSFT: 3100, GOOGL: 2300, AMZN: 2200,
    NVDA: 3300, META: 1600, TSLA: 1100,
};

const SECTOR_ETFS = {
    XLK: "Technology", XLF: "Financials", XLC: "Communication Svcs",
    XLY: "Consumer Disc.", XLV: "Health Care", XLI: "Industrials",
    XLP: "Consumer Staples", XLE: "Energy", XLU: "Utilities",
    XLB: "Materials", XLRE: "Real Estate"
};
const INDEX_MAP = { "^GSPC": "S&P 500", RSP: "S&P 500 Equal Weight" };

// Estimated Mag7 combined weight in S&P 500 at various start dates.
// This is the INITIAL weight (w0) - their weight grows naturally as they outperform.
// Sources: S&P Dow Jones Indices, various analyst reports.
const MAG7_INITIAL_WEIGHT = {
    2015: 0.11, 2016: 0.12, 2017: 0.14, 2018: 0.15, 2019: 0.16,
    2020: 0.18, 2021: 0.23, 2022: 0.20, 2023: 0.22, 2024: 0.28,
    2025: 0.30, 2026: 0.31,
};

const PLOTLY_LAYOUT = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: "#fafafa", size: 12 },
    margin: { t: 10, r: 20, b: 50, l: 60 },
    legend: { orientation: "h", y: -0.15, x: 0.5, xanchor: "center", font: { size: 11 } },
    xaxis: { gridcolor: "#363948", linecolor: "#363948" },
    yaxis: { gridcolor: "#363948", linecolor: "#363948" },
    height: 500,
};

const PLOTLY_CONFIG = { responsive: true, displayModeBar: false };

// --- State ---
let priceCache = {};
let currentTab = "indices";
let isLiveData = false;

// --- CORS Proxy for Yahoo Finance ---
const PROXIES = [
    (url) => `https://corsproxy.io/?${encodeURIComponent(url)}`,
    (url) => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
];

async function fetchWithProxy(url) {
    for (const makeProxy of [null, ...PROXIES]) {
        try {
            const fetchUrl = makeProxy ? makeProxy(url) : url;
            const resp = await fetch(fetchUrl, { signal: AbortSignal.timeout(12000) });
            if (resp.ok) {
                return await resp.json();
            }
        } catch (e) {
            continue;
        }
    }
    return null;
}

// --- Date range helpers ---
function getDateRange() {
    const startEl = document.getElementById("date-start");
    const endEl = document.getElementById("date-end");
    return { start: startEl.value, end: endEl.value };
}

function setDateRange(startStr, endStr) {
    document.getElementById("date-start").value = startStr;
    document.getElementById("date-end").value = endStr;
}

function initDateDefaults() {
    const today = new Date();
    const endStr = today.toISOString().slice(0, 10);
    const start = new Date(today);
    start.setFullYear(start.getFullYear() - 5);
    const startStr = start.toISOString().slice(0, 10);
    setDateRange(startStr, endStr);
}

function onShortcutChange() {
    const val = document.getElementById("period-shortcut").value;
    if (!val) return;
    const today = new Date();
    const endStr = today.toISOString().slice(0, 10);
    const start = new Date(today);
    if (val === "ytd") {
        start.setMonth(0, 1);
    } else {
        const years = parseInt(val);
        start.setFullYear(start.getFullYear() - years);
    }
    setDateRange(start.toISOString().slice(0, 10), endStr);
    priceCache = {};
    loadCurrentTab();
}

function onDateChange() {
    document.getElementById("period-shortcut").value = "";
    priceCache = {};
    loadCurrentTab();
}

function getDateLabel() {
    const { start, end } = getDateRange();
    return `${start} a ${end}`;
}

// --- Yahoo Finance Data Fetching ---
async function fetchYahooChart(symbol) {
    const { start, end } = getDateRange();
    const cacheKey = `${symbol}_${start}_${end}`;
    if (priceCache[cacheKey]) return priceCache[cacheKey];

    const period1 = Math.floor(new Date(start).getTime() / 1000);
    const period2 = Math.floor(new Date(end + "T23:59:59").getTime() / 1000);
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?period1=${period1}&period2=${period2}&interval=1d&includePrePost=false`;
    const data = await fetchWithProxy(url);

    if (data?.chart?.result?.[0]) {
        const result = data.chart.result[0];
        const timestamps = result.timestamp || [];
        const closes = result.indicators?.quote?.[0]?.close || [];
        const dates = timestamps.map((t) => new Date(t * 1000).toISOString().slice(0, 10));
        const parsed = { dates, closes, symbol };
        priceCache[cacheKey] = parsed;
        return parsed;
    }
    return null;
}

async function fetchMultiple(symbols) {
    const results = await Promise.allSettled(symbols.map((s) => fetchYahooChart(s)));
    const out = {};
    results.forEach((r, i) => {
        if (r.status === "fulfilled" && r.value) {
            out[symbols[i]] = r.value;
        }
    });
    return out;
}

function normalize(data) {
    if (!data.closes || data.closes.length === 0) return [];
    const firstValid = data.closes.find((v) => v != null);
    if (!firstValid) return [];
    return data.closes.map((v) => (v != null ? (v / firstValid) * 100 : null));
}

// --- S&P 493 Calculation ---
// Computes a cap-weighted Mag7 index, then removes its contribution from S&P 500
// using the estimated initial weight at the start date.
function computeCapWeightedMag7(mag7Data) {
    // Get relative weights from market caps
    const available = MAG7.filter((t) => mag7Data[t]);
    if (available.length === 0) return null;

    const totalCap = available.reduce((s, t) => s + MAG7_MKTCAP[t], 0);
    const weights = {};
    available.forEach((t) => { weights[t] = MAG7_MKTCAP[t] / totalCap; });

    // Normalize each stock's prices, then compute weighted average
    const refDates = mag7Data[available[0]].dates;
    const n = refDates.length;
    const weightedIndex = new Array(n).fill(null);

    for (let i = 0; i < n; i++) {
        let val = 0;
        let wSum = 0;
        for (const t of available) {
            const norm = normalize(mag7Data[t]);
            if (norm[i] != null) {
                val += weights[t] * norm[i];
                wSum += weights[t];
            }
        }
        weightedIndex[i] = wSum > 0 ? val / wSum : null;
    }
    return { dates: refDates, values: weightedIndex };
}

function getInitialWeight(startDate) {
    const year = new Date(startDate).getFullYear();
    // Find closest year in our weight table
    const years = Object.keys(MAG7_INITIAL_WEIGHT).map(Number).sort();
    let w = MAG7_INITIAL_WEIGHT[years[0]];
    for (const y of years) {
        if (y <= year) w = MAG7_INITIAL_WEIGHT[y];
    }
    return w;
}

function computeSP493(sp500Norm, mag7CapWeighted, startDate) {
    // S&P 493 = (SP500_norm - w0 * Mag7_capweighted_norm) / (1 - w0)
    // w0 = Mag7 weight at the START date (not current weight)
    const w0 = getInitialWeight(startDate);
    const sp493 = sp500Norm.map((v, i) => {
        if (v == null || mag7CapWeighted[i] == null) return null;
        return (v - w0 * mag7CapWeighted[i]) / (1 - w0);
    });
    // Re-normalize to base 100
    const first = sp493.find((v) => v != null);
    if (!first) return { values: sp493, w0 };
    return {
        values: sp493.map((v) => (v != null ? (v / first) * 100 : null)),
        w0,
    };
}

// --- Sample/Fallback Fundamentals Data ---
const FUNDAMENTALS = {
    AAPL: {
        years: ["2022", "2023", "2024", "2025E"],
        revenue: [394.3, 383.3, 391.0, 410.0],
        ebit: [119.4, 114.3, 118.7, 125.0],
        ebitda: [130.5, 125.8, 131.0, 138.0],
        net_income: [99.8, 97.0, 100.9, 106.0],
    },
    MSFT: {
        years: ["2022", "2023", "2024", "2025E"],
        revenue: [198.3, 211.9, 245.1, 275.0],
        ebit: [83.4, 88.5, 109.4, 125.0],
        ebitda: [97.9, 104.0, 125.0, 143.0],
        net_income: [72.7, 72.4, 88.1, 100.0],
    },
    GOOGL: {
        years: ["2022", "2023", "2024", "2025E"],
        revenue: [282.8, 307.4, 350.0, 390.0],
        ebit: [74.8, 84.3, 105.0, 120.0],
        ebitda: [90.8, 100.0, 120.0, 138.0],
        net_income: [59.9, 73.8, 90.0, 102.0],
    },
    AMZN: {
        years: ["2022", "2023", "2024", "2025E"],
        revenue: [514.0, 574.8, 638.0, 700.0],
        ebit: [12.2, 36.9, 55.0, 65.0],
        ebitda: [55.3, 85.5, 110.0, 125.0],
        net_income: [-2.7, 30.4, 44.0, 52.0],
    },
    NVDA: {
        years: ["2022", "2023", "2024", "2025E"],
        revenue: [27.0, 60.9, 130.5, 175.0],
        ebit: [4.2, 32.9, 82.0, 115.0],
        ebitda: [5.8, 34.8, 85.0, 120.0],
        net_income: [4.4, 29.8, 73.0, 100.0],
    },
    META: {
        years: ["2022", "2023", "2024", "2025E"],
        revenue: [116.6, 134.9, 162.0, 190.0],
        ebit: [28.9, 46.8, 60.0, 72.0],
        ebitda: [37.7, 56.5, 72.0, 85.0],
        net_income: [23.2, 39.1, 50.0, 60.0],
    },
    TSLA: {
        years: ["2022", "2023", "2024", "2025E"],
        revenue: [81.5, 96.8, 98.0, 110.0],
        ebit: [13.7, 8.9, 7.5, 10.0],
        ebitda: [17.9, 13.0, 12.0, 15.0],
        net_income: [12.6, 7.9, 7.0, 9.5],
    },
};

const VALUATION_DATA = {
    AAPL: { name: "Apple Inc.", mktCap: 3400, pe: 33.5, fwdPE: 30.1, ps: 8.7, evEbitda: 25.1, divYield: 0.45, high52: 260.1, low52: 169.2 },
    MSFT: { name: "Microsoft", mktCap: 3100, pe: 35.2, fwdPE: 29.8, ps: 12.6, evEbitda: 24.3, divYield: 0.72, high52: 468.4, low52: 362.9 },
    GOOGL: { name: "Alphabet", mktCap: 2300, pe: 25.0, fwdPE: 21.5, ps: 6.5, evEbitda: 17.8, divYield: 0.45, high52: 207.1, low52: 150.2 },
    AMZN: { name: "Amazon", mktCap: 2200, pe: 42.0, fwdPE: 32.5, ps: 3.4, evEbitda: 18.5, divYield: 0, high52: 242.5, low52: 166.2 },
    NVDA: { name: "NVIDIA", mktCap: 3300, pe: 45.0, fwdPE: 28.0, ps: 25.0, evEbitda: 38.5, divYield: 0.02, high52: 153.1, low52: 75.6 },
    META: { name: "Meta Platforms", mktCap: 1600, pe: 28.5, fwdPE: 23.0, ps: 9.8, evEbitda: 19.2, divYield: 0.35, high52: 740.9, low52: 442.6 },
    TSLA: { name: "Tesla", mktCap: 1100, pe: 120.0, fwdPE: 85.0, ps: 11.2, evEbitda: 72.0, divYield: 0, high52: 488.5, low52: 138.8 },
    XLK: { name: "Technology", mktCap: 72, pe: 32.0, fwdPE: 27.0, ps: null, evEbitda: null, divYield: 0.60, high52: 240, low52: 185 },
    XLF: { name: "Financials", mktCap: 42, pe: 16.5, fwdPE: 14.8, ps: null, evEbitda: null, divYield: 1.40, high52: 52, low52: 38 },
    XLC: { name: "Comm. Services", mktCap: 18, pe: 20.5, fwdPE: 18.0, ps: null, evEbitda: null, divYield: 0.70, high52: 100, low52: 72 },
    XLY: { name: "Consumer Disc.", mktCap: 20, pe: 28.0, fwdPE: 22.0, ps: null, evEbitda: null, divYield: 0.80, high52: 230, low52: 170 },
    XLV: { name: "Health Care", mktCap: 38, pe: 18.5, fwdPE: 16.2, ps: null, evEbitda: null, divYield: 1.50, high52: 155, low52: 125 },
    XLI: { name: "Industrials", mktCap: 18, pe: 22.0, fwdPE: 19.5, ps: null, evEbitda: null, divYield: 1.30, high52: 135, low52: 100 },
    XLP: { name: "Consumer Staples", mktCap: 16, pe: 21.0, fwdPE: 19.0, ps: null, evEbitda: null, divYield: 2.50, high52: 82, low52: 68 },
    XLE: { name: "Energy", mktCap: 38, pe: 12.5, fwdPE: 11.0, ps: null, evEbitda: null, divYield: 3.40, high52: 100, low52: 75 },
    XLU: { name: "Utilities", mktCap: 16, pe: 17.0, fwdPE: 16.0, ps: null, evEbitda: null, divYield: 2.80, high52: 80, low52: 60 },
    XLB: { name: "Materials", mktCap: 6, pe: 19.0, fwdPE: 17.5, ps: null, evEbitda: null, divYield: 1.80, high52: 95, low52: 75 },
    XLRE: { name: "Real Estate", mktCap: 6, pe: 35.0, fwdPE: 30.0, ps: null, evEbitda: null, divYield: 3.20, high52: 46, low52: 35 },
};

// ============================================================
// Tab switching
// ============================================================
function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelector(`.tab[data-tab="${tab}"]`).classList.add("active");
    document.querySelectorAll(".tab-content").forEach((s) => s.classList.remove("active"));
    document.getElementById(`tab-${tab}`).classList.add("active");
}

// ============================================================
// Loading
// ============================================================
function showLoading(text = "Carregando dados...") {
    document.getElementById("loading-text").textContent = text;
    document.getElementById("loading-overlay").classList.remove("hidden");
}

function hideLoading() {
    document.getElementById("loading-overlay").classList.add("hidden");
}

function setStatus(type, text) {
    const badge = document.getElementById("data-status");
    badge.className = `status-badge ${type}`;
    badge.textContent = text;
}

function setLastUpdated() {
    const el = document.getElementById("last-updated");
    el.textContent = `Atualizado: ${new Date().toLocaleTimeString("pt-BR")}`;
}

// ============================================================
// Rendering helpers
// ============================================================
function makeLineChart(divId, traces, title, yTitle = "Value") {
    const layout = {
        ...PLOTLY_LAYOUT,
        yaxis: { ...PLOTLY_LAYOUT.yaxis, title: yTitle },
    };
    // Title is handled by the h2/h3 in HTML, not inside the chart
    Plotly.newPlot(divId, traces, layout, PLOTLY_CONFIG);
}

function makeBarChart(divId, traces, title, yTitle = "Value") {
    const layout = {
        ...PLOTLY_LAYOUT,
        yaxis: { ...PLOTLY_LAYOUT.yaxis, title: yTitle },
        barmode: "group",
    };
    Plotly.newPlot(divId, traces, layout, PLOTLY_CONFIG);
}

function buildTable(headers, rows) {
    let html = "<table><thead><tr>";
    headers.forEach((h) => (html += `<th>${h}</th>`));
    html += "</tr></thead><tbody>";
    rows.forEach((row) => {
        html += "<tr>";
        row.forEach((cell, i) => {
            let cls = "";
            if (i > 0 && typeof cell === "number") {
                cls = cell > 0 ? "positive" : cell < 0 ? "negative" : "";
            }
            const display = typeof cell === "number" ? cell.toFixed(2) : (cell ?? "-");
            html += `<td class="${cls}">${display}</td>`;
        });
        html += "</tr>";
    });
    html += "</tbody></table>";
    return html;
}

function calcReturn(closes) {
    if (!closes || closes.length < 2) return null;
    const first = closes.find((v) => v != null);
    const last = [...closes].reverse().find((v) => v != null);
    if (!first || !last) return null;
    return ((last / first - 1) * 100);
}

// ============================================================
// TAB 1: Index Comparison
// ============================================================
async function loadIndices() {
    const [indexData, mag7Data] = await Promise.all([
        fetchMultiple(["^GSPC", "RSP"]),
        fetchMultiple(MAG7),
    ]);

    const hasLiveData = Object.keys(indexData).length > 0;

    if (!hasLiveData) {
        setStatus("error", "API indisponivel");
        document.getElementById("chart-indices").innerHTML =
            '<p style="padding:40px;text-align:center;color:#a0a4b0;">Nao foi possivel carregar dados de preco. Verifique sua conexao ou tente novamente.</p>';
        return;
    }

    isLiveData = true;
    setStatus("live", "Dados ao vivo");

    const traces = [];
    const dateLabel = getDateLabel();

    // S&P 500
    if (indexData["^GSPC"]) {
        const norm = normalize(indexData["^GSPC"]);
        traces.push({ x: indexData["^GSPC"].dates, y: norm, name: "S&P 500", type: "scatter", mode: "lines" });
    }

    // Equal Weight
    if (indexData["RSP"]) {
        const norm = normalize(indexData["RSP"]);
        traces.push({ x: indexData["RSP"].dates, y: norm, name: "S&P 500 Equal Weight", type: "scatter", mode: "lines" });
    }

    // Mag7 cap-weighted
    if (Object.keys(mag7Data).length > 0) {
        const mag7CW = computeCapWeightedMag7(mag7Data);

        if (mag7CW) {
            traces.push({
                x: mag7CW.dates, y: mag7CW.values,
                name: "Mag7 (cap-weighted)", type: "scatter", mode: "lines",
                line: { width: 3 },
            });

            // S&P 493 approximation
            if (indexData["^GSPC"]) {
                const sp500Norm = normalize(indexData["^GSPC"]);
                const { start } = getDateRange();
                const { values: sp493Values, w0 } = computeSP493(sp500Norm, mag7CW.values, start);
                traces.push({
                    x: indexData["^GSPC"].dates, y: sp493Values,
                    name: `S&P 493 (approx, w0=${(w0 * 100).toFixed(0)}%)`,
                    type: "scatter", mode: "lines",
                    line: { dash: "dot" },
                });
            }
        }
    }

    makeLineChart("chart-indices", traces, "", "Indice (Base=100)");

    // Returns table
    const headers = ["Index", `Retorno Total (${dateLabel})`];
    const rows = [];
    for (const t of traces) {
        const closes = t.y.filter((v) => v != null);
        if (closes.length > 1) {
            const ret = closes[closes.length - 1] - 100;
            rows.push([t.name, ret]);
        }
    }
    document.getElementById("table-indices-returns").innerHTML = buildTable(headers, rows);
}

// ============================================================
// TAB 2: Mag7
// ============================================================
async function loadMag7() {
    const mag7Data = await fetchMultiple(MAG7);

    if (Object.keys(mag7Data).length === 0) {
        document.getElementById("chart-mag7").innerHTML =
            '<p style="padding:40px;text-align:center;color:#a0a4b0;">Dados indisponiveis.</p>';
        return;
    }

    const traces = Object.entries(mag7Data).map(([symbol, d]) => ({
        x: d.dates, y: normalize(d),
        name: symbol, type: "scatter", mode: "lines",
    }));

    makeLineChart("chart-mag7", traces, "", "Preco (Base=100)");

    const dateLabel = getDateLabel();
    const headers = ["Ticker", `Retorno Total %`, "Preco Atual"];
    const rows = Object.entries(mag7Data).map(([symbol, d]) => {
        const ret = calcReturn(d.closes);
        const lastPrice = [...d.closes].reverse().find((v) => v != null);
        return [symbol, ret, lastPrice];
    });
    document.getElementById("table-mag7-returns").innerHTML = buildTable(headers, rows);
}

// ============================================================
// TAB 3: Sectors
// ============================================================
async function loadSectors() {
    const etfSymbols = Object.keys(SECTOR_ETFS);
    const etfData = await fetchMultiple(etfSymbols);

    if (Object.keys(etfData).length === 0) {
        document.getElementById("chart-sectors").innerHTML =
            '<p style="padding:40px;text-align:center;color:#a0a4b0;">Dados indisponiveis.</p>';
        return;
    }

    const traces = Object.entries(etfData).map(([symbol, d]) => ({
        x: d.dates, y: normalize(d),
        name: `${symbol} (${SECTOR_ETFS[symbol]})`, type: "scatter", mode: "lines",
    }));

    makeLineChart("chart-sectors", traces, "", "Indice (Base=100)");

    const dateLabel = getDateLabel();
    const returnData = Object.entries(etfData)
        .map(([symbol, d]) => ({ symbol, label: `${symbol}`, ret: calcReturn(d.closes) }))
        .filter((r) => r.ret != null)
        .sort((a, b) => b.ret - a.ret);

    const barTrace = {
        x: returnData.map((r) => r.label),
        y: returnData.map((r) => r.ret),
        type: "bar",
        marker: {
            color: returnData.map((r) => (r.ret >= 0 ? "#00cc96" : "#ef553b")),
        },
    };

    makeBarChart("chart-sector-bars", [barTrace], "", "Retorno %");

    const headers = ["Setor", "ETF", `Retorno %`];
    const rows = returnData.map((r) => [SECTOR_ETFS[r.symbol] || r.symbol, r.symbol, r.ret]);
    document.getElementById("table-sector-returns").innerHTML = buildTable(headers, rows);
}

// ============================================================
// TAB 4: Fundamentals
// ============================================================
function renderFundamentals() {
    const metric = document.getElementById("fund-metric").value;
    const view = document.getElementById("fund-view").value;
    const metricLabels = { revenue: "Revenue", ebit: "EBIT", ebitda: "EBITDA", net_income: "Net Income" };

    const tickers = MAG7.filter((t) => FUNDAMENTALS[t]);

    if (view === "absolute") {
        const traces = tickers.map((t) => ({
            x: FUNDAMENTALS[t].years,
            y: FUNDAMENTALS[t][metric],
            name: t, type: "bar",
        }));
        makeBarChart("chart-fundamentals", traces, "", "USD (B)");

        const headers = ["Ano", ...tickers];
        const rows = FUNDAMENTALS[tickers[0]].years.map((year, i) => [
            year,
            ...tickers.map((t) => FUNDAMENTALS[t][metric][i]),
        ]);
        document.getElementById("table-fundamentals").innerHTML = buildTable(headers, rows);
    } else {
        const traces = tickers.map((t) => {
            const vals = FUNDAMENTALS[t][metric];
            const growth = vals.map((v, i) => (i === 0 ? null : ((v - vals[i - 1]) / Math.abs(vals[i - 1])) * 100));
            return {
                x: FUNDAMENTALS[t].years.slice(1),
                y: growth.slice(1),
                name: t, type: "bar",
            };
        });
        makeBarChart("chart-fundamentals", traces, "", "Crescimento %");

        const headers = ["Ano", ...tickers];
        const years = FUNDAMENTALS[tickers[0]].years.slice(1);
        const rows = years.map((year, i) => [
            year,
            ...tickers.map((t) => {
                const vals = FUNDAMENTALS[t][metric];
                const idx = i + 1;
                return ((vals[idx] - vals[idx - 1]) / Math.abs(vals[idx - 1])) * 100;
            }),
        ]);
        document.getElementById("table-fundamentals").innerHTML = buildTable(headers, rows);
    }
}

// ============================================================
// TAB 5: Valuation
// ============================================================
function renderValuation() {
    const group = document.getElementById("val-group").value;
    const tickers = group === "mag7" ? MAG7 : Object.keys(SECTOR_ETFS);

    const headers = ["Ticker", "Name", "Mkt Cap (B)", "P/E", "Fwd P/E", "P/S", "EV/EBITDA", "Div Yield %", "52w High", "52w Low"];
    const rows = tickers.filter((t) => VALUATION_DATA[t]).map((t) => {
        const d = VALUATION_DATA[t];
        return [t, d.name, d.mktCap, d.pe, d.fwdPE, d.ps, d.evEbitda, d.divYield, d.high52, d.low52];
    });
    document.getElementById("table-valuation").innerHTML = buildTable(headers, rows);
}

// ============================================================
// Refresh / Load
// ============================================================
async function loadCurrentTab() {
    showLoading();
    try {
        switch (currentTab) {
            case "indices": await loadIndices(); break;
            case "mag7": await loadMag7(); break;
            case "sectors": await loadSectors(); break;
            case "fundamentals": renderFundamentals(); break;
            case "valuation": renderValuation(); break;
        }
        setLastUpdated();
    } catch (e) {
        console.error("Error loading data:", e);
        setStatus("error", "Erro ao carregar");
    }
    hideLoading();
}

async function refreshAllData() {
    const btn = document.getElementById("refresh-btn");
    btn.classList.add("loading");
    btn.disabled = true;

    priceCache = {};

    showLoading("Atualizando todos os dados...");
    try {
        await loadIndices();
        await loadMag7();
        await loadSectors();
        renderFundamentals();
        renderValuation();
        setLastUpdated();
    } catch (e) {
        console.error("Refresh error:", e);
        setStatus("error", "Erro na atualizacao");
    }
    hideLoading();
    btn.classList.remove("loading");
    btn.disabled = false;
}

// Override tab switch to load data
const origSwitchTab = switchTab;
window.switchTab = function (tab) {
    origSwitchTab(tab);
    loadCurrentTab();
};

// ============================================================
// Init
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
    initDateDefaults();
    loadCurrentTab();
});

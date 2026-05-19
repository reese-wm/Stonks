const form = document.querySelector("#ticker-form");
const input = document.querySelector("#ticker-input");
let chart;

form.addEventListener("submit", (event) => {
  event.preventDefault();
  loadTicker(input.value.trim() || "AAPL");
});

loadUnderDollarDashboard();
loadTrackingSummary();
loadTicker(input.value);

async function loadTicker(symbol) {
  setStatus(`Loading ${symbol.toUpperCase()}...`);
  try {
    const response = await fetch(`/api/ticker/${encodeURIComponent(symbol)}`);
    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }
    const data = await response.json();
    render(data);
    loadQuantIntelligence(data.symbol);
    setStatus("Loaded. This dashboard is research support only, not personalized financial advice.");
  } catch (error) {
    setStatus(`Could not load ${symbol.toUpperCase()}: ${error.message}`);
  }
}

async function loadQuantIntelligence(symbol) {
  const panel = document.querySelector("#quant-intelligence");
  panel.innerHTML = `<p>Compiling Quant Intelligence...</p>`;
  try {
    const response = await fetch(`/api/ticker/${encodeURIComponent(symbol)}/quant-intelligence`);
    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }
    const report = await response.json();
    panel.innerHTML = `
      <p>${report.summary}</p>
      <div class="quant-score-grid">
        ${metricHtml("Data", number(report.data_coverage_score))}
        ${metricHtml("Backtest", number(report.backtest_readiness_score))}
        ${metricHtml("ML ready", number(report.ml_readiness_score))}
      </div>
      <h3>Signal Stack</h3>
      <ul>${(report.signal_stack || []).slice(0, 3).map((item) => `<li>${item}</li>`).join("")}</ul>
      <h3>Backtest Plan</h3>
      <ul>${(report.backtest_plan || []).slice(0, 3).map((item) => `<li>${item}</li>`).join("")}</ul>
      <p class="description">${report.generated_by} / Inspired by OpenBB, Backtrader, Zipline, FinRL, and LEAN patterns.</p>
    `;
  } catch (error) {
    panel.innerHTML = `<p>Quant Intelligence unavailable: ${error.message}</p>`;
  }
}

async function loadUnderDollarDashboard() {
  try {
    const response = await fetch("/api/under-dollar-leaders");
    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }
    const data = await response.json();
    renderUnderDollarDashboard(data);
  } catch (error) {
    document.querySelector("#leaders-freshness").textContent = `Unable to load under-$1 feed: ${error.message}`;
  }
}

function render(data) {
  renderQuote(data);
  renderProfile(data.profile);
  renderScore(data.score);
  renderTechnicals(data.indicators);
  renderTipRanks(data.tipranks);
  renderLists(data);
  renderChart(data.historical);
  document.querySelector("#provider-status").textContent = JSON.stringify(data.provider_status, null, 2);
  loadTrackingSummary(data.symbol);
}

async function loadTrackingSummary(symbol = input.value.trim() || "AAPL") {
  try {
    const [healthResponse, historyResponse, projectionResponse, quoteResponse] = await Promise.all([
      fetch("/api/data-health"),
      fetch("/api/tracking/under-dollar-history?limit=1"),
      fetch("/api/tracking/projections?limit=1"),
      fetch(`/api/tracking/quotes/${encodeURIComponent(symbol)}?limit=1`)
    ]);
    const health = await healthResponse.json();
    const history = await historyResponse.json();
    const projections = await projectionResponse.json();
    const quotes = await quoteResponse.json();
    const database = health.database || {};
    const latest = history[0];
    const projection = projections[0];
    const quote = quotes[0];
    document.querySelector("#tracking-summary").innerHTML = [
      pill(`${database.under_dollar_snapshot_count || 0} under-$1 snapshots`),
      pill(`${database.quote_snapshot_count || 0} quote snapshots`),
      pill(latest?.generated_at ? `last mover scan ${dateTime(latest.generated_at)}` : "no mover scans yet"),
      pill(projection ? `top projection ${projection.symbol} ${number(projection.score)}` : "no projections yet"),
      pill(quote ? `${quote.symbol} tracked ${dateTime(quote.fetched_at)}` : `${symbol.toUpperCase()} not tracked yet`)
    ].join("");
  } catch (error) {
    document.querySelector("#tracking-summary").textContent = `Tracking status unavailable: ${error.message}`;
  }
}

function renderUnderDollarDashboard(data) {
  document.querySelector("#leaders-freshness").textContent =
    `${data.freshness_note} Checked ${data.leaders.length} under-$1 stocks. Generated ${dateTime(data.generated_at)}.`;
  document.querySelector("#ai-provider").textContent = data.ai_provider || "rules engine";
  document.querySelector("#ai-summary").textContent =
    data.ai_summary || data.warnings?.join(" ") || "Projection feed is using available provider data only.";
  renderTopProjectedBuy(data.top_projected_buy);
  renderHeatmap(data.leaders || []);

  document.querySelector("#leader-list").innerHTML = data.leaders.length
    ? data.leaders.slice(0, 20).map(renderLeaderRow).join("")
    : `<p class="summary-copy">Add FMP_API_KEY in .env to load provider-fetched under-$1 movers.</p>`;

  requestAnimationFrame(() => {
    for (const leader of data.leaders.slice(0, 20)) {
      drawSparkline(`spark-${leader.symbol}`, leader.sparkline || [], leader.change_percent);
    }
  });

  document.querySelector("#projection-list").innerHTML = data.projections.length
    ? data.projections.map(renderProjectionCard).join("")
    : `<p class="summary-copy">No projections available yet.</p>`;
}

function renderHeatmap(leaders) {
  const panel = document.querySelector("#heatmap-grid");
  if (!panel) return;
  const rows = leaders.length ? leaders.slice(0, 25) : [
    { symbol: "AAPL", change_percent: 1.23 },
    { symbol: "MSFT", change_percent: 0.95 },
    { symbol: "NVDA", change_percent: 2.15 },
    { symbol: "AMZN", change_percent: 1.45 },
    { symbol: "GOOGL", change_percent: 1.12 },
    { symbol: "META", change_percent: 0.89 },
    { symbol: "TSLA", change_percent: -0.65 }
  ];
  panel.innerHTML = rows.map((item, index) => {
    const move = Number(item.change_percent || 0);
    const sizeClass = index < 3 ? "large" : "";
    return `<div class="heat-tile ${move < 0 ? "negative" : ""} ${sizeClass}">
      <strong>${item.symbol}</strong>
      <span>${move >= 0 ? "+" : ""}${number(move)}%</span>
    </div>`;
  }).join("");
}

function renderTopProjectedBuy(topBuy) {
  const selected = topBuy?.selected;
  if (!selected) {
    document.querySelector("#top-buy-symbol").textContent = "No candidate selected";
    document.querySelector("#top-buy-score").textContent = "--";
    document.querySelector("#top-buy-thesis").textContent = topBuy?.warnings?.join(" ") || "No under-$1 universe was available to rank.";
    document.querySelector("#top-buy-behavior").innerHTML = "";
    return;
  }
  const behavior = selected.buyer_behavior || {};
  const components = selected.score_components || {};
  document.querySelector("#top-buy-symbol").textContent = `${selected.symbol} / ${selected.label}`;
  document.querySelector("#top-buy-score").textContent = number(selected.score);
  document.querySelector("#top-buy-thesis").textContent = topBuy.ai_summary
    ? `${topBuy.ai_summary} ${selected.thesis}`
    : selected.thesis;
  document.querySelector("#top-buy-behavior").innerHTML = [
    behaviorMetric("Volume", compactNumber(behavior.reported_volume)),
    behaviorMetric("Rel vol", `${number(behavior.relative_volume_proxy)}x`),
    behaviorMetric("Close strength", number(behavior.close_strength_proxy)),
    behaviorMetric("Up/down days", `${behavior.up_days_in_sparkline ?? "--"}/${behavior.down_days_in_sparkline ?? "--"}`),
    behaviorMetric("Buyer behavior", number(components.buyer_behavior)),
    behaviorMetric("Risk penalty", number(components.risk_penalty))
  ].join("");
}

function renderLeaderRow(item) {
  const trend = Number(item.change_percent || 0) >= 0 ? "positive" : "negative";
  return `
    <div class="leader-row">
      <div>
        <div class="ticker">${item.symbol}</div>
        <div class="company">${item.exchange || ""}</div>
      </div>
      <div class="company">${item.name || "Unknown company"}</div>
      <div class="price-cell"><strong>${money(item.price)}</strong><span>price</span></div>
      <div class="move-cell ${trend}"><strong>${number(item.change_percent)}%</strong><span>move</span></div>
      <canvas id="spark-${item.symbol}" class="sparkline" width="300" height="84"></canvas>
    </div>`;
}

function renderProjectionCard(item) {
  const evidence = (item.evidence || []).slice(0, 2).map((value) => `<li>${value}</li>`).join("");
  const risks = (item.risks || []).slice(0, 1).map((value) => `<li>${value}</li>`).join("");
  return `
    <div class="projection-card">
      <header>
        <strong>${item.symbol} / ${item.label}</strong>
        <span class="projection-score">${number(item.score)}</span>
      </header>
      <p>${item.thesis}</p>
      <ul>${evidence}${risks}</ul>
    </div>`;
}

function renderQuote(data) {
  const quote = data.quote;
  document.querySelector("#quote-symbol").textContent = data.symbol;
  document.querySelector("#asset-mark").textContent = data.symbol.slice(0, 1);
  document.querySelector("#order-symbol").textContent = data.symbol;
  document.querySelector("#quote-price").textContent = quote?.price ? money(quote.price) : "--";
  document.querySelector("#limit-price").value = quote?.price ? Number(quote.price).toFixed(2) : "--";
  const change = document.querySelector("#quote-change");
  if (quote?.change !== null && quote?.change !== undefined) {
    change.textContent = `${number(quote.change)} (${number(quote.change_percent)}%)`;
    change.className = `quote-change ${quote.change >= 0 ? "positive" : "negative"}`;
  } else {
    change.textContent = "--";
    change.className = "quote-change";
  }
  document.querySelector("#quote-freshness").textContent = quote?.freshness
    ? `${quote.freshness.display_note} Fetched ${dateTime(quote.freshness.fetched_at)}.`
    : "Quote unavailable. Add an API key in .env.";
  renderOrderBook(quote);
}

function renderProfile(profile) {
  document.querySelector("#profile-name").textContent = profile?.name || "--";
  document.querySelector("#profile-meta").textContent = [profile?.exchange, profile?.sector, profile?.industry]
    .filter(Boolean)
    .join(" / ") || "--";
  document.querySelector("#profile-description").textContent = profile?.description || "Profile unavailable.";
}

function renderScore(score) {
  document.querySelector("#rating-label").textContent = score.rating_label;
  document.querySelector("#composite-score").textContent = number(score.composite_score);
  fillList("#bull-case", score.bull_case);
  fillList("#bear-case", score.bear_case);
  fillList("#risk-notes", [...score.risk_notes, ...score.data_warnings]);
}

function renderTechnicals(indicators) {
  const metrics = [
    ["SMA 20", indicators.sma_20],
    ["SMA 50", indicators.sma_50],
    ["SMA 200", indicators.sma_200],
    ["RSI 14", indicators.rsi_14],
    ["MACD", indicators.macd],
    ["MACD Signal", indicators.macd_signal],
    ["ATR 14", indicators.atr_14],
    ["Relative Volume", indicators.relative_volume],
    ["52W High Distance", percent(indicators.high_52_week_distance)],
    ["52W Low Distance", percent(indicators.low_52_week_distance)]
  ];
  document.querySelector("#technical-list").innerHTML = metrics
    .map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${formatValue(value)}</strong></div>`)
    .join("");
}

function renderTipRanks(tipranks) {
  const panel = document.querySelector("#tipranks-panel");
  if (!tipranks) {
    panel.innerHTML = `<div class="metric"><span>Status</span><strong>Disabled or unavailable</strong></div>`;
    return;
  }
  const targets = tipranks.price_targets || {};
  const sentiment = tipranks.news_sentiment || {};
  panel.innerHTML = [
    metricHtml("Mean target", money(targets.mean)),
    metricHtml("Median target", money(targets.median)),
    metricHtml("Target range", targets.lowest && targets.highest ? `${money(targets.lowest)} / ${money(targets.highest)}` : "--"),
    metricHtml("Estimates", targets.number_of_estimates ?? "--"),
    metricHtml("Bullish news", sentiment.bullish_percent !== null && sentiment.bullish_percent !== undefined ? `${number(sentiment.bullish_percent * 100)}%` : "--"),
    metricHtml("Bearish news", sentiment.bearish_percent !== null && sentiment.bearish_percent !== undefined ? `${number(sentiment.bearish_percent * 100)}%` : "--"),
    metricHtml("News buzz", number(sentiment.buzz)),
    metricHtml("Articles/week", sentiment.articles_in_last_week ?? "--")
  ].join("");
}

function renderLists(data) {
  const news = data.news.length
    ? data.news
        .slice(0, 12)
        .map((item) => `<div class="item"><a href="${item.url}" target="_blank" rel="noreferrer">${item.headline}</a><time>${item.source_name} / ${dateTime(item.published_at)}</time><p>Sentiment ${number(item.sentiment_score)} / credibility ${number(item.credibility_score)}</p></div>`)
        .join("")
    : `<p class="description">No recent news available from configured providers.</p>`;
  document.querySelector("#news-list").innerHTML = news;

  const filings = data.filings.length
    ? data.filings
        .map((item) => `<div class="item"><a href="${item.url}" target="_blank" rel="noreferrer">${item.filing_type}</a><time>${item.filing_date || ""} / ${item.source}</time></div>`)
        .join("")
    : `<p class="description">No SEC filings found. This may be a non-U.S. ticker or the SEC lookup may be unavailable.</p>`;
  document.querySelector("#filing-list").innerHTML = filings;
}

function renderChart(rows) {
  const labels = rows.map((row) => row.date);
  const closes = rows.map((row) => row.close);
  const sma20 = movingAverage(closes, 20);
  const sma50 = movingAverage(closes, 50);
  const sma200 = movingAverage(closes, 200);
  const ctx = document.querySelector("#price-chart");
  chart?.destroy();
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        dataset("Close", closes, "#12d7ff", 2.5),
        dataset("SMA20", sma20, "#00f0a6", 1),
        dataset("SMA50", sma50, "#a855f7", 1),
        dataset("SMA200", sma200, "#ff3d62", 1)
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: "index" },
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#6f8aa2", maxTicksLimit: 8 }, grid: { color: "rgba(18, 215, 255, .06)" } },
        y: { position: "right", ticks: { color: "#7f9ab1", callback: (value) => `$${value}` }, grid: { color: "rgba(18, 215, 255, .08)" } }
      }
    }
  });
}

function renderOrderBook(quote) {
  const asks = document.querySelector("#orderbook-asks");
  const bids = document.querySelector("#orderbook-bids");
  if (!asks || !bids) return;
  const price = Number(quote?.price || 189.84);
  const change = Number(quote?.change || 0);
  const changePercent = Number(quote?.change_percent || 0);
  const sizes = [2300, 1800, 1200, 900, 1100];
  const askRows = sizes.map((size, index) => ({
    price: price + (index + 1) * 0.01,
    size,
    total: size * (index + 8)
  })).reverse();
  const bidRows = sizes.map((size, index) => ({
    price: price - (index + 1) * 0.01,
    size: size + index * 260,
    total: size * (index + 1)
  }));
  asks.innerHTML = askRows.map(bookRow).join("");
  bids.innerHTML = bidRows.map(bookRow).join("");
  document.querySelector("#book-mid-price").textContent = money(price);
  document.querySelector("#book-mid-change").textContent = `${change >= 0 ? "+" : ""}${number(change)} (${changePercent >= 0 ? "+" : ""}${number(changePercent)}%)`;
  document.querySelector("#spread-value").textContent = "0.01 (0.01%)";
}

function bookRow(row) {
  return `<div class="book-row"><span>${Number(row.price).toFixed(2)}</span><span>${compactNumber(row.size)}</span><span>${compactNumber(row.total)}</span></div>`;
}

function drawSparkline(canvasId, points, changePercent) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !points.length) return;
  const ctx = canvas.getContext("2d");
  const values = points.map((point) => Number(point.close)).filter((value) => !Number.isNaN(value));
  if (values.length < 2) return;
  const width = canvas.width;
  const height = canvas.height;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = Number(changePercent || 0) >= 0 ? "#29d17d" : "#ff5c63";
  ctx.lineWidth = 4;
  ctx.beginPath();
  values.forEach((value, index) => {
    const x = (index / (values.length - 1)) * width;
    const y = height - ((value - min) / range) * (height - 10) - 5;
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function movingAverage(values, period) {
  return values.map((_, index) => {
    if (index + 1 < period) return null;
    const slice = values.slice(index + 1 - period, index + 1);
    return slice.reduce((sum, value) => sum + value, 0) / period;
  });
}

function dataset(label, data, color, width) {
  return {
    label,
    data,
    borderColor: color,
    borderWidth: width,
    pointRadius: 0,
    tension: 0.18,
    fill: label === "Close",
    backgroundColor: label === "Close" ? "rgba(18, 215, 255, 0.08)" : "transparent"
  };
}

function fillList(selector, items) {
  document.querySelector(selector).innerHTML = items.map((item) => `<li>${item}</li>`).join("");
}

function pill(text) {
  return `<span class="tracking-pill">${text}</span>`;
}

function metricHtml(label, value) {
  return `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`;
}

function behaviorMetric(label, value) {
  return `<div class="behavior-metric"><span>${label}</span><strong>${value || "--"}</strong></div>`;
}

function setStatus(message) {
  document.querySelector("#status-strip").textContent = message;
}

function money(value) {
  return value === null || value === undefined ? "--" : `$${Number(value).toFixed(4)}`;
}

function number(value) {
  return value === null || value === undefined || Number.isNaN(Number(value)) ? "--" : Number(value).toFixed(2);
}

function compactNumber(value) {
  return value === null || value === undefined || Number.isNaN(Number(value))
    ? "--"
    : Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(Number(value));
}

function percent(value) {
  return value === null || value === undefined ? null : `${number(value)}%`;
}

function formatValue(value) {
  if (typeof value === "string") return value;
  return number(value);
}

function dateTime(value) {
  if (!value) return "unknown time";
  return new Date(value).toLocaleString();
}

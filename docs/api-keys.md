# API Keys

This app keeps provider keys server-side in `.env`. Do not paste provider keys into browser code, mobile apps, screenshots, or public GitHub repos.

## Required First

### Massive

Use for live-ish stock snapshots, top movers, full-market snapshots, and OHLC bars.

- Get a key: https://massive.com/docs/rest/quickstart
- Env var: `MASSIVE_API_KEY`
- Notes: best provider for the live under-$1 feed and quote snapshots. Check your plan for real-time vs delayed access.

### Financial Modeling Prep

Use for quotes, historical prices, company profile, fundamentals, news, and the under-$1 screener.

- Get a key: https://site.financialmodelingprep.com/developer/docs
- Env var: `FMP_API_KEY`
- Notes: check display/licensing terms before redistributing market data.

### OpenAI

Use for AI summaries and Top Projections analysis after the backend has fetched structured market data.

- Get a key: https://platform.openai.com/api-keys
- Env var: `OPENAI_API_KEY`
- Optional model var: `OPENAI_MODEL`
- Notes: the app prompt tells the model to use only provided JSON and not invent prices or recommendations.

## Strong Additions

### Finnhub

Use for quote backup, company news, analyst trends, market news, and insider transactions.

- Get a key: https://finnhub.io/register
- Docs: https://finnhub.io/docs/api
- Env var: `FINNHUB_API_KEY`

### Alpha Vantage

Use for fallback time series, indicators, news sentiment, and macro data.

- Get a key: https://www.alphavantage.co/support/#api-key
- Docs: https://www.alphavantage.co/documentation/
- Env var: `ALPHA_VANTAGE_API_KEY`
- Alias accepted by this app: `ALPHAVANTAGE_API_KEY`

### NewsAPI

Use for broad news discovery and cross-checking source coverage.

- Get a key: https://newsapi.org/register
- Docs: https://newsapi.org/docs
- Env var: `NEWS_API_KEY`

### TipRanks-style Sentiment and Targets

The optional TipRanks provider is adapted from the MIT-licensed `janlukasschroeder/tipranks-api-v2` endpoint pattern. It does not use an official API key. It calls TipRanks public web JSON endpoints for analyst targets and news sentiment.

- Env var: `TIPRANKS_ENABLED=true`
- Optional env var: `TIPRANKS_USER_AGENT`
- Optional env var: `TIPRANKS_COOKIE`
- Notes: only enable this if your use is permitted by TipRanks terms. If TipRanks returns `403 Forbidden`, the app keeps running and marks TipRanks data unavailable.

## Later Upgrades

### Polygon.io

Use later for higher-quality real-time, intraday, WebSocket, and options data.

- Get a key: https://polygon.io/dashboard/signup
- Docs: https://polygon.io/docs
- Env var: `POLYGON_API_KEY`

### Twelve Data

Use later for backup OHLCV, forex, crypto, and global-market coverage.

- Get a key: https://twelvedata.com/pricing
- Docs: https://twelvedata.com/docs
- Env var: `TWELVEDATA_API_KEY`

### Tiingo

Use later for EOD prices and financial news.

- Get a key: https://www.tiingo.com/account/api/token
- Docs: https://www.tiingo.com/documentation/
- Env var: `TIINGO_API_KEY`

## What ChatGPT Can and Cannot Do

ChatGPT/OpenAI can analyze and summarize the data your backend retrieves from FMP, Finnhub, Alpha Vantage, NewsAPI, and SEC EDGAR.

It cannot create third-party API keys for FMP, Finnhub, Alpha Vantage, NewsAPI, Polygon, Twelve Data, or Tiingo. Those accounts must be created by you with each provider.

After keys are in `.env`, restart the backend and check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/data-health
```

The dashboard should then change provider statuses from `missing ...` to `configured`.

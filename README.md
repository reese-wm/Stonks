# Stonks Research Dashboard

FastAPI-based stock research dashboard for quote data, daily price charts, technical indicators, news, SEC filings, and explainable research classifications.

This app is research support only. It avoids guaranteed predictions and direct personalized financial advice.

## Quick Start

```powershell
cd D:\Stonks
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe main.py
```

Open `http://127.0.0.1:8000`.

## API Keys

Add keys to `.env`:

```bash
FMP_API_KEY=
MASSIVE_API_KEY=
ALPHA_VANTAGE_API_KEY=
OPENAI_API_KEY=
DATABASE_URL=sqlite:///./data/stonks.db
UNDER_DOLLAR_REFRESH_SECONDS=300
SEC_USER_AGENT=Stonks research app your-email@example.com
```

FMP is the primary provider, Alpha Vantage is a fallback/secondary source, and SEC EDGAR is used for official U.S. filings. External responses are cached in `data/cache`.

See [docs/api-keys.md](docs/api-keys.md) for provider signup links and recommended priority.

## Current MVP

- Ticker research endpoint: `/api/ticker/{symbol}`
- Data health endpoint: `/api/data-health`
- Under-$1 movers and projections endpoint: `/api/under-dollar-leaders`
- Top projected buy endpoint for the top 100 under-$1 universe: `/api/under-dollar-top-buy`
- Stored latest under-$1 snapshot: `/api/under-dollar-leaders/latest`
- Manual refresh endpoint: `POST /api/under-dollar-leaders/refresh`
- Framework-inspired Quant Intelligence endpoint: `/api/ticker/{symbol}/quant-intelligence`
- Tracking history endpoints under `/api/tracking/*`
- Quote card with provider/freshness label
- Dark top dashboard for top-performing sub-dollar stocks
- Daily close chart with SMA overlays
- SMA, EMA, RSI, MACD, Bollinger Bands, ATR, relative volume, 52-week distance
- Recent provider news with credibility scoring
- SEC filing links for U.S. companies
- Research classification with bull case, bear case, risk notes, and data warnings
- Optional OpenAI/ChatGPT-style projection summary using only backend-fetched structured data
- Buyer-behavior proxy scoring from observable market data: volume, relative-volume proxy, close strength, recent trend, and liquidity risk
- Optional TipRanks-style analyst target and news sentiment panel, adapted from the MIT-licensed `janlukasschroeder/tipranks-api-v2` endpoint pattern
- Quant Intelligence endpoint inspired by OpenBB, Backtrader, Zipline, FinRL, and QuantConnect LEAN methodology
- SQLite tracking database by default, configurable via `DATABASE_URL`
- APScheduler background refresh for repeated under-$1 scans

## OpenAI Projection Feed

Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in `.env` to let the Top Projections feed summarize under-$1 movers. The prompt explicitly tells the model to use only fetched provider data and avoid personalized advice or invented numbers.

TipRanks integration is optional because the referenced community package uses TipRanks public web JSON endpoints, not an official key-based API. Set `TIPRANKS_ENABLED=true` only when your use is permitted by TipRanks terms. If the endpoint returns `403`, the app continues without TipRanks data.

## Tracking Database

By default the app creates `data/stonks.db` and stores:

- under-$1 screener snapshots
- screener leader rows and sparklines
- projection history
- ticker quote snapshots when a ticker is viewed
- API/provider health events

Use `DATABASE_URL` to switch to Postgres/Supabase later.

## Boundary

The dashboard uses evidence language such as "watchlist candidate", "mixed evidence", and "high-risk setup". It does not output guaranteed predictions, automated trading actions, or personalized buy/sell instructions.

# Stonks App API Integration Plan for Codex

Purpose: Build a stock research dashboard that helps the user make more informed trading decisions by combining market prices, fundamentals, SEC filings, credible news, technical indicators, and AI-generated summaries.

Important: This app is for research support only. Do not present outputs as guaranteed predictions or financial advice. Avoid “Buy/Sell” language unless the app includes proper disclaimers and the user understands the risk.

---

## 1. Core Build Principle

Do not scrape stock websites such as TradingView, Yahoo Finance, Seeking Alpha, Morningstar, or Bloomberg.

Use official APIs wherever possible.

Reasons:
- Scraping can violate terms of service.
- Scraped layouts break often.
- Market data licensing is serious.
- API keys must stay server-side.
- Codex should build a stable, maintainable system.

---

## 2. Recommended API Stack

### Phase 1: Starter Stack

Use these first:

```env
FMP_API_KEY=your_fmp_key_here
FINNHUB_API_KEY=your_finnhub_key_here
ALPHAVANTAGE_API_KEY=your_alpha_vantage_key_here
NEWS_API_KEY=your_newsapi_key_here
```

### Recommended use by provider

| Provider | Use In App | Priority |
|---|---|---|
| Financial Modeling Prep | Quotes, historical prices, fundamentals, statements, ratios, earnings, company profile, news | High |
| Finnhub | Real-time-ish quotes, company news, insider transactions, analyst ratings, market news | High |
| Alpha Vantage | Historical time series, technical indicators, market data backup | Medium |
| NewsAPI | Broad credible news discovery | Medium |
| SEC EDGAR | Official filings, 10-K, 10-Q, 8-K, company facts | High |
| Polygon.io | Upgrade option for professional-grade market data | Later |
| Twelve Data | Backup/alternative for OHLCV, forex, crypto, indicators | Later |

---

## 3. API References

### Financial Modeling Prep
Website:
https://site.financialmodelingprep.com/developer/docs

Useful endpoints:
```text
Quote:
https://financialmodelingprep.com/stable/quote?symbol=AAPL&apikey=FMP_API_KEY

Historical EOD:
https://financialmodelingprep.com/stable/historical-price-eod/light?symbol=AAPL&apikey=FMP_API_KEY

Company Profile:
https://financialmodelingprep.com/stable/profile?symbol=AAPL&apikey=FMP_API_KEY

Income Statement:
https://financialmodelingprep.com/stable/income-statement?symbol=AAPL&apikey=FMP_API_KEY

Balance Sheet:
https://financialmodelingprep.com/stable/balance-sheet-statement?symbol=AAPL&apikey=FMP_API_KEY

Cash Flow:
https://financialmodelingprep.com/stable/cash-flow-statement?symbol=AAPL&apikey=FMP_API_KEY

Stock News:
https://financialmodelingprep.com/stable/news/stock?symbols=AAPL&apikey=FMP_API_KEY
```

Use FMP as the primary source for:
- Current quote
- Historical price/volume
- Fundamentals
- Financial statements
- Ratios
- Earnings calendar
- Company profile
- Basic stock news

Licensing caution:
Displaying or redistributing FMP data may require a data display/licensing agreement depending on usage and plan.

---

### Finnhub
Website:
https://finnhub.io/docs/api

Useful endpoints:
```text
Quote:
https://finnhub.io/api/v1/quote?symbol=AAPL&token=FINNHUB_API_KEY

Company News:
https://finnhub.io/api/v1/company-news?symbol=AAPL&from=2026-05-01&to=2026-05-18&token=FINNHUB_API_KEY

Market News:
https://finnhub.io/api/v1/news?category=general&token=FINNHUB_API_KEY

Recommendation Trends:
https://finnhub.io/api/v1/stock/recommendation?symbol=AAPL&token=FINNHUB_API_KEY

Insider Transactions:
https://finnhub.io/api/v1/stock/insider-transactions?symbol=AAPL&token=FINNHUB_API_KEY
```

Use Finnhub for:
- Quote backup
- News backup
- Analyst recommendation trends
- Insider transactions
- Sentiment-related signals
- Market news

---

### Alpha Vantage
Website:
https://www.alphavantage.co/documentation/

Useful endpoints:
```text
Daily Time Series:
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=AAPL&apikey=ALPHAVANTAGE_API_KEY

Daily Adjusted:
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=AAPL&apikey=ALPHAVANTAGE_API_KEY

RSI:
https://www.alphavantage.co/query?function=RSI&symbol=AAPL&interval=daily&time_period=14&series_type=close&apikey=ALPHAVANTAGE_API_KEY

MACD:
https://www.alphavantage.co/query?function=MACD&symbol=AAPL&interval=daily&series_type=close&apikey=ALPHAVANTAGE_API_KEY

News and Sentiment:
https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers=AAPL&apikey=ALPHAVANTAGE_API_KEY
```

Use Alpha Vantage for:
- Backup historical prices
- Technical indicators
- News sentiment
- Macro/economic data later

Note:
Free tier limits can be restrictive. Cache aggressively.

---

### NewsAPI
Website:
https://newsapi.org/docs/endpoints/everything

Useful endpoint:
```text
https://newsapi.org/v2/everything?q=AAPL OR Apple stock&language=en&sortBy=publishedAt&apiKey=NEWS_API_KEY
```

Use NewsAPI for:
- Broad news discovery
- Cross-checking finance-specific news
- Pulling reputable source links

Credibility filter:
Prioritize:
- Reuters
- Associated Press
- Bloomberg
- Wall Street Journal
- CNBC
- Financial Times
- MarketWatch
- Barron's
- The Globe and Mail
- Financial Post
- Official company press releases
- SEC filings

Avoid over-weighting:
- Random blogs
- Pump-style sites
- Unverified social posts
- Single anonymous sources
- Promotional newsletters

---

### SEC EDGAR
Website:
https://www.sec.gov/search-filings/edgar-application-programming-interfaces

Useful base endpoints:
```text
Submissions:
https://data.sec.gov/submissions/CIK0000320193.json

Company Facts:
https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json
```

SEC requires a proper User-Agent header:
```http
User-Agent: StonksApp/1.0 contact@email.com
```

Use SEC EDGAR for:
- 10-K
- 10-Q
- 8-K
- Company facts
- Official filings
- Risk factor extraction later

Important:
Ticker-to-CIK mapping is required. Build or import a mapping table.

---

### Polygon.io
Website:
https://polygon.io/

Use later for:
- Higher quality real-time/historical market data
- WebSockets
- Intraday data
- Options data
- Professional upgrade path

Do not build the first version around Polygon unless the user has a paid plan.

---

### Twelve Data
Website:
https://twelvedata.com/docs

Use later for:
- Backup quote/time series
- Forex
- Crypto
- Technical indicators
- Global markets

---

## 4. App Architecture

### Recommended stack

```text
Frontend:
- Next.js or React
- Tailwind CSS
- TradingView Lightweight Charts or Recharts
- Ticker search interface
- Watchlist dashboard

Backend:
- FastAPI Python preferred
- Alternative: Node/Express or Next.js API routes
- All API keys stored server-side only

Database:
- PostgreSQL / Supabase
- Redis optional for short-term cache

AI Layer:
- OpenAI API or local LLM-compatible summarizer
- Never let AI invent numbers
- AI summaries must reference fetched data objects only
```

---

## 5. Security Rules

Never expose API keys in:
- React frontend
- Browser code
- Public GitHub
- APK/mobile app bundle
- Client-side environment variables

Use:
```text
Backend route:
GET /api/stocks/{symbol}/summary
```

Backend then calls providers using server-side keys.

`.env.example`:
```env
FMP_API_KEY=
FINNHUB_API_KEY=
ALPHAVANTAGE_API_KEY=
NEWS_API_KEY=
POLYGON_API_KEY=
TWELVEDATA_API_KEY=
OPENAI_API_KEY=
DATABASE_URL=
APP_CONTACT_EMAIL=
```

Add `.env` to `.gitignore`:
```gitignore
.env
.env.local
.env.production
```

---

## 6. Database Schema

### stocks
```sql
CREATE TABLE stocks (
  id SERIAL PRIMARY KEY,
  symbol TEXT UNIQUE NOT NULL,
  company_name TEXT,
  exchange TEXT,
  sector TEXT,
  industry TEXT,
  cik TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### price_snapshots
```sql
CREATE TABLE price_snapshots (
  id SERIAL PRIMARY KEY,
  symbol TEXT NOT NULL,
  price NUMERIC,
  change NUMERIC,
  change_percent NUMERIC,
  volume BIGINT,
  market_cap BIGINT,
  provider TEXT,
  captured_at TIMESTAMP DEFAULT NOW()
);
```

### historical_prices
```sql
CREATE TABLE historical_prices (
  id SERIAL PRIMARY KEY,
  symbol TEXT NOT NULL,
  date DATE NOT NULL,
  open NUMERIC,
  high NUMERIC,
  low NUMERIC,
  close NUMERIC,
  adjusted_close NUMERIC,
  volume BIGINT,
  provider TEXT,
  UNIQUE(symbol, date, provider)
);
```

### fundamentals
```sql
CREATE TABLE fundamentals (
  id SERIAL PRIMARY KEY,
  symbol TEXT NOT NULL,
  fiscal_period TEXT,
  fiscal_year INTEGER,
  revenue NUMERIC,
  gross_profit NUMERIC,
  operating_income NUMERIC,
  net_income NUMERIC,
  eps NUMERIC,
  total_assets NUMERIC,
  total_liabilities NUMERIC,
  total_debt NUMERIC,
  free_cash_flow NUMERIC,
  provider TEXT,
  captured_at TIMESTAMP DEFAULT NOW()
);
```

### news_articles
```sql
CREATE TABLE news_articles (
  id SERIAL PRIMARY KEY,
  symbol TEXT,
  title TEXT NOT NULL,
  source TEXT,
  url TEXT UNIQUE,
  published_at TIMESTAMP,
  summary TEXT,
  sentiment_score NUMERIC,
  credibility_score NUMERIC,
  provider TEXT,
  captured_at TIMESTAMP DEFAULT NOW()
);
```

### stock_scores
```sql
CREATE TABLE stock_scores (
  id SERIAL PRIMARY KEY,
  symbol TEXT NOT NULL,
  technical_score NUMERIC,
  fundamental_score NUMERIC,
  news_score NUMERIC,
  risk_score NUMERIC,
  overall_score NUMERIC,
  explanation TEXT,
  calculated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 7. Backend Routes

Build these routes:

```text
GET /api/health
GET /api/stocks/search?q=apple
GET /api/stocks/{symbol}
GET /api/stocks/{symbol}/quote
GET /api/stocks/{symbol}/historical?range=1y
GET /api/stocks/{symbol}/fundamentals
GET /api/stocks/{symbol}/news
GET /api/stocks/{symbol}/filings
GET /api/stocks/{symbol}/score
GET /api/stocks/{symbol}/ai-summary
POST /api/watchlist
GET /api/watchlist
DELETE /api/watchlist/{symbol}
```

---

## 8. Data Fetching Strategy

### Quote data
Refresh:
- On-demand when user opens ticker page
- Cache for 60 seconds during market hours
- Cache for 15 minutes outside market hours

### Historical prices
Refresh:
- Daily after market close
- On-demand if missing

### Fundamentals
Refresh:
- Daily or weekly
- Force refresh after earnings reports

### News
Refresh:
- Every 15-30 minutes for watched tickers
- On-demand for ticker detail page

### SEC filings
Refresh:
- Daily
- More often for watchlist tickers later

---

## 9. Technical Indicators

Prefer calculating indicators internally from OHLCV data.

Start with:
- SMA 20
- SMA 50
- SMA 200
- EMA 12
- EMA 26
- RSI 14
- MACD
- Bollinger Bands
- Average volume
- Relative volume
- 52-week high/low
- Max drawdown
- ATR

Avoid treating indicators as guarantees.

---

## 10. Scoring Model

Create a research score, not a prediction.

### Technical score: 0-100
Inputs:
- Price vs SMA 50
- Price vs SMA 200
- RSI
- MACD trend
- Relative volume
- 52-week strength

Example:
```text
+15 if price > SMA50
+15 if price > SMA200
+10 if SMA50 > SMA200
+10 if RSI between 45 and 70
+10 if MACD histogram improving
+10 if relative volume > 1.2
+10 if close is within 15% of 52-week high
-10 if RSI > 80
-15 if price < SMA200
```

### Fundamental score: 0-100
Inputs:
- Revenue growth
- EPS growth
- Free cash flow
- Debt-to-equity
- Gross margin
- Operating margin
- Valuation vs sector

### News score: 0-100
Inputs:
- Credible positive articles
- Credible negative articles
- Recency
- Source credibility
- SEC filing severity
- Earnings surprises
- Analyst upgrades/downgrades

### Risk score: 0-100
Higher score means higher risk.

Inputs:
- Beta
- Volatility
- Debt
- Earnings inconsistency
- Negative filings
- Large drawdown
- Heavy insider selling
- High short interest if available

### Overall score
```text
overall_score =
  technical_score * 0.30 +
  fundamental_score * 0.30 +
  news_score * 0.25 +
  (100 - risk_score) * 0.15
```

Display as:
```text
Research Rating:
- Strong Watch
- Watch
- Neutral
- High Risk
- Avoid for Now
```

Avoid:
```text
Buy
Sell
Guaranteed
Easy money
Prediction
```

---

## 11. AI Summary Rules

AI must summarize only data retrieved by backend.

Prompt template:
```text
You are a stock research assistant. Use only the provided JSON data.
Do not invent prices, metrics, ratings, or news.
Do not provide financial advice.
Summarize:
1. Current price action
2. Technical setup
3. Fundamental strength/weakness
4. Recent credible news
5. Key risks
6. What to monitor next

Return concise plain English for a retail trader.
```

Output format:
```json
{
  "summary": "...",
  "bull_case": ["..."],
  "bear_case": ["..."],
  "risks": ["..."],
  "watch_items": ["..."],
  "confidence": "low | medium | high",
  "data_sources_used": ["FMP", "Finnhub", "SEC EDGAR", "NewsAPI"]
}
```

---

## 12. Frontend Pages

### Dashboard
- Watchlist
- Market overview
- Biggest movers
- Recent alerts
- News feed

### Ticker Detail Page
Sections:
- Header: symbol, company, exchange, sector
- Current quote
- Interactive chart
- Technical indicators
- Fundamentals card
- Recent news
- SEC filings
- AI summary
- Score breakdown
- Risk warnings

### Watchlist Page
Columns:
- Symbol
- Price
- Daily %
- Volume
- Technical score
- News score
- Risk score
- Last refreshed

### News Page
Filters:
- Symbol
- Source
- Sentiment
- Date
- Credibility

---

## 13. Codex Build Tasks

### Task 1: Project setup
Create:
```text
/backend
/frontend
/docs
.env.example
README.md
```

Backend:
- FastAPI
- httpx
- pydantic
- SQLAlchemy or SQLModel
- PostgreSQL driver

Frontend:
- Next.js
- Tailwind
- charting library
- simple dashboard layout

### Task 2: Environment config
Create config loader:
- Reads API keys from `.env`
- Validates required keys
- Never sends keys to frontend

### Task 3: Provider clients
Create:
```text
backend/app/providers/fmp.py
backend/app/providers/finnhub.py
backend/app/providers/alphavantage.py
backend/app/providers/newsapi.py
backend/app/providers/sec_edgar.py
```

Each provider should:
- Use retries
- Handle rate limits
- Return normalized data
- Log provider errors safely
- Never crash the whole app when one provider fails

### Task 4: Normalized data models
Create normalized internal models:
```text
Quote
HistoricalBar
CompanyProfile
FinancialStatement
NewsArticle
Filing
StockScore
```

### Task 5: Cache layer
Implement:
- Short cache for quotes
- Long cache for fundamentals
- Daily cache for historical data
- News cache with source URL deduplication

### Task 6: Scoring engine
Create:
```text
backend/app/services/scoring.py
```

Functions:
```python
calculate_technical_score(historical_prices)
calculate_fundamental_score(fundamentals)
calculate_news_score(news_articles)
calculate_risk_score(data)
calculate_overall_score(...)
```

### Task 7: AI summary engine
Create:
```text
backend/app/services/ai_summary.py
```

Rules:
- Only summarize provided JSON.
- Include “not financial advice” disclaimer in UI.
- Include source list.
- If data is missing, say so.

### Task 8: Frontend dashboard
Create pages:
```text
/
/watchlist
/stocks/[symbol]
/news
```

### Task 9: Error handling
If a provider fails:
- Show partial data
- Display provider status
- Do not hide stale timestamps
- Never hallucinate missing data

### Task 10: Deployment
Recommended:
- Render, Railway, Fly.io, or VPS for backend
- Supabase for PostgreSQL
- Vercel for frontend if using Next.js
- Store keys in host environment variables

---

## 14. Example Backend Provider Code

```python
# backend/app/providers/fmp.py

import os
import httpx

FMP_API_KEY = os.getenv("FMP_API_KEY")
BASE_URL = "https://financialmodelingprep.com/stable"

async def get_quote(symbol: str) -> dict:
    if not FMP_API_KEY:
        raise RuntimeError("FMP_API_KEY is not configured")

    url = f"{BASE_URL}/quote"
    params = {"symbol": symbol.upper(), "apikey": FMP_API_KEY}

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    if not data:
        return {"symbol": symbol.upper(), "error": "No quote data returned"}

    item = data[0]
    return {
        "symbol": item.get("symbol"),
        "price": item.get("price"),
        "change": item.get("change"),
        "change_percent": item.get("changesPercentage"),
        "volume": item.get("volume"),
        "market_cap": item.get("marketCap"),
        "provider": "FMP"
    }
```

---

## 15. Example API Route

```python
# backend/app/routes/stocks.py

from fastapi import APIRouter, HTTPException
from app.providers.fmp import get_quote

router = APIRouter(prefix="/api/stocks", tags=["stocks"])

@router.get("/{symbol}/quote")
async def stock_quote(symbol: str):
    try:
        return await get_quote(symbol)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Quote provider failed: {str(exc)}")
```

---

## 16. Legal and UX Disclaimers

Add to UI footer:
```text
Stonks provides research tools and market data summaries for informational purposes only.
It is not financial advice. Market data may be delayed, incomplete, or inaccurate.
Always verify information with your broker or official filings before making trades.
```

Add to AI summary:
```text
This summary is generated from available data sources and may miss important context.
It should not be treated as a buy/sell recommendation.
```

---

## 17. Best First Version Scope

Do not overbuild.

MVP should include:
- Search ticker
- Current quote
- Historical chart
- Basic technicals
- Company profile
- Recent credible news
- AI summary
- Watchlist
- Research score

Skip for first version:
- Options flow
- Social sentiment
- Auto-trading
- Brokerage integration
- Complex backtesting
- Real-time websockets
- Payment plans
- Mobile app

---

## 18. Final Codex Prompt

Use this prompt in Codex:

```text
Build a stock research dashboard called Stonks.

Use a FastAPI backend and a Next.js frontend. All API keys must be stored server-side in environment variables and must never be exposed to the browser. Integrate Financial Modeling Prep, Finnhub, Alpha Vantage, NewsAPI, and SEC EDGAR as provider clients. Do not scrape websites.

Create normalized backend models for quotes, historical prices, company profiles, fundamentals, news articles, SEC filings, and stock scores. Implement caching so quote data is cached briefly, fundamentals are cached longer, and historical price data is cached daily.

Create routes for ticker search, quote, historical prices, fundamentals, news, SEC filings, stock score, AI summary, and watchlist. The AI summary must only summarize retrieved JSON data and must not invent numbers or provide financial advice.

Frontend pages should include a dashboard, watchlist, ticker detail page, and news page. The ticker detail page should show current quote, chart, technical indicators, fundamentals, recent credible news, SEC filings, score breakdown, and AI summary.

Include disclaimers that the app is for informational research only and not financial advice.
```

---

## 19. Future Upgrade Ideas

Later add:
- Polygon.io real-time market data
- WebSocket quote streaming
- Options flow
- Earnings call transcript summaries
- Insider buying alerts
- SEC filing AI risk extraction
- TSX support
- Backtesting
- Custom alert rules
- Portfolio tracking
- Broker import, but not trade execution

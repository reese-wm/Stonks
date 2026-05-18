# Codex Build Plan: Stock Analysis & Trading Research Dashboard

**Project purpose:** Build a research-support app that gathers credible market data, filings, financial statements, price action, technical indicators, and news/sentiment to help the user make more informed trading and investing decisions.

**Important boundary:** This app should provide research support, scoring, alerts, and explanations. It should not present itself as a guaranteed prediction engine or as personalized financial advice. Avoid language like “Buy now” or “Guaranteed trade.” Prefer “Bullish evidence,” “Bearish evidence,” “Watchlist candidate,” “High-risk setup,” or “Needs more research.”

---

## 1. Best Plan of Attack

### Phase 1 — Build the reliable core first
Start with a single-stock dashboard that works very well for U.S. and Canadian tickers.

Core features:

1. Ticker search
2. Current quote / latest available price
3. Historical OHLCV chart
4. Technical indicators calculated internally
5. Company profile
6. Financial statements and key ratios
7. SEC/SEDAR-style filing links where available
8. Recent credible news feed
9. News sentiment summary
10. Bull / bear / risk summary
11. Watchlist and alerts
12. Data freshness labels

The app should always show:

- Data provider
- Timestamp of latest update
- Whether the quote is real-time, delayed, or end-of-day
- Whether the source permits display/redistribution

---

## 2. Recommended Data Source Strategy

Do **not** scrape TradingView, Seeking Alpha, Morningstar, Yahoo Finance, or similar sites unless their terms explicitly allow your use case. Scraping creates fragility, possible legal/licensing issues, and unreliable app behaviour.

Use official APIs wherever possible.

### Tier 1: Start here

#### Financial Modeling Prep, or FMP
Use for:

- Current stock quote
- Historical prices
- Intraday prices depending on plan
- Financial statements
- Key metrics
- Analyst estimates where available
- Earnings calendar
- Company profile
- Stock news

Why:

- Broad coverage
- Easy developer experience
- Strong all-in-one starter source
- Useful for fundamentals and prices

Caution:

- Check licensing before displaying or redistributing data to other users.
- Their pricing page states that displaying or redistributing sourced data may require a Data Display and Licensing Agreement.

Reference:
https://site.financialmodelingprep.com/developer/docs
https://site.financialmodelingprep.com/developer/docs/pricing
https://site.financialmodelingprep.com/developer/docs/stable/stock-news

---

#### Alpha Vantage
Use for:

- Historical and real-time stock market data
- Technical indicators
- Options data depending on plan
- Economic indicators
- News and sentiment

Why:

- Good API documentation
- Free tier available
- Built-in technical indicators can be used for comparison against internally calculated values
- News and sentiment endpoint is useful for AI-style market interpretation

Caution:

- Free tier is limited.
- For production or frequent refreshing, expect to need a paid tier.

Reference:
https://www.alphavantage.co/
https://www.alphavantage.co/documentation/

---

#### SEC EDGAR APIs
Use for:

- Official U.S. filings
- 10-K, 10-Q, 8-K, insider filings, XBRL facts
- Verifying fundamentals directly from official filings

Why:

- Primary source
- Free
- Credible
- Essential for serious company research

Caution:

- Respect SEC fair-access rules.
- Cache results and avoid aggressive polling.
- Provide a proper User-Agent header when requesting SEC data.

Reference:
https://www.sec.gov/search-filings/edgar-application-programming-interfaces
https://www.sec.gov/about/developer-resources

---

## 3. Strong Add-On Data Sources

### Polygon.io / Massive.com
Use for:

- Real-time and historical stock market data
- Trades
- Quotes
- Aggregates
- WebSocket streaming
- Market snapshots

Why:

- Better suited for active trading workflows than many free APIs
- Strong for intraday and real-time market data

Caution:

- Real-time exchange data usually costs money.
- Licensing and exchange fees matter.

Reference:
https://massive.com/stocks
https://massive.com/docs/rest/stocks/overview

---

### Finnhub
Use for:

- Real-time market data
- Company fundamentals
- Economic data
- Alternative data
- Company news
- Market news
- News sentiment

Why:

- Good all-around source
- Useful for news and alternative data
- Easy to integrate

Reference:
https://finnhub.io/docs/api
https://finnhub.io/docs/api/company-news
https://finnhub.io/docs/api/market-news

---

### Intrinio
Use for:

- Real-time stock prices
- Business-grade financial data
- Fundamentals
- Metrics and ratios
- Institutional holdings
- News feeds

Why:

- More professional/business oriented
- Good option if the app becomes more serious or commercial

Caution:

- More expensive than hobby APIs.
- Use only when the app is ready for higher-quality paid data.

Reference:
https://intrinio.com/
https://docs.intrinio.com/documentation/web_api/get_security_snapshots_v2
https://intrinio.com/pricing

---

### Tiingo
Use for:

- End-of-day prices
- Financial news
- Crypto and FX data
- Historical news

Why:

- Good historical EOD data
- Useful institutional-style news API

Reference:
https://www.tiingo.com/
https://www.tiingo.com/documentation/
https://www.tiingo.com/documentation/end-of-day
https://www.tiingo.com/documentation/news

---

### Marketaux
Use for:

- Global financial news
- Entity/ticker-tagged news
- Sentiment and topic filtering

Why:

- Useful as a secondary news/sentiment provider
- Helps compare sentiment from multiple sources

Reference:
https://www.marketaux.com/
https://www.marketaux.com/documentation

---

## 4. Sources to Avoid as Primary APIs

### TradingView
Use for:

- Charting inspiration
- Manual research
- Potential charting library integration with your own data feed

Do not use as:

- A backend source for pulling market data or indicator values

Reason:

- TradingView states it does not have an API that gives access to data or indicator values.

Reference:
https://www.tradingview.com/support/solutions/43000474413-i-need-access-to-your-api-in-order-to-get-data-or-indicator-values/
https://www.tradingview.com/free-charting-libraries/

---

### Yahoo Finance / yfinance
Use for:

- Personal research
- Quick prototyping only

Do not use as:

- Production-grade backend data source

Reason:

- Unofficial libraries can break and may not be appropriate for commercial use.

Reference:
https://github.com/ranaroussi/yfinance

---

### IEX Cloud
Do not use.

Reason:

- IEX Cloud API products were retired on August 31, 2024.

Reference:
https://iexcloud.org/

---

## 5. Suggested Tech Stack

### Frontend
Use:

- Next.js or React
- TypeScript
- Tailwind CSS
- shadcn/ui components
- Lightweight Charts, Recharts, or TradingView Lightweight Charts

Frontend pages:

1. `/dashboard`
2. `/ticker/[symbol]`
3. `/watchlist`
4. `/alerts`
5. `/news`
6. `/settings/data-sources`
7. `/admin/data-health`

---

### Backend
Use either:

Option A:

- Python FastAPI
- Pydantic
- SQLAlchemy
- APScheduler or Celery

Option B:

- Node.js / Express or Next.js API routes
- Prisma ORM
- BullMQ for background jobs

Recommended for this project:

- Python FastAPI for financial calculations and data ingestion
- Next.js frontend for UI
- PostgreSQL/Supabase database
- Redis for queue/cache if needed

---

### Hosting
Good starter setup:

- Frontend: Vercel or Render
- Backend: Render, Railway, Fly.io, or a VPS
- Database: Supabase Postgres
- Secrets: environment variables only

Do not commit API keys to GitHub.

---

## 6. Database Schema Draft

### `symbols`
Fields:

- id
- symbol
- exchange
- name
- country
- currency
- sector
- industry
- provider_symbol
- active
- created_at
- updated_at

### `quotes`
Fields:

- id
- symbol_id
- price
- change
- change_percent
- volume
- market_cap
- provider
- quote_type: real_time / delayed / eod
- source_timestamp
- fetched_at

### `ohlcv_daily`
Fields:

- id
- symbol_id
- date
- open
- high
- low
- close
- adjusted_close
- volume
- provider

### `ohlcv_intraday`
Fields:

- id
- symbol_id
- interval
- timestamp
- open
- high
- low
- close
- volume
- provider

### `financial_statements`
Fields:

- id
- symbol_id
- statement_type: income / balance_sheet / cash_flow
- period: annual / quarterly
- fiscal_date
- data_json
- provider
- fetched_at

### `metrics`
Fields:

- id
- symbol_id
- date
- pe_ratio
- forward_pe
- peg_ratio
- price_to_sales
- price_to_book
- debt_to_equity
- current_ratio
- gross_margin
- operating_margin
- net_margin
- revenue_growth_yoy
- eps_growth_yoy
- free_cash_flow
- return_on_equity
- return_on_assets
- provider

### `news_articles`
Fields:

- id
- symbol_id nullable
- headline
- source_name
- url
- published_at
- summary
- provider
- sentiment_score
- relevance_score
- credibility_score
- tickers_json
- fetched_at

### `filings`
Fields:

- id
- symbol_id
- filing_type
- filing_date
- accession_number
- url
- source
- summary
- risk_flags_json
- fetched_at

### `technical_indicators`
Fields:

- id
- symbol_id
- date_or_timestamp
- interval
- sma_20
- sma_50
- sma_200
- ema_12
- ema_26
- rsi_14
- macd
- macd_signal
- macd_histogram
- atr_14
- bollinger_upper
- bollinger_middle
- bollinger_lower

### `research_scores`
Fields:

- id
- symbol_id
- as_of
- technical_score
- fundamental_score
- news_score
- risk_score
- momentum_score
- valuation_score
- composite_score
- rating_label
- explanation_json

### `watchlist`
Fields:

- id
- user_id
- symbol_id
- notes
- target_entry
- target_exit
- stop_loss
- alert_rules_json
- created_at

---

## 7. Data Freshness Rules

Every displayed value should have a freshness label.

Examples:

- Real-time: updated within the last few seconds/minutes, depending on provider
- Delayed: provider-defined delay, often 15 minutes depending on exchange and plan
- End-of-day: last official market close
- Stale: older than expected update window

UI examples:

- `AAPL $212.34 — delayed quote, fetched 2026-05-18 10:31 PT, provider: FMP`
- `RSI calculated from daily OHLCV through 2026-05-17 close`
- `News sentiment based on 16 articles from last 72 hours`

---

## 8. News Credibility System

The app should not treat all news equally.

Give higher credibility to:

- SEC filings
- Company investor relations press releases
- Major financial news outlets
- Exchange notices
- Earnings call transcripts
- Reputable wire services
- Direct regulator/government sources

Give lower credibility to:

- Anonymous blogs
- Low-quality scraped articles
- Social media posts
- Unverified rumour sites
- Promotional penny-stock content

### News scoring model

For each article:

`article_score = relevance_score * credibility_score * recency_weight * sentiment_strength`

Suggested scales:

- Relevance: 0 to 1
- Credibility: 0.25 to 1
- Recency weight: 0 to 1
- Sentiment strength: -1 to +1

Suggested recency decay:

- 0 to 6 hours: 1.0
- 6 to 24 hours: 0.85
- 1 to 3 days: 0.65
- 3 to 7 days: 0.35
- Older than 7 days: 0.15 unless it is a major filing, lawsuit, merger, FDA decision, or earnings event

---

## 9. Technical Analysis Engine

Calculate indicators internally from OHLCV data instead of relying only on provider-generated indicators.

Minimum indicators:

- SMA 20 / 50 / 200
- EMA 12 / 26
- RSI 14
- MACD
- Bollinger Bands
- ATR 14
- Relative volume
- 52-week high/low distance
- Support/resistance zones
- Recent gap up/down

Example technical score:

```text
technical_score = weighted average of:
- price above/below SMA50
- price above/below SMA200
- RSI condition
- MACD trend
- volume confirmation
- ATR-based risk
- distance from support/resistance
```

Do not interpret technical indicators as certainty. Present them as evidence.

---

## 10. Fundamental Analysis Engine

Minimum metrics:

- Revenue growth YoY
- EPS growth YoY
- Gross margin
- Operating margin
- Net margin
- Free cash flow trend
- Debt-to-equity
- Current ratio
- Return on equity
- P/E vs sector
- Forward P/E if available
- Price-to-sales
- Price-to-book
- Share dilution trend

Example fundamental rating labels:

- Strong fundamentals
- Improving fundamentals
- Mixed fundamentals
- Weak fundamentals
- High debt risk
- Unprofitable growth
- Turnaround candidate

---

## 11. Risk Engine

Include:

- Beta
- Average true range
- 30/90/180-day volatility
- Max drawdown
- Earnings date proximity
- Liquidity/volume risk
- Debt risk
- Dilution risk
- News/legal/regulatory risk
- Sector-wide weakness

Example risk labels:

- Low volatility / stable
- Medium volatility
- High volatility
- Event risk ahead
- Thin liquidity
- Earnings risk within 7 days
- Major headline risk

---

## 12. Composite Score Recommendation

The app should not output a blind buy/sell signal. It should output a research classification.

Suggested labels:

- Strong watchlist candidate
- Bullish setup, confirm risk
- Neutral / mixed evidence
- Weak setup
- Avoid for now
- High-risk speculative setup
- Needs more data

Example composite model:

```text
composite_score =
  0.30 * technical_score +
  0.25 * fundamental_score +
  0.20 * news_score +
  0.15 * valuation_score +
  0.10 * momentum_score -
  risk_penalty
```

Where each score is normalized from 0 to 100.

Always show explanation:

```json
{
  "bull_case": ["Revenue growth improving", "Price reclaimed SMA50", "Positive earnings revision"],
  "bear_case": ["Debt-to-equity elevated", "RSI near overbought", "Earnings in 4 days"],
  "risk_notes": ["High volatility", "News sentiment mixed"],
  "data_warnings": ["Quote is delayed", "Analyst target data missing"]
}
```

---

## 13. AI Summary Layer

Use AI only after data collection and scoring.

The AI should summarize:

1. What changed today
2. Why the stock may be moving
3. Important news/filings
4. Bullish evidence
5. Bearish evidence
6. Key risk events
7. What data is missing
8. Suggested research questions

AI must cite the exact stored sources used in the summary.

Do not let AI invent numbers. All numbers must come from the database.

Prompt pattern:

```text
You are a financial research assistant. Use only the provided structured data.
Do not invent values. If data is missing, say it is missing.
Summarize the bullish evidence, bearish evidence, risk factors, and data freshness.
Avoid personalized financial advice. Use research-support language only.
```

---

## 14. Alerts

Suggested alert types:

- Price crosses target
- Price crosses SMA50/SMA200
- RSI overbought/oversold
- Unusual volume
- New SEC filing
- Earnings date within X days
- Major news sentiment shift
- Analyst upgrade/downgrade
- Gap up/down
- Watchlist stock moves more than X percent

---

## 15. API Key and Security Rules

- Use `.env` locally
- Use hosting provider environment variables in production
- Never commit API keys
- Add `.env` to `.gitignore`
- Rate-limit all external API calls
- Cache provider responses
- Store raw API responses for debugging where terms allow
- Create a `/data-health` page showing failed API calls and stale data

Example `.env.example`:

```bash
FMP_API_KEY=
ALPHA_VANTAGE_API_KEY=
FINNHUB_API_KEY=
POLYGON_API_KEY=
MARKETAUX_API_KEY=
TIINGO_API_KEY=
DATABASE_URL=
REDIS_URL=
APP_TIMEZONE=America/Vancouver
```

---

## 16. Development Milestones

### Milestone 1 — MVP

Build:

- Ticker search
- Quote card
- Daily chart
- News list
- Basic technical indicators
- Company profile
- Data freshness labels

Use:

- FMP primary
- Alpha Vantage fallback
- SEC EDGAR for filings

### Milestone 2 — Research Scoring

Build:

- Technical score
- Fundamental score
- News score
- Risk score
- Composite research classification
- Bull/bear explanation cards

### Milestone 3 — Watchlist and Alerts

Build:

- Saved watchlist
- Custom alert rules
- Scheduled refresh jobs
- Email/browser notifications

### Milestone 4 — AI Research Assistant

Build:

- AI summaries based only on stored data
- Source citations
- “What changed since last check?” feature
- “Why is this moving?” feature

### Milestone 5 — Advanced Trading Research

Build:

- Sector comparison
- Peer comparison
- Earnings surprise tracker
- Analyst revision tracker
- Insider transaction tracker
- Options flow only if licensed data is added

---

## 17. Codex Prompt to Start the Build

Use this prompt in Codex:

```text
Build a stock research dashboard, not an automated trading bot. The app should use official/licensed financial APIs only and must not scrape TradingView, Yahoo Finance, Seeking Alpha, Morningstar, or other websites unless terms explicitly allow it.

Use Next.js + TypeScript for the frontend, FastAPI + Python for the backend, PostgreSQL/Supabase for storage, and environment variables for API keys.

Start with Financial Modeling Prep as the primary data provider, Alpha Vantage as a fallback/secondary source, and SEC EDGAR APIs for official filings. Design the code so Finnhub, Polygon/Massive, Tiingo, Intrinio, and Marketaux can be added later as provider modules.

Build these MVP features:
1. Ticker search
2. Current quote card with data freshness and provider label
3. Historical OHLCV chart
4. Internally calculated SMA20, SMA50, SMA200, RSI14, MACD, Bollinger Bands, ATR14
5. Company profile
6. Financial statement summary and key ratios
7. Recent news feed with source, published time, ticker relevance, and sentiment
8. SEC filing list for U.S. companies
9. Research score made from technical, fundamental, news, valuation, momentum, and risk components
10. Bull case, bear case, risk notes, and missing data notes

Create a provider abstraction layer so every API response is normalized into the app's database schema. Cache external API responses. Never expose API keys to the frontend. Add a data-health page showing provider status, failed calls, stale data, and rate-limit issues.

Use research-support language only. Do not output guaranteed predictions or direct personalized financial advice.
```

---

## 18. Initial Folder Structure

```text
stock-research-dashboard/
  frontend/
    app/
      dashboard/
      ticker/[symbol]/
      watchlist/
      alerts/
      news/
      settings/data-sources/
      admin/data-health/
    components/
      QuoteCard.tsx
      PriceChart.tsx
      TechnicalPanel.tsx
      FundamentalPanel.tsx
      NewsPanel.tsx
      FilingPanel.tsx
      ScoreCard.tsx
      RiskPanel.tsx
    lib/
      api.ts
      types.ts
  backend/
    app/
      main.py
      config.py
      database.py
      models/
      schemas/
      providers/
        base.py
        fmp.py
        alpha_vantage.py
        sec_edgar.py
        finnhub.py
        polygon.py
        tiingo.py
        marketaux.py
      services/
        technicals.py
        fundamentals.py
        news_scoring.py
        risk_scoring.py
        composite_scoring.py
        ai_summary.py
      routes/
        symbols.py
        quotes.py
        ohlcv.py
        news.py
        filings.py
        scores.py
        watchlist.py
        data_health.py
      jobs/
        refresh_quotes.py
        refresh_news.py
        refresh_fundamentals.py
  docs/
    data-sources.md
    scoring-model.md
    licensing-notes.md
    api-contracts.md
  .env.example
  README.md
```

---

## 19. Final Recommendation

Build this as a **research dashboard first**, then add more advanced trading features later.

Best starting data stack:

1. FMP for broad market/fundamental/news coverage
2. Alpha Vantage for fallback prices, indicators, sentiment, and economic data
3. SEC EDGAR for official filings
4. Finnhub or Marketaux for added news/sentiment
5. Polygon/Massive only when real-time or intraday precision becomes important enough to justify cost
6. Intrinio only if the project becomes commercial/pro-grade

The first version should prioritize reliability, data freshness, explainability, and source transparency over trying to create a magic prediction engine.

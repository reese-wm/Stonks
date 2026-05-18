# Data Sources

## Primary Sources

- Financial Modeling Prep: quotes, historical prices, company profile, stock news.
- Alpha Vantage: fallback quotes, fallback daily prices, news and sentiment.
- SEC EDGAR: official U.S. company filings.

## Provider Rules

- API keys stay in `.env`.
- Provider calls are made from backend routes only.
- API responses are cached in `data/cache`.
- Tracking snapshots are stored in the configured database, SQLite locally by default.
- The UI must show provider and freshness details.
- Do not scrape TradingView, Yahoo Finance, Seeking Alpha, Morningstar, or similar sites unless terms explicitly allow the target use case.

## Later Provider Modules

The provider layer is intentionally separate so Finnhub, Polygon/Massive, Tiingo, Intrinio, and Marketaux can be added without changing UI contracts.

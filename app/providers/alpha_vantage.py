from datetime import datetime, timezone

from app.config import get_settings
from app.providers.base import CachedHTTPClient, ProviderError
from app.schemas.market import DataFreshness, NewsArticle, OHLCV, Quote


class AlphaVantageProvider:
    name = "Alpha Vantage"
    base_url = "https://www.alphavantage.co/query"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = CachedHTTPClient("alpha_vantage")

    def _require_key(self) -> str:
        if not self.settings.alpha_vantage_api_key:
            raise ProviderError(self.name, "ALPHA_VANTAGE_API_KEY is not configured")
        return self.settings.alpha_vantage_api_key

    async def quote(self, symbol: str) -> Quote:
        data = await self.client.get_json(
            self.base_url,
            params={"function": "GLOBAL_QUOTE", "symbol": symbol.upper(), "apikey": self._require_key()},
        )
        item = data.get("Global Quote") or {}
        if not item:
            raise ProviderError(self.name, f"No quote returned for {symbol}")
        fetched_at = datetime.now(timezone.utc)
        return Quote(
            symbol=symbol.upper(),
            price=_float(item.get("05. price")),
            change=_float(item.get("09. change")),
            change_percent=_percent(item.get("10. change percent")),
            volume=_int(item.get("06. volume")),
            freshness=DataFreshness(
                provider=self.name,
                fetched_at=fetched_at,
                source_timestamp=item.get("07. latest trading day"),
                quote_type="delayed_or_eod",
                display_note="Alpha Vantage global quote. Check plan and exchange delay terms.",
            ),
        )

    async def daily_prices(self, symbol: str, limit: int = 260) -> list[OHLCV]:
        data = await self.client.get_json(
            self.base_url,
            params={"function": "TIME_SERIES_DAILY_ADJUSTED", "symbol": symbol.upper(), "outputsize": "compact", "apikey": self._require_key()},
            ttl_seconds=3600,
        )
        series = data.get("Time Series (Daily)") or {}
        prices: list[OHLCV] = []
        for day, row in list(series.items())[:limit]:
            prices.append(
                OHLCV(
                    date=day,
                    open=float(row["1. open"]),
                    high=float(row["2. high"]),
                    low=float(row["3. low"]),
                    close=float(row["4. close"]),
                    adjusted_close=float(row.get("5. adjusted close") or row["4. close"]),
                    volume=int(row["6. volume"]),
                    provider=self.name,
                )
            )
        return sorted(prices, key=lambda item: item.date)

    async def news(self, symbol: str, limit: int = 12) -> list[NewsArticle]:
        data = await self.client.get_json(
            self.base_url,
            params={"function": "NEWS_SENTIMENT", "tickers": symbol.upper(), "limit": limit, "apikey": self._require_key()},
            ttl_seconds=900,
        )
        articles: list[NewsArticle] = []
        for row in data.get("feed", [])[:limit]:
            articles.append(
                NewsArticle(
                    headline=row.get("title") or "Untitled article",
                    source_name=row.get("source") or "Unknown",
                    url=row.get("url") or "",
                    published_at=_parse_av_time(row.get("time_published")),
                    summary=row.get("summary"),
                    provider=self.name,
                    sentiment_score=_float(row.get("overall_sentiment_score")) or 0,
                    relevance_score=0.8,
                    credibility_score=0.65,
                )
            )
        return articles


def _float(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def _int(value: str | None) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except ValueError:
        return None


def _percent(value: str | None) -> float | None:
    if value is None:
        return None
    return _float(value.replace("%", ""))


def _parse_av_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)

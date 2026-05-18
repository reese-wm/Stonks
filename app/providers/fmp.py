from datetime import datetime, timezone

from app.config import get_settings
from app.providers.base import CachedHTTPClient, ProviderError
from app.schemas.market import CompanyProfile, DataFreshness, MiniChartPoint, NewsArticle, OHLCV, Quote, UnderDollarStock


class FMPProvider:
    name = "FMP"
    base_url = "https://financialmodelingprep.com/stable"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = CachedHTTPClient(self.name.lower())

    def _require_key(self) -> str:
        if not self.settings.fmp_api_key:
            raise ProviderError(self.name, "FMP_API_KEY is not configured")
        return self.settings.fmp_api_key

    async def quote(self, symbol: str) -> Quote:
        data = await self.client.get_json(
            f"{self.base_url}/quote",
            params={"symbol": symbol.upper(), "apikey": self._require_key()},
        )
        if not data:
            raise ProviderError(self.name, f"No quote returned for {symbol}")
        item = data[0]
        fetched_at = datetime.now(timezone.utc)
        return Quote(
            symbol=symbol.upper(),
            price=item.get("price"),
            change=item.get("change"),
            change_percent=item.get("changesPercentage"),
            volume=item.get("volume"),
            market_cap=item.get("marketCap"),
            freshness=DataFreshness(
                provider=self.name,
                fetched_at=fetched_at,
                source_timestamp=fetched_at,
                quote_type="delayed_or_eod",
                display_note="FMP quote. Confirm plan terms for real-time, delayed, or EOD display rights.",
            ),
        )

    async def daily_prices(self, symbol: str, limit: int = 260) -> list[OHLCV]:
        data = await self.client.get_json(
            f"{self.base_url}/historical-price-eod/full",
            params={"symbol": symbol.upper(), "apikey": self._require_key()},
            ttl_seconds=3600,
        )
        rows = data if isinstance(data, list) else data.get("historical", [])
        prices: list[OHLCV] = []
        for row in rows[:limit]:
            prices.append(
                OHLCV(
                    date=row["date"],
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    adjusted_close=row.get("adjClose"),
                    volume=row.get("volume", 0),
                    provider=self.name,
                )
            )
        return sorted(prices, key=lambda item: item.date)

    async def profile(self, symbol: str) -> CompanyProfile:
        data = await self.client.get_json(
            f"{self.base_url}/profile",
            params={"symbol": symbol.upper(), "apikey": self._require_key()},
            ttl_seconds=86400,
        )
        if not data:
            raise ProviderError(self.name, f"No company profile returned for {symbol}")
        item = data[0]
        return CompanyProfile(
            symbol=symbol.upper(),
            name=item.get("companyName"),
            exchange=item.get("exchangeShortName"),
            country=item.get("country"),
            currency=item.get("currency"),
            sector=item.get("sector"),
            industry=item.get("industry"),
            website=item.get("website"),
            description=item.get("description"),
            provider=self.name,
            fetched_at=datetime.now(timezone.utc),
        )

    async def news(self, symbol: str, limit: int = 12) -> list[NewsArticle]:
        data = await self.client.get_json(
            f"{self.base_url}/news/stock",
            params={"symbols": symbol.upper(), "limit": limit, "apikey": self._require_key()},
            ttl_seconds=900,
        )
        articles: list[NewsArticle] = []
        for row in data[:limit]:
            articles.append(
                NewsArticle(
                    headline=row.get("title") or "Untitled article",
                    source_name=row.get("site") or "Unknown",
                    url=row.get("url") or "",
                    published_at=row.get("publishedDate"),
                    summary=row.get("text"),
                    provider=self.name,
                    relevance_score=0.8,
                    credibility_score=0.65,
                )
            )
        return articles

    async def under_dollar_leaders(self, limit: int = 10) -> list[UnderDollarStock]:
        data = await self.client.get_json(
            f"{self.base_url}/company-screener",
            params={
                "priceLowerThan": 1,
                "priceMoreThan": 0.01,
                "volumeMoreThan": 100000,
                "isActivelyTrading": "true",
                "limit": 100,
                "apikey": self._require_key(),
            },
            ttl_seconds=300,
        )
        rows = data if isinstance(data, list) else []
        sorted_rows = sorted(rows, key=lambda row: _safe_float(row.get("changesPercentage") or row.get("changePercentage")), reverse=True)
        leaders: list[UnderDollarStock] = []
        fetched_at = datetime.now(timezone.utc)
        for row in sorted_rows[:limit]:
            leaders.append(
                UnderDollarStock(
                    symbol=(row.get("symbol") or "").upper(),
                    name=row.get("companyName") or row.get("companyName") or row.get("name"),
                    exchange=row.get("exchangeShortName") or row.get("exchange"),
                    price=_nullable_float(row.get("price")),
                    change=_nullable_float(row.get("change")),
                    change_percent=_nullable_float(row.get("changesPercentage") or row.get("changePercentage")),
                    volume=_nullable_int(row.get("volume")),
                    market_cap=_nullable_float(row.get("marketCap")),
                    provider=self.name,
                    fetched_at=fetched_at,
                )
            )
        return [leader for leader in leaders if leader.symbol]

    async def add_sparklines(self, leaders: list[UnderDollarStock], days: int = 20) -> list[UnderDollarStock]:
        for leader in leaders:
            try:
                prices = await self.daily_prices(leader.symbol, limit=days)
                leader.sparkline = [MiniChartPoint(date=item.date, close=item.close) for item in prices[-days:]]
            except ProviderError:
                leader.sparkline = []
        return leaders


def _safe_float(value) -> float:
    parsed = _nullable_float(value)
    return parsed if parsed is not None else -999999.0


def _nullable_float(value) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _nullable_int(value) -> int | None:
    try:
        return int(float(value)) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None

from datetime import date, datetime, timedelta, timezone

from app.config import get_settings
from app.providers.base import CachedHTTPClient, ProviderError
from app.schemas.market import (
    ChartBar,
    DataFreshness,
    MassiveIndicatorPoint,
    MassiveMarketInsight,
    MassiveShortVolume,
    MiniChartPoint,
    NewsArticle,
    OHLCV,
    Quote,
    TickerDirectoryItem,
    UnderDollarStock,
)


class MassiveProvider:
    name = "Massive"
    base_url = "https://api.massive.com"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = CachedHTTPClient("massive")

    def _require_key(self) -> str:
        if not self.settings.massive_api_key:
            raise ProviderError(self.name, "MASSIVE_API_KEY is not configured")
        return self.settings.massive_api_key

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._require_key()}"}

    async def quote(self, symbol: str) -> Quote:
        try:
            return await self._snapshot_quote(symbol)
        except ProviderError as snapshot_error:
            if "403" not in snapshot_error.message and "NOT_AUTHORIZED" not in snapshot_error.message:
                raise
            return await self._daily_bar_quote(symbol, snapshot_error.message)

    async def _snapshot_quote(self, symbol: str) -> Quote:
        data = await self.client.get_json(
            f"{self.base_url}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol.upper()}",
            headers=self._auth_headers(),
            ttl_seconds=30,
        )
        ticker = data.get("ticker") or data.get("results") or {}
        if not ticker:
            raise ProviderError(self.name, f"No snapshot returned for {symbol}")
        day = ticker.get("day") or {}
        prev_day = ticker.get("prevDay") or {}
        last_trade = ticker.get("lastTrade") or {}
        price = _nullable_float(day.get("c") or last_trade.get("p"))
        prev_close = _nullable_float(prev_day.get("c"))
        change = (price - prev_close) if price is not None and prev_close else _nullable_float(ticker.get("todaysChange"))
        change_percent = _nullable_float(ticker.get("todaysChangePerc"))
        fetched_at = datetime.now(timezone.utc)
        source_ts = _ns_to_datetime(last_trade.get("t")) or fetched_at
        return Quote(
            symbol=symbol.upper(),
            price=price,
            change=change,
            change_percent=change_percent,
            volume=_nullable_int(day.get("v") or ticker.get("dayVolume")),
            market_cap=None,
            freshness=DataFreshness(
                provider=self.name,
                fetched_at=fetched_at,
                source_timestamp=source_ts,
                quote_type="snapshot",
                display_note="Massive stock snapshot. Confirm plan terms for real-time, delayed, or EOD display rights.",
            ),
        )

    async def _daily_bar_quote(self, symbol: str, reason: str) -> Quote:
        prices = await self.daily_prices(symbol, limit=2)
        if not prices:
            raise ProviderError(self.name, reason)
        latest = prices[-1]
        previous = prices[-2] if len(prices) > 1 else None
        change = (latest.close - previous.close) if previous else None
        change_percent = (change / previous.close * 100) if previous and previous.close else None
        fetched_at = datetime.now(timezone.utc)
        return Quote(
            symbol=symbol.upper(),
            price=latest.close,
            change=change,
            change_percent=change_percent,
            volume=latest.volume,
            market_cap=None,
            freshness=DataFreshness(
                provider=self.name,
                fetched_at=fetched_at,
                source_timestamp=latest.date,
                quote_type="eod_fallback",
                display_note="Massive snapshot is not entitled on this plan, so quote uses the latest available daily OHLC close.",
            ),
        )

    async def daily_prices(self, symbol: str, limit: int = 260) -> list[OHLCV]:
        to_date = date.today()
        from_date = to_date - timedelta(days=max(400, limit * 2))
        data = await self.client.get_json(
            f"{self.base_url}/v2/aggs/ticker/{symbol.upper()}/range/1/day/{from_date}/{to_date}",
            params={"adjusted": "true", "sort": "desc", "limit": limit},
            headers=self._auth_headers(),
            ttl_seconds=900,
        )
        rows = data.get("results") or []
        prices: list[OHLCV] = []
        for row in rows[:limit]:
            prices.append(
                OHLCV(
                    date=datetime.fromtimestamp(row["t"] / 1000, tz=timezone.utc).date(),
                    open=row["o"],
                    high=row["h"],
                    low=row["l"],
                    close=row["c"],
                    adjusted_close=row.get("c"),
                    volume=int(row.get("v") or 0),
                    provider=self.name,
                )
            )
        return sorted(prices, key=lambda item: item.date)

    async def custom_bars(self, symbol: str, range_key: str = "1D") -> list[ChartBar]:
        config = _range_config(range_key)
        to_date = date.today()
        from_date = to_date - timedelta(days=config["days"])
        data = await self.client.get_json(
            f"{self.base_url}/v2/aggs/ticker/{symbol.upper()}/range/{config['multiplier']}/{config['timespan']}/{from_date}/{to_date}",
            params={"adjusted": "true", "sort": "asc", "limit": 50000},
            headers=self._auth_headers(),
            ttl_seconds=config["ttl"],
        )
        rows = data.get("results") or []
        return [
            ChartBar(
                timestamp=datetime.fromtimestamp(row["t"] / 1000, tz=timezone.utc),
                label=datetime.fromtimestamp(row["t"] / 1000, tz=timezone.utc).isoformat(),
                open=float(row["o"]),
                high=float(row["h"]),
                low=float(row["l"]),
                close=float(row["c"]),
                volume=int(row.get("v") or 0),
                provider=self.name,
                timespan=f"{config['multiplier']} {config['timespan']}",
            )
            for row in rows
        ]

    async def ticker_search(self, query: str = "", limit: int = 25) -> list[TickerDirectoryItem]:
        data = await self.client.get_json(
            f"{self.base_url}/v3/reference/tickers",
            params={"market": "stocks", "active": "true", "search": query, "limit": min(max(limit, 1), 1000), "sort": "ticker"},
            headers=self._auth_headers(),
            ttl_seconds=86400,
        )
        return [
            TickerDirectoryItem(
                symbol=(row.get("ticker") or "").upper(),
                name=row.get("name"),
                market=row.get("market"),
                exchange=row.get("primary_exchange"),
                type=row.get("type"),
                currency=row.get("currency_name") or row.get("currency_symbol"),
                active=row.get("active"),
            )
            for row in data.get("results", [])
            if row.get("ticker")
        ]

    async def news(self, symbol: str, limit: int = 12) -> list[NewsArticle]:
        data = await self.client.get_json(
            f"{self.base_url}/v2/reference/news",
            params={"ticker": symbol.upper(), "order": "desc", "sort": "published_utc", "limit": limit},
            headers=self._auth_headers(),
            ttl_seconds=900,
        )
        articles: list[NewsArticle] = []
        for row in data.get("results", [])[:limit]:
            publisher = row.get("publisher") or {}
            sentiment = _massive_sentiment(row, symbol)
            articles.append(
                NewsArticle(
                    headline=row.get("title") or "Untitled Massive news item",
                    source_name=publisher.get("name") or "Massive News",
                    url=row.get("article_url") or row.get("amp_url") or "",
                    published_at=row.get("published_utc"),
                    summary=row.get("description"),
                    provider=self.name,
                    sentiment_score=sentiment,
                    relevance_score=0.85,
                    credibility_score=0.75,
                )
            )
        return articles

    async def ema(self, symbol: str, window: int = 12, timespan: str = "day") -> MassiveIndicatorPoint:
        data = await self.client.get_json(
            f"{self.base_url}/v1/indicators/ema/{symbol.upper()}",
            params={"timespan": timespan, "adjusted": "true", "window": window, "series_type": "close", "order": "desc", "limit": 1},
            headers=self._auth_headers(),
            ttl_seconds=900,
        )
        values = (data.get("results") or {}).get("values") or []
        if not values:
            raise ProviderError(self.name, f"No Massive EMA{window} returned for {symbol}")
        row = values[0]
        timestamp = _timestamp_to_datetime(row.get("timestamp"))
        return MassiveIndicatorPoint(timestamp=timestamp, value=_nullable_float(row.get("value")))

    async def short_volume(self, symbol: str) -> MassiveShortVolume:
        data = await self.client.get_json(
            f"{self.base_url}/stocks/v1/short-volume",
            params={"ticker": symbol.upper(), "limit": 1, "sort": "date.desc"},
            headers=self._auth_headers(),
            ttl_seconds=3600,
        )
        rows = data.get("results") or []
        if not rows:
            raise ProviderError(self.name, f"No Massive short-volume data returned for {symbol}")
        row = rows[0]
        return MassiveShortVolume(
            trade_date=row.get("date"),
            short_volume=_nullable_int(row.get("short_volume")),
            total_volume=_nullable_int(row.get("total_volume")),
            short_volume_ratio=_nullable_float(row.get("short_volume_ratio")),
            exempt_volume=_nullable_float(row.get("exempt_volume")),
        )

    async def market_insight(self, symbol: str) -> MassiveMarketInsight:
        warnings: list[str] = []
        ema_12 = None
        ema_26 = None
        short_volume = None
        for window in (12, 26):
            try:
                if window == 12:
                    ema_12 = await self.ema(symbol, window=window)
                else:
                    ema_26 = await self.ema(symbol, window=window)
            except ProviderError as error:
                warnings.append(error.message)
        try:
            short_volume = await self.short_volume(symbol)
        except ProviderError as error:
            warnings.append(error.message)
        if ema_12 is None and ema_26 is None and short_volume is None:
            raise ProviderError(self.name, "; ".join(warnings) or f"No Massive insight data returned for {symbol}")
        return MassiveMarketInsight(
            symbol=symbol.upper(),
            fetched_at=datetime.now(timezone.utc),
            ema_12=ema_12,
            ema_26=ema_26,
            short_volume=short_volume,
            warnings=warnings,
        )

    async def under_dollar_leaders(self, limit: int = 10) -> list[UnderDollarStock]:
        try:
            return await self._snapshot_under_dollar_leaders(limit)
        except ProviderError as snapshot_error:
            if "403" not in snapshot_error.message and "NOT_AUTHORIZED" not in snapshot_error.message:
                raise
            return await self._grouped_daily_under_dollar_leaders(limit)

    async def _snapshot_under_dollar_leaders(self, limit: int = 10) -> list[UnderDollarStock]:
        data = await self.client.get_json(
            f"{self.base_url}/v2/snapshot/locale/us/markets/stocks/tickers",
            headers=self._auth_headers(),
            ttl_seconds=60,
        )
        tickers = data.get("tickers") or data.get("results") or []
        fetched_at = datetime.now(timezone.utc)
        leaders: list[UnderDollarStock] = []
        for item in tickers:
            day = item.get("day") or {}
            prev_day = item.get("prevDay") or {}
            last_trade = item.get("lastTrade") or {}
            price = _nullable_float(day.get("c") or last_trade.get("p"))
            volume = _nullable_int(day.get("v"))
            if price is None or price >= 1 or price <= 0.01 or (volume or 0) < 10_000:
                continue
            change_percent = _nullable_float(item.get("todaysChangePerc"))
            change = _nullable_float(item.get("todaysChange"))
            if change is None and prev_day.get("c"):
                change = price - float(prev_day["c"])
            leaders.append(
                UnderDollarStock(
                    symbol=(item.get("ticker") or "").upper(),
                    name=item.get("name"),
                    exchange=None,
                    price=price,
                    change=change,
                    change_percent=change_percent,
                    volume=volume,
                    market_cap=None,
                    provider=self.name,
                    fetched_at=fetched_at,
                )
            )
        leaders = [leader for leader in leaders if leader.symbol]
        return sorted(leaders, key=lambda leader: leader.change_percent if leader.change_percent is not None else -999999, reverse=True)[:limit]

    async def _grouped_daily_under_dollar_leaders(self, limit: int = 10) -> list[UnderDollarStock]:
        latest_date, latest_rows = await self._latest_grouped_daily()
        previous_date, previous_rows = await self._previous_grouped_daily(latest_date)
        previous_close = {row.get("T"): _nullable_float(row.get("c")) for row in previous_rows if row.get("T")}
        fetched_at = datetime.now(timezone.utc)
        leaders: list[UnderDollarStock] = []

        for row in latest_rows:
            symbol = (row.get("T") or "").upper()
            close = _nullable_float(row.get("c"))
            open_price = _nullable_float(row.get("o"))
            volume = _nullable_int(row.get("v"))
            if _looks_like_derivative(symbol) or close is None or close >= 1 or close <= 0.01 or (volume or 0) < 10_000:
                continue
            base = previous_close.get(symbol) or open_price
            change = (close - base) if base else None
            change_percent = (change / base * 100) if change is not None and base else None
            leaders.append(
                UnderDollarStock(
                    symbol=symbol,
                    name=None,
                    exchange=None,
                    price=close,
                    change=change,
                    change_percent=change_percent,
                    volume=volume,
                    market_cap=None,
                    provider=self.name,
                    fetched_at=fetched_at,
                )
            )

        return sorted(leaders, key=lambda leader: leader.change_percent if leader.change_percent is not None else -999999, reverse=True)[:limit]

    async def _latest_grouped_daily(self) -> tuple[date, list[dict]]:
        for days_back in range(0, 14):
            target = date.today() - timedelta(days=days_back)
            try:
                rows = await self._grouped_daily(target)
            except ProviderError as error:
                if "before end of day" in error.message or "today's data" in error.message:
                    continue
                raise
            if rows:
                return target, rows
        raise ProviderError(self.name, "No grouped daily market data returned for the last 14 calendar days")

    async def _previous_grouped_daily(self, latest_date: date) -> tuple[date, list[dict]]:
        for days_back in range(1, 14):
            target = latest_date - timedelta(days=days_back)
            try:
                rows = await self._grouped_daily(target)
            except ProviderError as error:
                if "before end of day" in error.message or "today's data" in error.message:
                    continue
                raise
            if rows:
                return target, rows
        return latest_date, []

    async def _grouped_daily(self, target: date) -> list[dict]:
        data = await self.client.get_json(
            f"{self.base_url}/v2/aggs/grouped/locale/us/market/stocks/{target.isoformat()}",
            params={"adjusted": "true"},
            headers=self._auth_headers(),
            ttl_seconds=3600,
        )
        return data.get("results") or []

    async def add_sparklines(self, leaders: list[UnderDollarStock], days: int = 20) -> list[UnderDollarStock]:
        for leader in leaders:
            try:
                prices = await self.daily_prices(leader.symbol, limit=days)
                leader.sparkline = [MiniChartPoint(date=item.date, close=item.close, volume=item.volume) for item in prices[-days:]]
            except ProviderError:
                leader.sparkline = []
        return leaders


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


def _timestamp_to_datetime(value) -> datetime | date | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                return date.fromisoformat(value)
            except ValueError:
                return None
    try:
        number = int(value)
        if number > 10_000_000_000:
            number = number / 1000
        return datetime.fromtimestamp(number, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _ns_to_datetime(value) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1_000_000_000, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _looks_like_derivative(symbol: str) -> bool:
    if not symbol:
        return True
    suffixes = ("W", "WS", "WT", "U", "R")
    return any(symbol.endswith(suffix) for suffix in suffixes)


def _range_config(range_key: str) -> dict[str, int | str]:
    clean = range_key.upper()
    if clean == "1D":
        return {"days": 2, "multiplier": 15, "timespan": "minute", "ttl": 60}
    if clean == "5D":
        return {"days": 8, "multiplier": 30, "timespan": "minute", "ttl": 120}
    if clean == "1M":
        return {"days": 35, "multiplier": 1, "timespan": "day", "ttl": 900}
    if clean == "3M":
        return {"days": 100, "multiplier": 1, "timespan": "day", "ttl": 900}
    if clean == "6M":
        return {"days": 190, "multiplier": 1, "timespan": "day", "ttl": 900}
    if clean == "YTD":
        return {"days": max(1, (date.today() - date(date.today().year, 1, 1)).days + 1), "multiplier": 1, "timespan": "day", "ttl": 900}
    if clean == "1Y":
        return {"days": 370, "multiplier": 1, "timespan": "day", "ttl": 900}
    return {"days": 900, "multiplier": 1, "timespan": "day", "ttl": 900}


def _massive_sentiment(row: dict, symbol: str) -> float:
    for insight in row.get("insights") or []:
        if (insight.get("ticker") or "").upper() == symbol.upper():
            sentiment = str(insight.get("sentiment") or "").lower()
            if sentiment == "positive":
                return 0.7
            if sentiment == "negative":
                return -0.7
            return 0.0
    return 0.0

from datetime import date, datetime, timedelta, timezone

from app.config import get_settings
from app.providers.base import CachedHTTPClient, ProviderError
from app.schemas.market import DataFreshness, MiniChartPoint, OHLCV, Quote, UnderDollarStock


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

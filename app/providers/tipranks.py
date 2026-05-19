from datetime import datetime, timezone
from statistics import median

from app.config import get_settings
from app.providers.base import CachedHTTPClient, ProviderError
from app.schemas.market import TipRanksInsight, TipRanksNewsSentiment, TipRanksPriceTargets


class TipRanksProvider:
    name = "TipRanks"
    base_url = "https://www.tipranks.com/api/stocks"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = CachedHTTPClient("tipranks")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": self.settings.tipranks_user_agent,
        }
        if self.settings.tipranks_cookie:
            headers["Cookie"] = self.settings.tipranks_cookie
        return headers

    async def insight(self, symbol: str) -> TipRanksInsight:
        if not self.settings.tipranks_enabled:
            raise ProviderError(self.name, "TIPRANKS_ENABLED is false")

        clean_symbol = symbol.upper().strip()
        warnings: list[str] = []
        price_targets = None
        news_sentiment = None

        try:
            price_targets = await self.price_targets(clean_symbol)
        except ProviderError as error:
            warnings.append(f"Price targets unavailable: {error.message}")

        try:
            news_sentiment = await self.news_sentiment(clean_symbol)
        except ProviderError as error:
            warnings.append(f"News sentiment unavailable: {error.message}")

        if price_targets is None and news_sentiment is None:
            raise ProviderError(self.name, "; ".join(warnings) or f"No TipRanks data returned for {clean_symbol}")

        return TipRanksInsight(
            symbol=clean_symbol,
            fetched_at=datetime.now(timezone.utc),
            price_targets=price_targets,
            news_sentiment=news_sentiment,
            warnings=warnings,
        )

    async def price_targets(self, symbol: str) -> TipRanksPriceTargets:
        payload = await self.client.get_json(
            f"{self.base_url}/getData/",
            params={"name": symbol.lower(), "benchmark": 1, "period": 3, "break": int(datetime.now(timezone.utc).timestamp())},
            headers=self._headers(),
            ttl_seconds=3600,
        )
        experts = payload.get("experts") or []
        estimates: list[float] = []
        for expert in experts:
            ratings = expert.get("ratings") or []
            if not ratings:
                continue
            target = _nullable_float(ratings[0].get("priceTarget"))
            if target is not None:
                estimates.append(target)

        if not estimates:
            raise ProviderError(self.name, f"No recent analyst price targets returned for {symbol}")

        return TipRanksPriceTargets(
            mean=sum(estimates) / len(estimates),
            median=median(estimates),
            highest=max(estimates),
            lowest=min(estimates),
            number_of_estimates=len(estimates),
        )

    async def news_sentiment(self, symbol: str) -> TipRanksNewsSentiment:
        payload = await self.client.get_json(
            f"{self.base_url}/getNewsSentiments/",
            params={"ticker": symbol.lower(), "break": int(datetime.now(timezone.utc).timestamp())},
            headers=self._headers(),
            ttl_seconds=1800,
        )
        sentiment = payload.get("sentiment") or {}
        buzz = payload.get("buzz") or {}
        if not sentiment and not buzz and payload.get("score") is None:
            raise ProviderError(self.name, f"No news sentiment returned for {symbol}")

        return TipRanksNewsSentiment(
            bullish_percent=_nullable_float(sentiment.get("bullishPercent")),
            bearish_percent=_nullable_float(sentiment.get("bearishPercent")),
            articles_in_last_week=_nullable_int(buzz.get("articlesInLastWeek")),
            weekly_average=_nullable_float(buzz.get("weeklyAverage")),
            buzz=_nullable_float(buzz.get("buzz")),
            sector_average_bullish_percent=_nullable_float(payload.get("sectorAverageBullishPercent")),
            sector_average_news_score=_nullable_float(payload.get("sectorAverageNewsScore")),
            company_news_score=_nullable_float(payload.get("score")),
        )


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

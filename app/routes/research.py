import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.providers.alpha_vantage import AlphaVantageProvider
from app.providers.base import ProviderError
from app.providers.fmp import FMPProvider
from app.providers.massive import MassiveProvider
from app.providers.sec_edgar import SECEdgarProvider
from app.providers.tipranks import TipRanksProvider
from app.schemas.market import (
    AIResearchBrief,
    AIStockStance,
    ChartBar,
    MassiveMarketInsight,
    ProjectionScenario,
    QuantIntelligenceReport,
    TickerDirectoryItem,
    TickerResearch,
    TopProjectedBuy,
    UnderDollarDashboard,
)
from app.services.ai_stance import build_ai_stock_stance
from app.services.ai_summary import build_ai_research_brief
from app.services.news_scoring import score_articles
from app.services.quant_intelligence import build_quant_intelligence_report
from app.services.scoring import build_research_score
from app.services.scenario_projection import build_projection_scenario
from app.services.scheduler import scheduler_status
from app.services.technicals import calculate_indicators
from app.services.tracking import (
    data_health_summary,
    latest_under_dollar_dashboard,
    projection_history,
    quote_history,
    save_quote_snapshot,
    under_dollar_history,
)
from app.services.under_dollar import build_and_store_under_dollar_dashboard

router = APIRouter(prefix="/api", tags=["research"])


@router.get("/ticker/{symbol}", response_model=TickerResearch)
async def ticker_research(symbol: str, db: Session = Depends(get_db)) -> TickerResearch:
    symbol = symbol.upper().strip()
    provider_status: dict[str, str] = {}
    warnings: list[str] = []

    fmp = FMPProvider()
    massive = MassiveProvider()
    alpha = AlphaVantageProvider()
    sec = SECEdgarProvider()
    tipranks = TipRanksProvider()

    quote = await _first_success("quote", symbol, provider_status, massive, fmp, alpha)
    save_quote_snapshot(db, quote)
    historical = await _first_success("daily_prices", symbol, provider_status, massive, fmp, alpha) or []
    profile = await _optional_call(fmp.profile(symbol), provider_status, "FMP profile")

    news_results = await asyncio.gather(
        _optional_call(massive.news(symbol), provider_status, "Massive news"),
        _optional_call(fmp.news(symbol), provider_status, "FMP news"),
        _optional_call(alpha.news(symbol), provider_status, "Alpha Vantage news"),
    )
    news = score_articles([article for result in news_results if result for article in result])
    filings = await _optional_call(sec.company_filings(symbol), provider_status, "SEC filings") or []
    tipranks_insight = await _optional_call(tipranks.insight(symbol), provider_status, "TipRanks insights")
    massive_insight = await _optional_call(massive.market_insight(symbol), provider_status, "Massive EMA/short-volume")

    if quote is None:
        warnings.append("Quote is unavailable. Add MASSIVE_API_KEY, FMP_API_KEY, or ALPHA_VANTAGE_API_KEY in .env.")
    if not historical:
        warnings.append("Historical OHLCV data is unavailable, so technical indicators are incomplete.")

    indicators = calculate_indicators(historical)
    score = build_research_score(quote, indicators, news, tipranks=tipranks_insight, data_warnings=warnings)

    return TickerResearch(
        symbol=symbol,
        quote=quote,
        profile=profile,
        historical=historical,
        indicators=indicators,
        news=news,
        filings=filings,
        tipranks=tipranks_insight,
        massive_insight=massive_insight,
        score=score,
        provider_status=provider_status,
    )


@router.get("/ticker/{symbol}/ai-summary", response_model=AIResearchBrief)
async def ticker_ai_summary(symbol: str, db: Session = Depends(get_db)) -> AIResearchBrief:
    research = await ticker_research(symbol, db)
    return await build_ai_research_brief(research)


@router.get("/ticker/{symbol}/ai-stance", response_model=AIStockStance)
async def ticker_ai_stance(symbol: str, db: Session = Depends(get_db)) -> AIStockStance:
    research = await ticker_research(symbol, db)
    return await build_ai_stock_stance(research)


@router.get("/ticker/{symbol}/quant-intelligence", response_model=QuantIntelligenceReport)
async def ticker_quant_intelligence(symbol: str, db: Session = Depends(get_db)) -> QuantIntelligenceReport:
    research = await ticker_research(symbol, db)
    return await build_quant_intelligence_report(research)


@router.get("/ticker/{symbol}/projection-scenario", response_model=ProjectionScenario)
async def ticker_projection_scenario(
    symbol: str,
    amount: float = 100,
    mode: str = "daily",
    periods: int = 1,
    db: Session = Depends(get_db),
) -> ProjectionScenario:
    research = await ticker_research(symbol, db)
    return build_projection_scenario(research, amount=amount, mode=mode, periods=periods)


@router.get("/ticker/{symbol}/bars", response_model=list[ChartBar])
async def ticker_chart_bars(symbol: str, range: str = "1D") -> list[ChartBar]:
    massive = MassiveProvider()
    try:
        bars = await massive.custom_bars(symbol, range_key=range)
        if bars:
            return bars
    except ProviderError as error:
        pass
    try:
        fallback = await massive.daily_prices(symbol, limit=370)
    except ProviderError:
        return []
    return [
        ChartBar(
            timestamp=datetime.combine(row.date, datetime.min.time()),
            label=row.date.isoformat(),
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume,
            provider=f"{row.provider} daily fallback",
            timespan="1 day",
        )
        for row in fallback
    ]


@router.get("/ticker/{symbol}/massive-insight", response_model=MassiveMarketInsight)
async def ticker_massive_insight(symbol: str) -> MassiveMarketInsight:
    return await MassiveProvider().market_insight(symbol)


@router.get("/tickers/search", response_model=list[TickerDirectoryItem])
async def ticker_directory_search(q: str = "", limit: int = 25) -> list[TickerDirectoryItem]:
    return await MassiveProvider().ticker_search(q, limit=limit)


@router.get("/data-health")
async def data_health(db: Session = Depends(get_db)) -> dict[str, object]:
    providers = {
        "Massive": "configured" if FMPProvider().settings.massive_api_key else "missing MASSIVE_API_KEY",
        "FMP": "configured" if FMPProvider().settings.fmp_api_key else "missing FMP_API_KEY",
        "Alpha Vantage": "configured" if AlphaVantageProvider().settings.alpha_vantage_api_key else "missing ALPHA_VANTAGE_API_KEY",
        "Finnhub": "configured" if FMPProvider().settings.finnhub_api_key else "missing FINNHUB_API_KEY",
        "NewsAPI": "configured" if FMPProvider().settings.news_api_key else "missing NEWS_API_KEY",
        "OpenAI": "configured" if FMPProvider().settings.openai_api_key else "missing OPENAI_API_KEY",
        "TipRanks": "enabled" if FMPProvider().settings.tipranks_enabled else "disabled; set TIPRANKS_ENABLED=true if your use is permitted",
        "SEC EDGAR": "configured",
    }
    return {
        "providers": providers,
        "cache": "file cache in data/cache",
        "database": data_health_summary(db),
        "scheduler": scheduler_status(),
        "policy": "Official/licensed APIs preferred. Optional TipRanks integration uses public web JSON endpoints and should only be enabled when your use is permitted by TipRanks terms.",
    }


@router.get("/under-dollar-leaders", response_model=UnderDollarDashboard)
async def under_dollar_leaders(db: Session = Depends(get_db)) -> UnderDollarDashboard:
    return await build_and_store_under_dollar_dashboard(db, persist=True)


@router.get("/under-dollar-leaders/latest", response_model=UnderDollarDashboard | None)
async def latest_under_dollar_leaders(db: Session = Depends(get_db)) -> UnderDollarDashboard | None:
    return latest_under_dollar_dashboard(db)


@router.post("/under-dollar-leaders/refresh")
async def refresh_under_dollar_leaders(db: Session = Depends(get_db)) -> UnderDollarDashboard:
    return await build_and_store_under_dollar_dashboard(db, persist=True)


@router.get("/under-dollar-top-buy", response_model=TopProjectedBuy)
async def under_dollar_top_buy(db: Session = Depends(get_db)) -> TopProjectedBuy:
    dashboard = await build_and_store_under_dollar_dashboard(db, persist=True)
    if dashboard.top_projected_buy is None:
        return TopProjectedBuy(
            generated_at=dashboard.generated_at,
            universe_count=len(dashboard.leaders),
            selected=None,
            candidates=[],
            ai_provider=None,
            ai_summary=None,
            methodology="No under-$1 candidates were available to rank.",
            warnings=dashboard.warnings,
        )
    return dashboard.top_projected_buy


@router.get("/tracking/under-dollar-history")
async def under_dollar_snapshots(limit: int = 24, db: Session = Depends(get_db)) -> list[dict]:
    return under_dollar_history(db, limit=min(max(limit, 1), 250))


@router.get("/tracking/projections")
async def projection_snapshots(symbol: str | None = None, limit: int = 50, db: Session = Depends(get_db)) -> list[dict]:
    return projection_history(db, symbol=symbol, limit=min(max(limit, 1), 250))


@router.get("/tracking/quotes/{symbol}")
async def ticker_quote_history(symbol: str, limit: int = 100, db: Session = Depends(get_db)) -> list[dict]:
    return quote_history(db, symbol=symbol, limit=min(max(limit, 1), 500))


async def _first_success(method_name: str, symbol: str, provider_status: dict[str, str], *providers):
    for provider in providers:
        try:
            result = await getattr(provider, method_name)(symbol)
            provider_status[f"{provider.name} {method_name}"] = "ok"
            return result
        except ProviderError as error:
            provider_status[f"{error.provider} {method_name}"] = error.message
    return None


async def _optional_call(awaitable, provider_status: dict[str, str], label: str):
    try:
        result = await awaitable
        provider_status[label] = "ok"
        return result
    except ProviderError as error:
        provider_status[label] = error.message
        return None

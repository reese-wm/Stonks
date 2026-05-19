import json
from datetime import datetime, timezone

import httpx

from app.config import get_settings
from app.schemas.market import QuantIntelligenceReport, TickerResearch
from app.services.ai_projection import _extract_output_text, _strip_json_fence


OPEN_SOURCE_INSPIRATION = [
    "OpenBB-style provider abstraction and multi-source research context",
    "Backtrader-style strategy/backtest checklist",
    "Zipline-style factor and event-driven research framing",
    "FinRL-style ML readiness review for state, reward, and environment design",
    "QuantConnect LEAN-style production readiness, brokerage, and risk-control framing",
]

SYSTEM_PROMPT = """You are a cautious quant research assistant.
Use only the supplied backend-fetched stock data and framework-readiness scores.
Do not invent backtest results, price targets, trades, catalysts, or news.
Do not give personalized financial advice or direct buy/sell instructions.
Return JSON only with concise research-support language."""


async def build_quant_intelligence_report(research: TickerResearch) -> QuantIntelligenceReport:
    fallback = _deterministic_report(research)
    settings = get_settings()
    if not settings.openai_api_key:
        fallback.warnings.append("OPENAI_API_KEY is not configured, so Quant Intelligence uses the local rules engine.")
        return fallback

    payload = {
        "symbol": research.symbol,
        "quote": research.quote.model_dump(mode="json") if research.quote else None,
        "profile": research.profile.model_dump(mode="json") if research.profile else None,
        "latest_bars": [row.model_dump(mode="json") for row in research.historical[-60:]],
        "indicators": research.indicators.model_dump(mode="json"),
        "news_count": len(research.news),
        "latest_news": [item.model_dump(mode="json") for item in research.news[:8]],
        "filings_count": len(research.filings),
        "tipranks": research.tipranks.model_dump(mode="json") if research.tipranks else None,
        "research_score": research.score.model_dump(mode="json"),
        "fallback_quant_report": fallback.model_dump(mode="json"),
    }
    request = {
        "model": settings.openai_model,
        "instructions": SYSTEM_PROMPT,
        "input": (
            "Polish this into a quant intelligence report inspired by OpenBB, Backtrader, Zipline, FinRL, and LEAN. "
            "Return JSON with keys: summary, signal_stack, backtest_plan, ai_workflow_notes, risk_controls, warnings. "
            "Use the fallback scores as-is unless a data-quality reason is present.\n"
            f"{json.dumps(payload, default=str)}"
        ),
        "max_output_tokens": 1100,
    }

    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
                json=request,
            )
            response.raise_for_status()
            parsed = json.loads(_strip_json_fence(_extract_output_text(response.json())))
            return QuantIntelligenceReport(
                symbol=research.symbol,
                generated_at=datetime.now(timezone.utc),
                generated_by=f"OpenAI Responses API ({settings.openai_model})",
                summary=parsed.get("summary") or fallback.summary,
                data_coverage_score=fallback.data_coverage_score,
                backtest_readiness_score=fallback.backtest_readiness_score,
                ml_readiness_score=fallback.ml_readiness_score,
                signal_stack=[str(item) for item in parsed.get("signal_stack", fallback.signal_stack)],
                backtest_plan=[str(item) for item in parsed.get("backtest_plan", fallback.backtest_plan)],
                ai_workflow_notes=[str(item) for item in parsed.get("ai_workflow_notes", fallback.ai_workflow_notes)],
                risk_controls=[str(item) for item in parsed.get("risk_controls", fallback.risk_controls)],
                open_source_inspiration=OPEN_SOURCE_INSPIRATION,
                warnings=[str(item) for item in parsed.get("warnings", fallback.warnings)],
            )
    except Exception as error:
        fallback.warnings.append(f"OpenAI Quant Intelligence failed, using rules engine: {str(error)[:180]}")
        return fallback


def _deterministic_report(research: TickerResearch) -> QuantIntelligenceReport:
    bars = len(research.historical)
    providers = {row.provider for row in research.historical}
    if research.quote:
        providers.add(research.quote.freshness.provider)
    providers.update(article.provider for article in research.news)
    if research.tipranks:
        providers.add(research.tipranks.provider)

    data_coverage = 20
    if research.quote:
        data_coverage += 15
    if bars >= 200:
        data_coverage += 25
    elif bars >= 60:
        data_coverage += 18
    elif bars >= 20:
        data_coverage += 10
    if research.news:
        data_coverage += 10
    if research.filings:
        data_coverage += 10
    if research.tipranks:
        data_coverage += 10
    data_coverage = _clamp(data_coverage)

    backtest_readiness = _clamp(25 + min(35, bars / 6) + (15 if research.indicators.sma_50 else 0) + (15 if research.quote and research.quote.volume else 0))
    ml_readiness = _clamp(20 + min(25, bars / 10) + (15 if research.news else 0) + (15 if research.tipranks else 0) + (10 if len(providers) >= 3 else 0))

    summary = (
        f"{research.symbol} has data coverage {data_coverage:.0f}/100, backtest readiness {backtest_readiness:.0f}/100, "
        f"and ML readiness {ml_readiness:.0f}/100. Treat this as a research workflow score, not a trading signal."
    )
    signal_stack = [
        f"Technical layer: {research.score.rating_label} with composite score {research.score.composite_score}.",
        f"Market data layer: {bars} daily bars from {', '.join(sorted(providers)) or 'no provider'} coverage.",
        "Sentiment layer: combine provider news, TipRanks sentiment when enabled, and SEC filing context.",
    ]
    backtest_plan = [
        "Start with a simple momentum/mean-reversion baseline before adding AI signals.",
        "Use walk-forward splits and out-of-sample validation before trusting any result.",
        "Track slippage, spreads, borrow constraints, and minimum liquidity, especially for sub-$1 names.",
    ]
    ai_workflow_notes = [
        "Use OpenAI to summarize fetched JSON and generate hypotheses, not to invent market data.",
        "Promote features only after they can be reproduced from historical bars, news timestamps, and filings.",
        "FinRL-style reinforcement learning needs a stable environment, reward design, and much more history than a single ticker screen.",
    ]
    risk_controls = [
        "Require position sizing limits before any live or paper-trading workflow.",
        "Block strategies that only work on one ticker or one recent market regime.",
        "Separate research scores from executable orders until backtests and paper trading are added.",
    ]
    warnings = ["Quant Intelligence is a research assistant layer, not financial advice or an execution engine."]
    if bars < 200:
        warnings.append("Backtest readiness is limited because fewer than 200 daily bars are available.")
    if not research.tipranks:
        warnings.append("TipRanks-style analyst/news sentiment is unavailable or disabled.")

    return QuantIntelligenceReport(
        symbol=research.symbol,
        generated_at=datetime.now(timezone.utc),
        summary=summary,
        data_coverage_score=data_coverage,
        backtest_readiness_score=backtest_readiness,
        ml_readiness_score=ml_readiness,
        signal_stack=signal_stack,
        backtest_plan=backtest_plan,
        ai_workflow_notes=ai_workflow_notes,
        risk_controls=risk_controls,
        open_source_inspiration=OPEN_SOURCE_INSPIRATION,
        warnings=warnings,
    )


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)

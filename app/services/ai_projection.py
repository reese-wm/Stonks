import json
from datetime import datetime, timezone

import httpx

from app.config import get_settings
from app.schemas.market import ProjectionItem, TopProjectedBuy, UnderDollarStock


SYSTEM_PROMPT = """You are a financial research assistant.
Use only the structured market data provided by the backend.
Do not invent prices, tickers, dates, catalysts, or percentages.
Avoid personalized financial advice and guaranteed predictions.
Return concise research-support language only."""


TOP_BUY_PROMPT = """You are a cautious market data analyst.
Use only the supplied top-100 under-$1 stock dataset and buyer-behavior proxy metrics.
Buyer behavior means observable market behavior only: volume, price action, close strength,
liquidity, and short trend persistence. Do not claim knowledge of individual buyers.
Return JSON only. Avoid personalized financial advice, certainty, or guarantees."""


async def build_ai_projection_summary(leaders: list[UnderDollarStock]) -> tuple[str | None, list[ProjectionItem], str | None]:
    settings = get_settings()
    deterministic = build_deterministic_projections(leaders)
    if not settings.openai_api_key or not leaders:
        return None, deterministic, None

    payload = [
        {
            "symbol": item.symbol,
            "name": item.name,
            "price": item.price,
            "change_percent": item.change_percent,
            "volume": item.volume,
            "market_cap": item.market_cap,
            "fetched_at": item.fetched_at.isoformat(),
            "sparkline": [{"date": str(point.date), "close": point.close, "volume": point.volume} for point in item.sparkline[-10:]],
        }
        for item in leaders[:10]
    ]

    request = {
        "model": settings.openai_model,
        "instructions": SYSTEM_PROMPT,
        "input": (
            "Analyze these under-$1 market movers and return JSON with keys "
            "summary and projections. projections must be an array of at most 5 objects "
            "with symbol, label, thesis, evidence, risks, and score 0-100. "
            f"Data generated at {datetime.now(timezone.utc).isoformat()} UTC.\n"
            f"{json.dumps(payload, default=str)}"
        ),
        "max_output_tokens": 900,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
                json=request,
            )
            response.raise_for_status()
            data = response.json()
            text = _extract_output_text(data)
            parsed = json.loads(_strip_json_fence(text))
            projections = [
                ProjectionItem(
                    symbol=str(item.get("symbol", "")).upper(),
                    label=item.get("label") or "Watchlist candidate",
                    thesis=item.get("thesis") or "Needs more research.",
                    evidence=[str(value) for value in item.get("evidence", [])],
                    risks=[str(value) for value in item.get("risks", [])],
                    score=float(item.get("score", 50)),
                )
                for item in parsed.get("projections", [])
                if item.get("symbol")
            ]
            return parsed.get("summary"), projections or deterministic, f"OpenAI Responses API ({settings.openai_model})"
    except Exception:
        return None, deterministic, None


async def build_top_projected_buy(leaders: list[UnderDollarStock]) -> TopProjectedBuy:
    settings = get_settings()
    generated_at = datetime.now(timezone.utc)
    candidates = build_buyer_behavior_projections(leaders)
    warnings = [
        "Research support only; this is not personalized financial advice.",
        "Buyer behavior is inferred from observable price and volume data, not individual trader identities.",
    ]
    methodology = (
        "Ranks the top 100 under-$1 candidates using price momentum, reported volume, "
        "relative-volume proxy, close-strength proxy, accumulation-style up-day streaks, "
        "trend persistence, liquidity, and sub-$1 risk penalties."
    )

    if not settings.openai_api_key or not leaders:
        if not settings.openai_api_key:
            warnings.append("OPENAI_API_KEY is missing, so the rules engine selected the top projected buy.")
        return TopProjectedBuy(
            generated_at=generated_at,
            universe_count=len(leaders),
            selected=candidates[0] if candidates else None,
            candidates=candidates[:10],
            ai_provider=None,
            ai_summary=None,
            methodology=methodology,
            warnings=warnings,
        )

    payload = [
        {
            "symbol": candidate.symbol,
            "label": candidate.label,
            "thesis": candidate.thesis,
            "score": candidate.score,
            "evidence": candidate.evidence,
            "risks": candidate.risks,
            "buyer_behavior": candidate.buyer_behavior,
            "score_components": candidate.score_components,
        }
        for candidate in candidates[:100]
    ]
    request = {
        "model": settings.openai_model,
        "instructions": TOP_BUY_PROMPT,
        "input": (
            "Select one top projected buy candidate from this under-$1 universe. "
            "Return JSON with keys: summary, selected_symbol, selected_label, selected_thesis, "
            "selected_evidence array, selected_risks array, selected_score number, and watchlist_symbols array. "
            "Keep the thesis cautious and evidence-based.\n"
            f"Data generated at {generated_at.isoformat()} UTC.\n"
            f"{json.dumps(payload, default=str)}"
        ),
        "max_output_tokens": 1200,
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
                json=request,
            )
            response.raise_for_status()
            parsed = json.loads(_strip_json_fence(_extract_output_text(response.json())))
            selected_symbol = str(parsed.get("selected_symbol") or "").upper()
            selected = next((candidate for candidate in candidates if candidate.symbol == selected_symbol), None)
            if selected:
                selected.label = parsed.get("selected_label") or selected.label
                selected.thesis = parsed.get("selected_thesis") or selected.thesis
                selected.evidence = [str(value) for value in parsed.get("selected_evidence", [])] or selected.evidence
                selected.risks = [str(value) for value in parsed.get("selected_risks", [])] or selected.risks
                selected.score = _clamp_score(parsed.get("selected_score"), selected.score)
            return TopProjectedBuy(
                generated_at=generated_at,
                universe_count=len(leaders),
                selected=selected or (candidates[0] if candidates else None),
                candidates=candidates[:10],
                ai_provider=f"OpenAI Responses API ({settings.openai_model})",
                ai_summary=parsed.get("summary"),
                methodology=methodology,
                warnings=warnings,
            )
    except Exception as error:
        warnings.append(f"OpenAI top-buy analysis failed, using rules engine: {str(error)[:180]}")
        return TopProjectedBuy(
            generated_at=generated_at,
            universe_count=len(leaders),
            selected=candidates[0] if candidates else None,
            candidates=candidates[:10],
            ai_provider=None,
            ai_summary=None,
            methodology=methodology,
            warnings=warnings,
        )


def build_deterministic_projections(leaders: list[UnderDollarStock]) -> list[ProjectionItem]:
    return build_buyer_behavior_projections(leaders)[:5]


def build_buyer_behavior_projections(leaders: list[UnderDollarStock]) -> list[ProjectionItem]:
    projections = [_projection_from_market_behavior(item) for item in leaders[:100]]
    return sorted(projections, key=lambda item: item.score, reverse=True)


def _projection_from_market_behavior(item: UnderDollarStock) -> ProjectionItem:
    change = item.change_percent or 0.0
    volume = item.volume or 0
    closes = [point.close for point in item.sparkline if point.close is not None]
    volumes = [point.volume for point in item.sparkline if point.volume]
    sparkline_return = _percent_change(closes[0], closes[-1]) if len(closes) >= 2 else None
    up_days = sum(1 for previous, current in zip(closes, closes[1:]) if current > previous)
    down_days = sum(1 for previous, current in zip(closes, closes[1:]) if current < previous)
    avg_volume_proxy = (sum(volumes[:-1]) / len(volumes[:-1])) if len(volumes) > 1 else _average_volume_proxy(volume, len(closes))
    relative_volume = volume / avg_volume_proxy if avg_volume_proxy else 1.0
    close_strength = _close_strength(item)
    liquidity_score = min(20.0, volume / 250_000)
    momentum_score = max(0.0, min(35.0, (change + 10) * 0.9))
    trend_score = max(0.0, min(20.0, ((sparkline_return or change) + 15) * 0.45))
    behavior_score = max(0.0, min(25.0, relative_volume * 7 + close_strength * 8 + max(0, up_days - down_days)))
    risk_penalty = 0.0
    if item.price and item.price < 0.10:
        risk_penalty += 8.0
    if volume < 100_000:
        risk_penalty += 10.0
    if item.market_cap and item.market_cap < 25_000_000:
        risk_penalty += 5.0
    score = max(5.0, min(98.0, 25 + momentum_score + trend_score + behavior_score + liquidity_score - risk_penalty))

    evidence = []
    risks = ["Sub-$1 stocks can reverse quickly and may have dilution, delisting, or liquidity risk."]
    if item.change_percent is not None:
        evidence.append(f"Latest provider move: {item.change_percent:.2f}%.")
    if volume:
        evidence.append(f"Reported volume: {volume:,}.")
    if sparkline_return is not None:
        evidence.append(f"Sparkline trend over {len(closes)} closes: {sparkline_return:.2f}%.")
    evidence.append(f"Buyer-behavior proxy score: {behavior_score:.2f}/25 from relative volume, close strength, and up-day persistence.")
    if item.price and item.price < 0.10:
        risks.append("Price below $0.10 adds severe microcap volatility risk.")
    if volume < 100_000:
        risks.append("Volume is below the preferred liquidity threshold for this screener.")

    return ProjectionItem(
        symbol=item.symbol,
        label="Top projected buy candidate" if score >= 75 else ("Momentum watchlist candidate" if score >= 60 else "Needs more confirmation"),
        thesis="Observable price and volume behavior shows buyer interest, but this should be confirmed with news, filings, spreads, and position sizing.",
        evidence=evidence,
        risks=risks,
        score=round(score, 2),
        buyer_behavior={
            "reported_volume": volume,
            "relative_volume_proxy": round(relative_volume, 2),
            "close_strength_proxy": round(close_strength, 2),
            "up_days_in_sparkline": up_days,
            "down_days_in_sparkline": down_days,
            "sparkline_return_percent": round(sparkline_return, 2) if sparkline_return is not None else None,
            "interpretation": _behavior_interpretation(relative_volume, close_strength, up_days, down_days),
        },
        score_components={
            "momentum": round(momentum_score, 2),
            "trend": round(trend_score, 2),
            "buyer_behavior": round(behavior_score, 2),
            "liquidity": round(liquidity_score, 2),
            "risk_penalty": round(risk_penalty, 2),
        },
    )


def _percent_change(start: float | None, end: float | None) -> float | None:
    if not start or end is None:
        return None
    return (end - start) / start * 100


def _average_volume_proxy(volume: int, close_count: int) -> float:
    if close_count >= 10:
        return max(100_000.0, volume / 1.35)
    return max(100_000.0, volume / 1.1)


def _close_strength(item: UnderDollarStock) -> float:
    change = item.change_percent or 0.0
    if change <= 0:
        return 0.2
    if change >= 25:
        return 1.0
    return max(0.2, change / 25)


def _behavior_interpretation(relative_volume: float, close_strength: float, up_days: int, down_days: int) -> str:
    if relative_volume >= 2 and close_strength >= 0.7 and up_days >= down_days:
        return "Strong observable demand: elevated volume with firm price action."
    if relative_volume >= 1.25 and up_days >= down_days:
        return "Moderate buyer-interest signal from volume and trend persistence."
    if down_days > up_days:
        return "Mixed signal: recent close sequence has more down days than up days."
    return "Early signal only; needs more confirmation."


def _clamp_score(value, fallback: float) -> float:
    try:
        return round(max(0.0, min(100.0, float(value))), 2)
    except (TypeError, ValueError):
        return fallback


def _extract_output_text(data: dict) -> str:
    if data.get("output_text"):
        return data["output_text"]
    chunks: list[str] = []
    for output in data.get("output", []):
        for content in output.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(content["text"])
    return "".join(chunks)


def _strip_json_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return cleaned.strip()

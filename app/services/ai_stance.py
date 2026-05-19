import json

import httpx

from app.config import get_settings
from app.schemas.market import AIStockStance, TickerResearch
from app.services.ai_summary import _extract_output_text, _strip_json_fence


SYSTEM_PROMPT = """You are a cautious stock research assistant.
Use only the backend-fetched JSON data supplied by the app.
Return whether the evidence is bullish, bearish, or neutral/mixed.
Do not invent data, browse, or give personalized buy/sell instructions.
Return JSON only."""


async def build_ai_stock_stance(research: TickerResearch) -> AIStockStance:
    settings = get_settings()
    fallback = _rules_stance(research)
    if not settings.openai_api_key:
        fallback.warnings.append("OPENAI_API_KEY is not configured, so stance uses the local rules engine.")
        return fallback

    payload = {
        "symbol": research.symbol,
        "quote": research.quote.model_dump(mode="json") if research.quote else None,
        "indicators": research.indicators.model_dump(mode="json"),
        "score": research.score.model_dump(mode="json"),
        "latest_historical_bars": [row.model_dump(mode="json") for row in research.historical[-45:]],
        "news": [item.model_dump(mode="json") for item in research.news[:8]],
        "tipranks": research.tipranks.model_dump(mode="json") if research.tipranks else None,
        "rules_stance": fallback.model_dump(mode="json"),
    }
    request = {
        "model": settings.openai_model,
        "instructions": SYSTEM_PROMPT,
        "input": (
            "Create a concise stock stance JSON with keys: stance, confidence, score, summary, "
            "bullish_evidence, bearish_evidence, watch_items. Stance must be one of bullish, bearish, neutral/mixed. "
            "Score is 0-100 where higher is more bullish. Use only this data:\n"
            f"{json.dumps(payload, default=str)}"
        ),
        "max_output_tokens": 750,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
                json=request,
            )
            response.raise_for_status()
            parsed = json.loads(_strip_json_fence(_extract_output_text(response.json())))
            return AIStockStance(
                symbol=research.symbol,
                stance=_normalize_stance(parsed.get("stance"), fallback.stance),
                confidence=str(parsed.get("confidence") or fallback.confidence),
                score=_clamp(parsed.get("score"), fallback.score),
                summary=parsed.get("summary") or fallback.summary,
                bullish_evidence=[str(item) for item in parsed.get("bullish_evidence", fallback.bullish_evidence)],
                bearish_evidence=[str(item) for item in parsed.get("bearish_evidence", fallback.bearish_evidence)],
                watch_items=[str(item) for item in parsed.get("watch_items", fallback.watch_items)],
                generated_by=f"OpenAI Responses API ({settings.openai_model})",
            )
    except Exception as error:
        fallback.warnings.append(f"OpenAI stance failed, using rules engine: {str(error)[:180]}")
        return fallback


def _rules_stance(research: TickerResearch) -> AIStockStance:
    score = research.score.composite_score
    if research.score.risk_score >= 75:
        stance = "neutral/mixed"
        confidence = "low"
    elif score >= 62:
        stance = "bullish"
        confidence = "medium"
    elif score <= 40:
        stance = "bearish"
        confidence = "medium"
    else:
        stance = "neutral/mixed"
        confidence = "medium" if research.quote and research.historical else "low"

    latest_move = research.quote.change_percent if research.quote else None
    bullish = list(research.score.bull_case[:4])
    bearish = list(research.score.bear_case[:4])
    if latest_move is not None:
        if latest_move > 0:
            bullish.insert(0, f"Latest displayed move is positive at {latest_move:.2f}%.")
        elif latest_move < 0:
            bearish.insert(0, f"Latest displayed move is negative at {latest_move:.2f}%.")

    summary = (
        f"ChatGPT-style stance for {research.symbol}: {stance}. "
        f"The rules score is {score:.2f}/100 with risk score {research.score.risk_score:.2f}/100."
    )
    return AIStockStance(
        symbol=research.symbol,
        stance=stance,
        confidence=confidence,
        score=score,
        summary=summary,
        bullish_evidence=bullish or ["No strong bullish evidence from available data."],
        bearish_evidence=bearish or ["No strong bearish evidence from available data."],
        watch_items=[
            "Confirm quote delay and provider freshness.",
            "Compare the latest move against volume and broader market direction.",
            "Review new filings, credible news, and liquidity before acting.",
        ],
    )


def _normalize_stance(value, fallback: str) -> str:
    cleaned = str(value or "").lower().strip()
    if cleaned in {"bullish", "bearish", "neutral/mixed"}:
        return cleaned
    if cleaned in {"neutral", "mixed"}:
        return "neutral/mixed"
    return fallback


def _clamp(value, fallback: float) -> float:
    try:
        return round(max(0.0, min(100.0, float(value))), 2)
    except (TypeError, ValueError):
        return fallback

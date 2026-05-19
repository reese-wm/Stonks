import json

import httpx

from app.config import get_settings
from app.schemas.market import AIResearchBrief, TickerResearch


SYSTEM_PROMPT = """You are a stock research assistant.
Use only the JSON data provided by the backend.
Do not invent prices, metrics, ratings, catalysts, or news.
Do not browse, scrape, or imply you checked outside sources.
Do not provide personalized financial advice or buy/sell instructions.
Return concise research-support language only."""


async def build_ai_research_brief(research: TickerResearch) -> AIResearchBrief:
    settings = get_settings()
    fallback = _deterministic_brief(research)
    if not settings.openai_api_key:
        fallback.warnings.append("OPENAI_API_KEY is not configured, so this brief uses the local rules engine.")
        return fallback

    payload = _compact_research_payload(research)
    request = {
        "model": settings.openai_model,
        "instructions": SYSTEM_PROMPT,
        "input": (
            "Create a JSON research brief with keys: summary, bull_case, bear_case, "
            "risks, watch_items, confidence, data_sources_used. "
            "Use only this backend-fetched JSON data:\n"
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
            parsed = json.loads(_strip_json_fence(_extract_output_text(response.json())))
            return AIResearchBrief(
                symbol=research.symbol,
                summary=parsed.get("summary") or fallback.summary,
                bull_case=[str(item) for item in parsed.get("bull_case", fallback.bull_case)],
                bear_case=[str(item) for item in parsed.get("bear_case", fallback.bear_case)],
                risks=[str(item) for item in parsed.get("risks", fallback.risks)],
                watch_items=[str(item) for item in parsed.get("watch_items", fallback.watch_items)],
                confidence=str(parsed.get("confidence") or "low"),
                data_sources_used=[str(item) for item in parsed.get("data_sources_used", fallback.data_sources_used)],
                generated_by=f"OpenAI Responses API ({settings.openai_model})",
                warnings=[],
            )
    except Exception as error:
        fallback.warnings.append(f"OpenAI summary failed, using rules engine: {str(error)[:180]}")
        return fallback


def _deterministic_brief(research: TickerResearch) -> AIResearchBrief:
    sources = sorted(
        {
            *(item.provider for item in research.historical),
            *(item.provider for item in research.news),
            *(item.source for item in research.filings),
            research.quote.freshness.provider if research.quote else "none",
            research.tipranks.provider if research.tipranks else "none",
        }
    )
    price = research.quote.price if research.quote else None
    rating = research.score.rating_label
    summary = (
        f"{research.symbol} is classified as {rating} from available data. "
        f"Latest displayed price is {price}." if price is not None else
        f"{research.symbol} has limited quote data, so the brief has low confidence."
    )
    return AIResearchBrief(
        symbol=research.symbol,
        summary=summary,
        bull_case=research.score.bull_case,
        bear_case=research.score.bear_case,
        risks=research.score.risk_notes + research.score.data_warnings,
        watch_items=[
            "Confirm data freshness and provider delay terms.",
            "Review recent filings and credible news before acting.",
            "Compare price action with volume and broader market conditions.",
        ],
        confidence="medium" if research.quote and research.historical else "low",
        data_sources_used=[source for source in sources if source and source != "none"],
    )


def _compact_research_payload(research: TickerResearch) -> dict:
    return {
        "symbol": research.symbol,
        "quote": research.quote.model_dump(mode="json") if research.quote else None,
        "profile": research.profile.model_dump(mode="json") if research.profile else None,
        "latest_historical_bars": [item.model_dump(mode="json") for item in research.historical[-20:]],
        "indicators": research.indicators.model_dump(mode="json"),
        "news": [item.model_dump(mode="json") for item in research.news[:10]],
        "filings": [item.model_dump(mode="json") for item in research.filings[:10]],
        "tipranks": research.tipranks.model_dump(mode="json") if research.tipranks else None,
        "score": research.score.model_dump(mode="json"),
        "provider_status": research.provider_status,
    }


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

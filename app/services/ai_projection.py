import json
from datetime import datetime, timezone

import httpx

from app.config import get_settings
from app.schemas.market import ProjectionItem, UnderDollarStock


SYSTEM_PROMPT = """You are a financial research assistant.
Use only the structured market data provided by the backend.
Do not invent prices, tickers, dates, catalysts, or percentages.
Avoid personalized financial advice and guaranteed predictions.
Return concise research-support language only."""


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
            "sparkline": [{"date": str(point.date), "close": point.close} for point in item.sparkline[-10:]],
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


def build_deterministic_projections(leaders: list[UnderDollarStock]) -> list[ProjectionItem]:
    projections: list[ProjectionItem] = []
    for item in leaders[:5]:
        change = item.change_percent or 0
        volume = item.volume or 0
        score = min(95, max(25, 50 + change * 0.7 + (10 if volume > 1_000_000 else 0)))
        evidence = []
        risks = ["Sub-$1 stocks can be highly volatile and thinly capitalized."]
        if item.change_percent is not None:
            evidence.append(f"Latest provider change is {item.change_percent:.2f}%.")
        if item.volume:
            evidence.append(f"Reported volume is {item.volume:,}.")
        if item.sparkline:
            start = item.sparkline[0].close
            end = item.sparkline[-1].close
            if start:
                evidence.append(f"Recent close-to-close move over sparkline window is {(end - start) / start * 100:.2f}%.")
        if item.market_cap and item.market_cap < 50_000_000:
            risks.append("Market cap is very small, increasing liquidity and dilution risk.")
        projections.append(
            ProjectionItem(
                symbol=item.symbol,
                label="Momentum watchlist candidate" if score >= 60 else "Needs more confirmation",
                thesis="Positive price/volume evidence is present, but confirmation from filings, news, and liquidity is still needed.",
                evidence=evidence or ["Provider data is limited."],
                risks=risks,
                score=round(score, 2),
            )
        )
    return projections


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

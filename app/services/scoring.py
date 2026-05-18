from app.schemas.market import IndicatorSnapshot, NewsArticle, Quote, ResearchScore


def build_research_score(
    quote: Quote | None,
    indicators: IndicatorSnapshot,
    news: list[NewsArticle],
    *,
    data_warnings: list[str] | None = None,
) -> ResearchScore:
    bull_case: list[str] = []
    bear_case: list[str] = []
    risk_notes: list[str] = []
    warnings = data_warnings or []

    technical = 50.0
    momentum = 50.0
    risk = 35.0

    price = quote.price if quote else None
    if price and indicators.sma_50:
        if price > indicators.sma_50:
            technical += 12
            bull_case.append("Price is above SMA50.")
        else:
            technical -= 10
            bear_case.append("Price is below SMA50.")

    if price and indicators.sma_200:
        if price > indicators.sma_200:
            technical += 10
            bull_case.append("Price is above SMA200.")
        else:
            technical -= 12
            bear_case.append("Price is below SMA200.")

    if indicators.rsi_14 is not None:
        if indicators.rsi_14 > 70:
            technical -= 6
            risk += 8
            risk_notes.append("RSI is in overbought territory.")
        elif indicators.rsi_14 < 30:
            technical -= 4
            risk += 8
            risk_notes.append("RSI is in oversold territory.")
        else:
            technical += 5

    if indicators.macd_histogram is not None:
        if indicators.macd_histogram > 0:
            momentum += 12
            bull_case.append("MACD histogram is positive.")
        else:
            momentum -= 8
            bear_case.append("MACD histogram is negative.")

    if indicators.relative_volume and indicators.relative_volume > 1.5:
        momentum += 8
        risk += 5
        risk_notes.append("Relative volume is elevated.")

    if indicators.atr_14 and price:
        atr_percent = indicators.atr_14 / price * 100
        if atr_percent > 5:
            risk += 18
            risk_notes.append("ATR indicates high day-to-day volatility.")
        elif atr_percent > 2.5:
            risk += 8
            risk_notes.append("ATR indicates medium volatility.")

    news_score = _news_score(news)
    if not news:
        warnings.append("Recent news data is missing.")

    fundamental = 50.0
    valuation = 50.0
    warnings.append("Fundamental and valuation scoring are placeholders until statements/ratios are connected.")

    technical = _clamp(technical)
    momentum = _clamp(momentum)
    risk = _clamp(risk)
    composite = (
        0.30 * technical
        + 0.25 * fundamental
        + 0.20 * news_score
        + 0.15 * valuation
        + 0.10 * momentum
        - max(risk - 50, 0) * 0.35
    )
    composite = _clamp(composite)

    return ResearchScore(
        technical_score=technical,
        fundamental_score=fundamental,
        news_score=news_score,
        risk_score=risk,
        momentum_score=momentum,
        valuation_score=valuation,
        composite_score=round(composite, 2),
        rating_label=_rating_label(composite, risk),
        bull_case=bull_case or ["No strong bullish evidence from available data."],
        bear_case=bear_case or ["No strong bearish evidence from available data."],
        risk_notes=risk_notes or ["No major risk flags calculated from available indicators."],
        data_warnings=warnings,
    )


def _news_score(articles: list[NewsArticle]) -> float:
    if not articles:
        return 50.0
    weighted = 0.0
    total_weight = 0.0
    for article in articles:
        weight = article.relevance_score * article.credibility_score
        weighted += (50 + article.sentiment_score * 50) * weight
        total_weight += weight
    return _clamp(weighted / total_weight if total_weight else 50)


def _rating_label(score: float, risk: float) -> str:
    if risk >= 75:
        return "High-risk speculative setup"
    if score >= 70:
        return "Strong watchlist candidate"
    if score >= 60:
        return "Bullish setup, confirm risk"
    if score >= 45:
        return "Neutral / mixed evidence"
    if score >= 35:
        return "Weak setup"
    return "Avoid for now"


def _clamp(value: float) -> float:
    return round(max(0, min(100, value)), 2)

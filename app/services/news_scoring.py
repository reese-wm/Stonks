from datetime import datetime, timezone

from app.schemas.market import NewsArticle


HIGH_CREDIBILITY_SOURCES = {"sec", "reuters", "ap", "business wire", "globe newswire", "investor relations"}
LOW_CREDIBILITY_TERMS = {"rumor", "rumour", "penny stock", "promotion"}


def score_articles(articles: list[NewsArticle]) -> list[NewsArticle]:
    now = datetime.now(timezone.utc)
    scored: list[NewsArticle] = []
    for article in articles:
        source = article.source_name.lower()
        credibility = 0.65
        if any(term in source for term in HIGH_CREDIBILITY_SOURCES):
            credibility = 0.95
        if any(term in (article.headline + " " + (article.summary or "")).lower() for term in LOW_CREDIBILITY_TERMS):
            credibility = 0.35

        recency = 0.5
        if article.published_at:
            age_hours = (now - article.published_at).total_seconds() / 3600
            if age_hours <= 6:
                recency = 1.0
            elif age_hours <= 24:
                recency = 0.85
            elif age_hours <= 72:
                recency = 0.65
            elif age_hours <= 168:
                recency = 0.35
            else:
                recency = 0.15

        article.credibility_score = credibility
        article.relevance_score = max(article.relevance_score, recency * 0.8)
        scored.append(article)
    return scored

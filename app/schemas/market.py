from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class DataFreshness(BaseModel):
    provider: str
    fetched_at: datetime
    source_timestamp: datetime | date | None = None
    quote_type: str = "unknown"
    display_note: str


class Quote(BaseModel):
    symbol: str
    price: float | None = None
    change: float | None = None
    change_percent: float | None = None
    volume: int | None = None
    market_cap: float | None = None
    freshness: DataFreshness


class OHLCV(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float | None = None
    volume: int
    provider: str


class CompanyProfile(BaseModel):
    symbol: str
    name: str | None = None
    exchange: str | None = None
    country: str | None = None
    currency: str | None = None
    sector: str | None = None
    industry: str | None = None
    website: str | None = None
    description: str | None = None
    provider: str
    fetched_at: datetime


class NewsArticle(BaseModel):
    headline: str
    source_name: str
    url: str
    published_at: datetime | None = None
    summary: str | None = None
    provider: str
    sentiment_score: float = 0
    relevance_score: float = 0.5
    credibility_score: float = 0.5


class Filing(BaseModel):
    filing_type: str
    filing_date: date | None = None
    accession_number: str | None = None
    url: str
    source: str = "SEC EDGAR"


class IndicatorSnapshot(BaseModel):
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    ema_12: float | None = None
    ema_26: float | None = None
    rsi_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    atr_14: float | None = None
    bollinger_upper: float | None = None
    bollinger_middle: float | None = None
    bollinger_lower: float | None = None
    relative_volume: float | None = None
    high_52_week_distance: float | None = None
    low_52_week_distance: float | None = None


class ResearchScore(BaseModel):
    technical_score: float
    fundamental_score: float
    news_score: float
    risk_score: float
    momentum_score: float
    valuation_score: float
    composite_score: float
    rating_label: str
    bull_case: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    data_warnings: list[str] = Field(default_factory=list)


class MiniChartPoint(BaseModel):
    date: date
    close: float


class UnderDollarStock(BaseModel):
    symbol: str
    name: str | None = None
    exchange: str | None = None
    price: float | None = None
    change: float | None = None
    change_percent: float | None = None
    volume: int | None = None
    market_cap: float | None = None
    provider: str
    fetched_at: datetime
    sparkline: list[MiniChartPoint] = Field(default_factory=list)


class ProjectionItem(BaseModel):
    symbol: str
    label: str
    thesis: str
    evidence: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    score: float


class AIResearchBrief(BaseModel):
    symbol: str
    summary: str
    bull_case: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    watch_items: list[str] = Field(default_factory=list)
    confidence: str = "low"
    data_sources_used: list[str] = Field(default_factory=list)
    generated_by: str = "rules engine"
    warnings: list[str] = Field(default_factory=list)


class ProjectionScenario(BaseModel):
    symbol: str
    amount: float
    mode: str
    periods: int
    rate_percent_per_period: float
    projected_value: float
    projected_gain_loss: float
    projected_gain_loss_percent: float
    source_label: str
    explanation: str
    warnings: list[str] = Field(default_factory=list)


class UnderDollarDashboard(BaseModel):
    generated_at: datetime
    provider: str
    freshness_note: str
    leaders: list[UnderDollarStock] = Field(default_factory=list)
    projections: list[ProjectionItem] = Field(default_factory=list)
    ai_summary: str | None = None
    ai_provider: str | None = None
    warnings: list[str] = Field(default_factory=list)


class TickerResearch(BaseModel):
    symbol: str
    quote: Quote | None = None
    profile: CompanyProfile | None = None
    historical: list[OHLCV] = Field(default_factory=list)
    indicators: IndicatorSnapshot
    news: list[NewsArticle] = Field(default_factory=list)
    filings: list[Filing] = Field(default_factory=list)
    score: ResearchScore
    provider_status: dict[str, Any] = Field(default_factory=dict)

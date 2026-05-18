from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UnderDollarSnapshot(Base):
    __tablename__ = "under_dollar_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    provider: Mapped[str] = mapped_column(String(64), default="FMP")
    freshness_note: Mapped[str] = mapped_column(Text, default="")
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_provider: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    warnings_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    leaders: Mapped[list["UnderDollarLeader"]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")
    projections: Mapped[list["ProjectionRecord"]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")


class UnderDollarLeader(Base):
    __tablename__ = "under_dollar_leaders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("under_dollar_snapshots.id"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    exchange: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    provider: Mapped[str] = mapped_column(String(64), default="FMP")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sparkline_json: Mapped[str] = mapped_column(Text, default="[]")

    snapshot: Mapped[UnderDollarSnapshot] = relationship(back_populates="leaders")


class ProjectionRecord(Base):
    __tablename__ = "projection_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("under_dollar_snapshots.id"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    label: Mapped[str] = mapped_column(String(128))
    thesis: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    risks_json: Mapped[str] = mapped_column(Text, default="[]")
    score: Mapped[float] = mapped_column(Float)

    snapshot: Mapped[UnderDollarSnapshot] = relationship(back_populates="projections")


class QuoteSnapshot(Base):
    __tablename__ = "quote_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    provider: Mapped[str] = mapped_column(String(64))
    quote_type: Mapped[str] = mapped_column(String(64), default="unknown")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ApiEvent(Base):
    __tablename__ = "api_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    operation: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

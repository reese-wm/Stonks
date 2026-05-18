import json
from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import ApiEvent, ProjectionRecord, QuoteSnapshot, UnderDollarLeader, UnderDollarSnapshot
from app.schemas.market import MiniChartPoint, ProjectionItem, Quote, UnderDollarDashboard, UnderDollarStock


def save_under_dollar_dashboard(db: Session, dashboard: UnderDollarDashboard) -> int:
    snapshot = UnderDollarSnapshot(
        generated_at=dashboard.generated_at,
        provider=dashboard.provider,
        freshness_note=dashboard.freshness_note,
        ai_summary=dashboard.ai_summary,
        ai_provider=dashboard.ai_provider,
        warnings_json=json.dumps(dashboard.warnings),
    )
    db.add(snapshot)
    db.flush()

    for rank, leader in enumerate(dashboard.leaders, start=1):
        db.add(
            UnderDollarLeader(
                snapshot_id=snapshot.id,
                rank=rank,
                symbol=leader.symbol,
                name=leader.name,
                exchange=leader.exchange,
                price=leader.price,
                change=leader.change,
                change_percent=leader.change_percent,
                volume=leader.volume,
                market_cap=leader.market_cap,
                provider=leader.provider,
                fetched_at=leader.fetched_at,
                sparkline_json=json.dumps([point.model_dump(mode="json") for point in leader.sparkline]),
            )
        )

    for rank, projection in enumerate(dashboard.projections, start=1):
        db.add(
            ProjectionRecord(
                snapshot_id=snapshot.id,
                rank=rank,
                symbol=projection.symbol,
                label=projection.label,
                thesis=projection.thesis,
                evidence_json=json.dumps(projection.evidence),
                risks_json=json.dumps(projection.risks),
                score=projection.score,
            )
        )

    db.commit()
    return snapshot.id


def save_quote_snapshot(db: Session, quote: Quote | None) -> None:
    if quote is None:
        return
    db.add(
        QuoteSnapshot(
            symbol=quote.symbol,
            price=quote.price,
            change=quote.change,
            change_percent=quote.change_percent,
            volume=quote.volume,
            market_cap=quote.market_cap,
            provider=quote.freshness.provider,
            quote_type=quote.freshness.quote_type,
            fetched_at=quote.freshness.fetched_at,
        )
    )
    db.commit()


def log_api_event(db: Session, provider: str, operation: str, status: str, message: str = "") -> None:
    db.add(ApiEvent(provider=provider, operation=operation, status=status, message=message[:1000]))
    db.commit()


def latest_under_dollar_dashboard(db: Session) -> UnderDollarDashboard | None:
    snapshot = db.scalar(
        select(UnderDollarSnapshot)
        .options(selectinload(UnderDollarSnapshot.leaders), selectinload(UnderDollarSnapshot.projections))
        .order_by(desc(UnderDollarSnapshot.generated_at))
        .limit(1)
    )
    if snapshot is None:
        return None
    return _snapshot_to_dashboard(snapshot)


def under_dollar_history(db: Session, limit: int = 24) -> list[dict]:
    snapshots = db.scalars(
        select(UnderDollarSnapshot)
        .options(selectinload(UnderDollarSnapshot.leaders), selectinload(UnderDollarSnapshot.projections))
        .order_by(desc(UnderDollarSnapshot.generated_at))
        .limit(limit)
    ).all()
    return [_snapshot_summary(snapshot) for snapshot in snapshots]


def projection_history(db: Session, symbol: str | None = None, limit: int = 50) -> list[dict]:
    query = select(ProjectionRecord, UnderDollarSnapshot.generated_at).join(UnderDollarSnapshot)
    if symbol:
        query = query.where(ProjectionRecord.symbol == symbol.upper())
    query = query.order_by(desc(UnderDollarSnapshot.generated_at), ProjectionRecord.rank).limit(limit)
    rows = db.execute(query).all()
    return [
        {
            "generated_at": generated_at,
            "symbol": record.symbol,
            "label": record.label,
            "score": record.score,
            "thesis": record.thesis,
            "evidence": json.loads(record.evidence_json or "[]"),
            "risks": json.loads(record.risks_json or "[]"),
        }
        for record, generated_at in rows
    ]


def quote_history(db: Session, symbol: str, limit: int = 100) -> list[dict]:
    rows = db.scalars(
        select(QuoteSnapshot)
        .where(QuoteSnapshot.symbol == symbol.upper())
        .order_by(desc(QuoteSnapshot.fetched_at))
        .limit(limit)
    ).all()
    return [
        {
            "symbol": row.symbol,
            "price": row.price,
            "change": row.change,
            "change_percent": row.change_percent,
            "volume": row.volume,
            "market_cap": row.market_cap,
            "provider": row.provider,
            "quote_type": row.quote_type,
            "fetched_at": row.fetched_at,
        }
        for row in rows
    ]


def data_health_summary(db: Session) -> dict:
    latest_snapshot = db.scalar(select(func.max(UnderDollarSnapshot.generated_at)))
    snapshot_count = db.scalar(select(func.count(UnderDollarSnapshot.id))) or 0
    quote_count = db.scalar(select(func.count(QuoteSnapshot.id))) or 0
    recent_events = db.scalars(select(ApiEvent).order_by(desc(ApiEvent.created_at)).limit(20)).all()
    return {
        "latest_under_dollar_snapshot": latest_snapshot,
        "under_dollar_snapshot_count": snapshot_count,
        "quote_snapshot_count": quote_count,
        "recent_events": [
            {
                "provider": event.provider,
                "operation": event.operation,
                "status": event.status,
                "message": event.message,
                "created_at": event.created_at,
            }
            for event in recent_events
        ],
    }


def _snapshot_to_dashboard(snapshot: UnderDollarSnapshot) -> UnderDollarDashboard:
    leaders = [
        UnderDollarStock(
            symbol=row.symbol,
            name=row.name,
            exchange=row.exchange,
            price=row.price,
            change=row.change,
            change_percent=row.change_percent,
            volume=row.volume,
            market_cap=row.market_cap,
            provider=row.provider,
            fetched_at=row.fetched_at,
            sparkline=[MiniChartPoint(**point) for point in json.loads(row.sparkline_json or "[]")],
        )
        for row in sorted(snapshot.leaders, key=lambda item: item.rank)
    ]
    projections = [
        ProjectionItem(
            symbol=row.symbol,
            label=row.label,
            thesis=row.thesis,
            evidence=json.loads(row.evidence_json or "[]"),
            risks=json.loads(row.risks_json or "[]"),
            score=row.score,
        )
        for row in sorted(snapshot.projections, key=lambda item: item.rank)
    ]
    return UnderDollarDashboard(
        generated_at=snapshot.generated_at,
        provider=snapshot.provider,
        freshness_note=snapshot.freshness_note,
        leaders=leaders,
        projections=projections,
        ai_summary=snapshot.ai_summary,
        ai_provider=snapshot.ai_provider,
        warnings=json.loads(snapshot.warnings_json or "[]"),
    )


def _snapshot_summary(snapshot: UnderDollarSnapshot) -> dict:
    top_leader = min(snapshot.leaders, key=lambda item: item.rank, default=None)
    top_projection = min(snapshot.projections, key=lambda item: item.rank, default=None)
    return {
        "id": snapshot.id,
        "generated_at": snapshot.generated_at,
        "provider": snapshot.provider,
        "leader_count": len(snapshot.leaders),
        "projection_count": len(snapshot.projections),
        "top_leader": top_leader.symbol if top_leader else None,
        "top_leader_change_percent": top_leader.change_percent if top_leader else None,
        "top_projection": top_projection.symbol if top_projection else None,
        "top_projection_score": top_projection.score if top_projection else None,
        "warnings": json.loads(snapshot.warnings_json or "[]"),
    }


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

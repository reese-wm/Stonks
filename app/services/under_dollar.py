from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.providers.base import ProviderError
from app.providers.fmp import FMPProvider
from app.providers.massive import MassiveProvider
from app.schemas.market import UnderDollarDashboard
from app.services.ai_projection import build_ai_projection_summary
from app.services.tracking import log_api_event, save_under_dollar_dashboard


async def build_and_store_under_dollar_dashboard(db: Session, *, persist: bool = True) -> UnderDollarDashboard:
    massive = MassiveProvider()
    fmp = FMPProvider()
    warnings: list[str] = []
    try:
        provider = massive if massive.settings.massive_api_key else fmp
        leaders = await provider.under_dollar_leaders(limit=10)
        leaders = await provider.add_sparklines(leaders[:8], days=20)
        log_api_event(db, provider.name, "under_dollar_leaders", "ok", f"Fetched {len(leaders)} leaders")
    except ProviderError as error:
        leaders = []
        warnings.append(error.message)
        log_api_event(db, error.provider, "under_dollar_leaders", "error", error.message)

    ai_summary, projections, ai_provider = await build_ai_projection_summary(leaders)
    if not leaders:
        warnings.append("Under-$1 leaders require MASSIVE_API_KEY with aggregate access or FMP_API_KEY with screener access.")
    if ai_provider is None:
        warnings.append("OpenAI projections are using deterministic scoring until OPENAI_API_KEY is configured.")
        log_api_event(db, "OpenAI", "under_dollar_projection", "skipped", "OPENAI_API_KEY missing or analysis failed")
    else:
        log_api_event(db, "OpenAI", "under_dollar_projection", "ok", f"Generated {len(projections)} projections")

    dashboard = UnderDollarDashboard(
        generated_at=datetime.now(timezone.utc),
        provider=(leaders[0].provider if leaders else ("Massive" if massive.settings.massive_api_key else "FMP")),
        freshness_note="Provider-fetched under-$1 market data. Confirm provider licensing and exchange delay terms.",
        leaders=leaders,
        projections=projections,
        ai_summary=ai_summary,
        ai_provider=ai_provider,
        warnings=warnings,
    )
    if persist:
        save_under_dollar_dashboard(db, dashboard)
    return dashboard

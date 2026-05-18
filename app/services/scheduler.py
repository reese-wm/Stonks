import asyncio
from contextlib import suppress

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings
from app.database import SessionLocal
from app.services.under_dollar import build_and_store_under_dollar_dashboard


scheduler = BackgroundScheduler(timezone=get_settings().app_timezone)


def start_scheduler() -> None:
    settings = get_settings()
    if scheduler.running:
        return
    scheduler.add_job(
        refresh_under_dollar_job,
        "interval",
        seconds=max(60, settings.under_dollar_refresh_seconds),
        id="refresh_under_dollar",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        with suppress(Exception):
            scheduler.shutdown(wait=False)


def refresh_under_dollar_job() -> None:
    db = SessionLocal()
    try:
        asyncio.run(build_and_store_under_dollar_dashboard(db, persist=True))
    finally:
        db.close()


def scheduler_status() -> dict:
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
        )
    return {"running": scheduler.running, "jobs": jobs}

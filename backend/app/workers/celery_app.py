"""Celery application configuration with beat schedule."""
from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_newsletter",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_max_retries=3,
    task_default_retry_delay=60,
    broker_connection_retry_on_startup=True,
)

# Beat schedule — runs in UTC
celery_app.conf.beat_schedule = {
    # Step 1: Collect articles daily at configured hour
    "daily-collect": {
        "task": "app.workers.tasks.collect_articles_task",
        "schedule": crontab(
            hour=settings.DAILY_COLLECT_HOUR,
            minute=settings.DAILY_COLLECT_MINUTE,
        ),
        "kwargs": {},
    },
    # Step 2: Generate report (1 hour after collection)
    "daily-report": {
        "task": "app.workers.tasks.generate_report_task",
        "schedule": crontab(
            hour=settings.DAILY_REPORT_HOUR,
            minute=settings.DAILY_REPORT_MINUTE,
        ),
        "kwargs": {},
    },
    # Step 3: Send email (1 hour after report)
    "daily-send": {
        "task": "app.workers.tasks.send_daily_email_task",
        "schedule": crontab(
            hour=settings.DAILY_SEND_HOUR,
            minute=settings.DAILY_SEND_MINUTE,
        ),
        "kwargs": {},
    },
}

"""Celery tasks for collection, report generation, and email delivery."""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone

from celery import Task
from tenacity import retry, stop_after_attempt, wait_exponential

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async coroutine from Celery sync context."""
    return asyncio.get_event_loop().run_until_complete(coro)


class LoggedTask(Task):
    """Base task that logs execution to DB."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("Task %s failed: %s", self.name, exc)


@celery_app.task(
    bind=True,
    base=LoggedTask,
    name="app.workers.tasks.collect_articles_task",
    max_retries=3,
    default_retry_delay=120,
)
def collect_articles_task(self, source_ids: list[int] | None = None):
    """Collect articles from all enabled sources."""
    from app.database import AsyncSessionLocal
    from app.models.job import JobExecutionLog, JobStatus, JobType
    from app.services.collector_service import run_collection

    async def _run():
        async with AsyncSessionLocal() as db:
            log = JobExecutionLog(
                job_type=JobType.collect,
                status=JobStatus.running,
                celery_task_id=self.request.id,
                triggered_by="scheduler",
            )
            db.add(log)
            await db.flush()

            try:
                result = await run_collection(db, source_ids=source_ids)
                log.status = JobStatus.success
                log.result_summary = result
            except Exception as exc:
                log.status = JobStatus.failed
                log.error_detail = str(exc)
                await db.commit()
                raise self.retry(exc=exc)
            finally:
                log.finished_at = datetime.now(timezone.utc)
                await db.commit()

            return result

    return _run_async(_run())


@celery_app.task(
    bind=True,
    base=LoggedTask,
    name="app.workers.tasks.generate_report_task",
    max_retries=2,
    default_retry_delay=300,
)
def generate_report_task(self, report_date_str: str | None = None):
    """Generate daily report via LLM."""
    from app.database import AsyncSessionLocal
    from app.models.job import JobExecutionLog, JobStatus, JobType
    from app.services.report_service import generate_daily_report

    target_date = (
        date.fromisoformat(report_date_str) if report_date_str else date.today()
    )

    async def _run():
        async with AsyncSessionLocal() as db:
            log = JobExecutionLog(
                job_type=JobType.generate_report,
                status=JobStatus.running,
                celery_task_id=self.request.id,
                triggered_by="scheduler",
            )
            db.add(log)
            await db.flush()

            try:
                version = await generate_daily_report(db, target_date)
                log.status = JobStatus.success
                log.result_summary = {
                    "report_date": str(target_date),
                    "version_id": version.id,
                    "version_number": version.version_number,
                }
            except Exception as exc:
                log.status = JobStatus.failed
                log.error_detail = str(exc)
                await db.commit()
                raise self.retry(exc=exc)
            finally:
                log.finished_at = datetime.now(timezone.utc)
                await db.commit()

    return _run_async(_run())


@celery_app.task(
    bind=True,
    base=LoggedTask,
    name="app.workers.tasks.send_daily_email_task",
    max_retries=2,
    default_retry_delay=300,
)
def send_daily_email_task(self, report_id: int | None = None):
    """Send today's report to all active recipients."""
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.job import JobExecutionLog, JobStatus, JobType
    from app.models.report import DailyReport, ReportStatus
    from app.services.email_service import send_report

    async def _run():
        async with AsyncSessionLocal() as db:
            log = JobExecutionLog(
                job_type=JobType.send_email,
                status=JobStatus.running,
                celery_task_id=self.request.id,
                triggered_by="scheduler",
            )
            db.add(log)
            await db.flush()

            try:
                # Find the report to send
                if report_id:
                    target_report_id = report_id
                else:
                    result = await db.execute(
                        select(DailyReport)
                        .where(DailyReport.report_date == date.today())
                        .where(DailyReport.status.in_([ReportStatus.ready, ReportStatus.approved]))
                    )
                    report = result.scalar_one_or_none()
                    if not report:
                        log.status = JobStatus.failed
                        log.error_detail = "No ready report found for today"
                        log.finished_at = datetime.now(timezone.utc)
                        await db.commit()
                        return

                    target_report_id = report.id

                result = await send_report(db, report_id=target_report_id)
                log.status = JobStatus.success if result["failed"] == 0 else JobStatus.partial
                log.result_summary = result
            except Exception as exc:
                log.status = JobStatus.failed
                log.error_detail = str(exc)
                await db.commit()
                raise self.retry(exc=exc)
            finally:
                log.finished_at = datetime.now(timezone.utc)
                await db.commit()

    return _run_async(_run())


@celery_app.task(name="app.workers.tasks.send_email_task")
def send_email_task(report_id: int):
    """Wrapper for manual send trigger from API."""
    return send_daily_email_task(report_id=report_id)

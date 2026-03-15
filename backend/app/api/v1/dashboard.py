"""Dashboard summary endpoint."""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.article import Article
from app.models.job import JobExecutionLog
from app.models.report import DailyReport, EmailDelivery, DeliveryStatus, ReportStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(db: AsyncSession = Depends(get_db)):
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)

    # Today's articles count
    articles_today = await db.scalar(
        select(func.count(Article.id)).where(Article.collected_at >= today_start)
    )

    # Today's report
    report_result = await db.execute(
        select(DailyReport).where(DailyReport.report_date == today)
    )
    today_report = report_result.scalar_one_or_none()

    # Today's email deliveries
    deliveries_result = await db.execute(
        select(EmailDelivery).where(EmailDelivery.created_at >= today_start)
    )
    deliveries = deliveries_result.scalars().all()
    sent_count = sum(1 for d in deliveries if d.status == DeliveryStatus.sent)
    failed_count = sum(1 for d in deliveries if d.status == DeliveryStatus.failed)

    # Last 7-day article trend
    trend = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time()).replace(tzinfo=timezone.utc)
        day_end = datetime.combine(day, datetime.max.time()).replace(tzinfo=timezone.utc)
        count = await db.scalar(
            select(func.count(Article.id)).where(
                Article.collected_at >= day_start,
                Article.collected_at <= day_end,
            )
        )
        trend.append({"date": str(day), "count": count or 0})

    # Recent job logs
    logs_result = await db.execute(
        select(JobExecutionLog)
        .order_by(JobExecutionLog.started_at.desc())
        .limit(10)
    )
    recent_logs = [
        {
            "id": log.id,
            "job_type": log.job_type.value,
            "status": log.status.value,
            "started_at": log.started_at.isoformat(),
            "duration": log.duration_seconds,
        }
        for log in logs_result.scalars().all()
    ]

    return {
        "today": str(today),
        "articles_today": articles_today or 0,
        "report_status": today_report.status.value if today_report else None,
        "report_id": today_report.id if today_report else None,
        "emails_sent_today": sent_count,
        "emails_failed_today": failed_count,
        "article_trend_7d": trend,
        "recent_jobs": recent_logs,
    }

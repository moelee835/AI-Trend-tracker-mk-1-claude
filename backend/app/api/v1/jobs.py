"""Job execution — manual triggers and execution log."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job import JobExecutionLog

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobLogOut(BaseModel):
    id: int
    job_type: str
    status: str
    triggered_by: str
    result_summary: dict
    error_detail: Optional[str]
    started_at: datetime
    finished_at: Optional[datetime]
    duration_seconds: Optional[float]

    model_config = {"from_attributes": True}


@router.get("/logs", response_model=list[JobLogOut])
async def list_job_logs(
    job_type: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    query = select(JobExecutionLog).order_by(desc(JobExecutionLog.started_at)).limit(limit)
    if job_type:
        query = query.where(JobExecutionLog.job_type == job_type)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        JobLogOut(
            id=log.id,
            job_type=log.job_type.value,
            status=log.status.value,
            triggered_by=log.triggered_by,
            result_summary=log.result_summary,
            error_detail=log.error_detail,
            started_at=log.started_at,
            finished_at=log.finished_at,
            duration_seconds=log.duration_seconds,
        )
        for log in logs
    ]


@router.post("/run/collect")
async def run_collect():
    """Manually trigger article collection."""
    from app.workers.tasks import collect_articles_task
    task = collect_articles_task.delay()
    return {"task_id": task.id, "status": "queued", "job_type": "collect"}


@router.post("/run/report")
async def run_report(report_date: Optional[str] = None):
    """Manually trigger report generation for today or a given date."""
    from datetime import date
    from app.workers.tasks import generate_report_task
    target = report_date or date.today().isoformat()
    task = generate_report_task.delay(target)
    return {"task_id": task.id, "status": "queued", "job_type": "generate_report", "date": target}


@router.post("/run/send")
async def run_send(report_id: int):
    """Manually trigger email send for a report."""
    from app.workers.tasks import send_email_task
    task = send_email_task.delay(report_id)
    return {"task_id": task.id, "status": "queued", "job_type": "send_email"}

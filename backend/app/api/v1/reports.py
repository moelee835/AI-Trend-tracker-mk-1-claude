"""Report management endpoints."""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.report import DailyReport, ReportStatus, ReportVersion
from app.services.report_service import generate_daily_report

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportOut(BaseModel):
    id: int
    report_date: date
    status: str
    included_article_count: int
    created_at: datetime
    version_count: int

    model_config = {"from_attributes": True}


class ReportVersionOut(BaseModel):
    id: int
    report_id: int
    version_number: int
    is_active: bool
    subject_line: str
    llm_model: Optional[str]
    generation_tokens: Optional[int]
    edited_by_operator: bool
    generated_at: datetime

    model_config = {"from_attributes": True}


class EditReportContent(BaseModel):
    html_content: str
    subject_line: Optional[str] = None


@router.get("/", response_model=list[ReportOut])
async def list_reports(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    status: Optional[ReportStatus] = None,
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(DailyReport)
        .options(selectinload(DailyReport.versions))
        .order_by(desc(DailyReport.report_date))
        .limit(limit)
    )
    if date_from:
        query = query.where(DailyReport.report_date >= date_from)
    if date_to:
        query = query.where(DailyReport.report_date <= date_to)
    if status:
        query = query.where(DailyReport.status == status)

    result = await db.execute(query)
    reports = result.scalars().all()

    return [
        ReportOut(
            id=r.id,
            report_date=r.report_date,
            status=r.status.value,
            included_article_count=len(r.included_article_ids),
            created_at=r.created_at,
            version_count=len(r.versions),
        )
        for r in reports
    ]


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DailyReport)
        .options(selectinload(DailyReport.versions))
        .where(DailyReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportOut(
        id=report.id,
        report_date=report.report_date,
        status=report.status.value,
        included_article_count=len(report.included_article_ids),
        created_at=report.created_at,
        version_count=len(report.versions),
    )


@router.get("/{report_id}/versions", response_model=list[ReportVersionOut])
async def list_versions(report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ReportVersion)
        .where(ReportVersion.report_id == report_id)
        .order_by(desc(ReportVersion.version_number))
    )
    return result.scalars().all()


@router.get("/{report_id}/versions/{version_id}/html")
async def get_version_html(report_id: int, version_id: int, db: AsyncSession = Depends(get_db)):
    version = await db.get(ReportVersion, version_id)
    if not version or version.report_id != report_id:
        raise HTTPException(status_code=404, detail="Version not found")
    return Response(content=version.html_content, media_type="text/html")


@router.patch("/{report_id}/versions/{version_id}", response_model=ReportVersionOut)
async def edit_version(
    report_id: int,
    version_id: int,
    payload: EditReportContent,
    db: AsyncSession = Depends(get_db),
):
    version = await db.get(ReportVersion, version_id)
    if not version or version.report_id != report_id:
        raise HTTPException(status_code=404, detail="Version not found")
    version.html_content = payload.html_content
    if payload.subject_line:
        version.subject_line = payload.subject_line
    version.edited_by_operator = True
    await db.commit()
    await db.refresh(version)
    return version


@router.post("/{report_id}/approve", response_model=ReportOut)
async def approve_report(report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DailyReport)
        .options(selectinload(DailyReport.versions))
        .where(DailyReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = ReportStatus.approved
    await db.commit()
    return ReportOut(
        id=report.id,
        report_date=report.report_date,
        status=report.status.value,
        included_article_count=len(report.included_article_ids),
        created_at=report.created_at,
        version_count=len(report.versions),
    )


@router.post("/generate", status_code=202)
async def trigger_report_generation(
    report_date: date,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger report generation for a given date."""
    from app.workers.tasks import generate_report_task
    task = generate_report_task.delay(report_date.isoformat())
    return {"task_id": task.id, "report_date": str(report_date), "status": "queued"}

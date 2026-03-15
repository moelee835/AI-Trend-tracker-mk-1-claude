"""Analytics and trend analysis endpoints."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.analytics_service import analyze_period, diff_reports

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/trends")
async def get_trends(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
):
    if (end_date - start_date).days > 90:
        raise HTTPException(status_code=400, detail="Date range must not exceed 90 days")
    return await analyze_period(db, start_date, end_date)


@router.get("/trends/last7")
async def trends_last_7(db: AsyncSession = Depends(get_db)):
    end = date.today()
    start = end - timedelta(days=6)
    return await analyze_period(db, start, end)


@router.get("/trends/last30")
async def trends_last_30(db: AsyncSession = Depends(get_db)):
    end = date.today()
    start = end - timedelta(days=29)
    return await analyze_period(db, start, end)


@router.get("/diff")
async def report_diff(
    report_id_a: int = Query(..., description="Earlier report ID"),
    report_id_b: int = Query(..., description="Later report ID"),
    db: AsyncSession = Depends(get_db),
):
    return await diff_reports(db, report_id_a, report_id_b)

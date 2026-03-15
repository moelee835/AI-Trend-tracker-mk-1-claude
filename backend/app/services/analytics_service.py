"""Period-based trend analysis across multiple reports."""
from __future__ import annotations

import collections
import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.generators.report_generator import generate_trend_analysis
from app.models.report import DailyReport, ReportVersion

logger = logging.getLogger(__name__)


async def analyze_period(
    db: AsyncSession,
    start_date: date,
    end_date: date,
) -> dict:
    """Aggregate keyword/category data across a date range."""
    result = await db.execute(
        select(DailyReport)
        .where(DailyReport.report_date >= start_date)
        .where(DailyReport.report_date <= end_date)
        .order_by(DailyReport.report_date)
    )
    reports = result.scalars().all()

    if not reports:
        return {"error": "no_reports", "message": "선택한 기간에 리포트가 없습니다."}

    # --- Basic aggregation (no LLM needed) ---
    keyword_counter: collections.Counter = collections.Counter()
    category_counter: collections.Counter = collections.Counter()
    date_keyword_map: dict[str, list[str]] = {}

    reports_data = []
    for report in reports:
        kw_summary = report.keyword_summary or {}
        keywords = kw_summary.get("keywords", [])
        keyword_counter.update(keywords)
        date_keyword_map[str(report.report_date)] = keywords

        reports_data.append({
            "report_date": str(report.report_date),
            "keyword_summary": kw_summary,
            "editorial_summary": kw_summary.get("editorial", ""),
        })

    # Trending: appeared in later half but not first half
    half = len(reports) // 2
    early_reports = reports[:half] if half else []
    late_reports = reports[half:]

    early_kws: set[str] = set()
    for r in early_reports:
        early_kws.update(r.keyword_summary.get("keywords", []))

    late_kws: set[str] = set()
    for r in late_reports:
        late_kws.update(r.keyword_summary.get("keywords", []))

    rising = sorted(late_kws - early_kws)
    declining = sorted(early_kws - late_kws)

    # LLM-powered trend summary
    try:
        period_label = f"{start_date} ~ {end_date}"
        llm_analysis = await generate_trend_analysis(reports_data, period_label)
    except Exception as exc:
        logger.warning("LLM trend analysis failed: %s", exc)
        llm_analysis = {"summary": "분석 중 오류가 발생했습니다.", "key_observations": []}

    return {
        "period": {"start": str(start_date), "end": str(end_date)},
        "total_reports": len(reports),
        "top_keywords": keyword_counter.most_common(20),
        "rising_keywords": rising[:15],
        "declining_keywords": declining[:15],
        "date_keyword_map": date_keyword_map,
        "llm_summary": llm_analysis.get("summary", ""),
        "key_observations": llm_analysis.get("key_observations", []),
        "vendor_mentions": llm_analysis.get("vendor_mentions", {}),
        "category_trend": llm_analysis.get("category_trend", {}),
    }


async def diff_reports(
    db: AsyncSession,
    report_id_a: int,
    report_id_b: int,
) -> dict:
    """Compare two report versions to show what changed."""
    async def get_keywords(report_id: int) -> set[str]:
        r = await db.get(DailyReport, report_id)
        if not r:
            return set()
        return set(r.keyword_summary.get("keywords", []))

    kw_a = await get_keywords(report_id_a)
    kw_b = await get_keywords(report_id_b)

    report_a = await db.get(DailyReport, report_id_a)
    report_b = await db.get(DailyReport, report_id_b)

    ids_a = set(report_a.included_article_ids if report_a else [])
    ids_b = set(report_b.included_article_ids if report_b else [])

    return {
        "new_keywords": sorted(kw_b - kw_a),
        "removed_keywords": sorted(kw_a - kw_b),
        "common_keywords": sorted(kw_a & kw_b),
        "new_article_ids": sorted(ids_b - ids_a),
        "removed_article_ids": sorted(ids_a - ids_b),
        "report_a_date": str(report_a.report_date) if report_a else None,
        "report_b_date": str(report_b.report_date) if report_b else None,
    }

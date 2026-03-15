"""Report creation, versioning, and retrieval."""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.generators.email_template import render_email_html
from app.generators.report_generator import generate_report
from app.models.article import Article, ArticleContent, ArticleScore
from app.models.report import DailyReport, ReportSection, ReportStatus, ReportVersion

logger = logging.getLogger(__name__)


async def get_or_create_daily_report(db: AsyncSession, report_date: date) -> DailyReport:
    result = await db.execute(
        select(DailyReport).where(DailyReport.report_date == report_date)
    )
    report = result.scalar_one_or_none()
    if not report:
        report = DailyReport(report_date=report_date)
        db.add(report)
        await db.flush()
    return report


async def generate_daily_report(db: AsyncSession, report_date: date) -> ReportVersion:
    """Fetch top articles for a date and generate a new report version."""
    # Query top-scored articles for the day
    articles_result = await db.execute(
        select(Article, ArticleScore, ArticleContent)
        .join(ArticleScore, Article.id == ArticleScore.article_id, isouter=True)
        .join(ArticleContent, Article.id == ArticleContent.article_id, isouter=True)
        .where(Article.is_duplicate == False)  # noqa: E712
        .where(Article.collected_at >= datetime.combine(report_date, datetime.min.time()).replace(tzinfo=timezone.utc))
        .order_by(ArticleScore.composite_score.desc())
        .limit(40)
    )
    rows = articles_result.fetchall()

    articles_data = []
    for article, score, content in rows:
        articles_data.append({
            "title": article.title,
            "canonical_url": article.canonical_url,
            "category": article.category.value if article.category else "other",
            "summary": content.summary_excerpt if content else None,
            "composite_score": score.composite_score if score else 0,
        })

    # Call LLM
    report_dict = await generate_report(report_date, articles_data)

    # Persist report
    daily_report = await get_or_create_daily_report(db, report_date)

    # Deactivate previous versions
    prev_versions_result = await db.execute(
        select(ReportVersion).where(
            ReportVersion.report_id == daily_report.id,
            ReportVersion.is_active == True,  # noqa: E712
        )
    )
    for v in prev_versions_result.scalars().all():
        v.is_active = False

    # Get next version number
    count_result = await db.execute(
        select(ReportVersion).where(ReportVersion.report_id == daily_report.id)
    )
    version_num = len(count_result.scalars().all()) + 1

    # Render HTML email
    html_content = render_email_html(
        subject_line=report_dict.get("subject_line", f"AI Trend | {report_date}"),
        report_date=report_date,
        sections=report_dict.get("sections", []),
        editorial_summary=report_dict.get("editorial_summary", ""),
        global_keywords=report_dict.get("keywords", []),
    )

    version = ReportVersion(
        report_id=daily_report.id,
        version_number=version_num,
        is_active=True,
        subject_line=report_dict.get("subject_line", f"AI Trend | {report_date}"),
        html_content=html_content,
        plain_content=report_dict.get("editorial_summary", ""),
        llm_model=report_dict.get("_model"),
        generation_tokens=report_dict.get("_tokens"),
    )
    db.add(version)
    await db.flush()

    # Save sections
    for idx, section in enumerate(report_dict.get("sections", [])):
        db.add(ReportSection(
            version_id=version.id,
            order=idx,
            title=section.get("title", ""),
            section_type=section.get("type", "unknown"),
            content_json=section,
            html_content=None,
        ))

    daily_report.status = ReportStatus.ready
    daily_report.included_article_ids = [r[0].id for r in rows]
    daily_report.keyword_summary = {
        "keywords": report_dict.get("keywords", []),
        "editorial": report_dict.get("editorial_summary", ""),
    }

    await db.commit()
    logger.info("Report generated: date=%s version=%d", report_date, version_num)
    return version

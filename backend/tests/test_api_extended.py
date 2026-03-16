"""Extended API tests for articles, reports, analytics, jobs, deliveries, and recipients."""
from __future__ import annotations

import pytest
from datetime import date, datetime, timezone

from app.models.source import Source, SourceType, PollStrategy
from app.models.article import Article, ArticleContent, ArticleScore, ArticleCategory
from app.models.recipient import Recipient
from app.models.report import DailyReport, ReportStatus, ReportVersion, EmailDelivery, DeliveryStatus
from app.models.job import JobExecutionLog, JobType, JobStatus


@pytest.fixture
async def source(db):
    s = Source(
        name="Test Source",
        source_type=SourceType.rss,
        base_url="https://example.com",
        feed_url="https://example.com/rss.xml",
        poll_strategy=PollStrategy.rss,
        enabled=True,
        parser_config={},
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@pytest.fixture
async def article(db, source):
    a = Article(
        source_id=source.id,
        title="Test Article: GPT-5 Released",
        canonical_url="https://example.com/articles/gpt5",
        author="Test Author",
        published_at=datetime(2026, 3, 17, 10, 0, tzinfo=timezone.utc),
        category=ArticleCategory.model_llm,
        is_duplicate=False,
        full_content_fetched=True,
        tags=["gpt", "openai"],
    )
    db.add(a)
    await db.flush()
    score = ArticleScore(
        article_id=a.id,
        importance_score=0.8,
        novelty_score=0.7,
        developer_relevance_score=0.9,
        composite_score=0.82,
        score_details={},
    )
    db.add(score)
    content = ArticleContent(
        article_id=a.id,
        raw_html="<p>Test content</p>",
        cleaned_text="Test content",
        summary_excerpt="Summary excerpt",
    )
    db.add(content)
    await db.commit()
    await db.refresh(a)
    return a


@pytest.fixture
async def report(db):
    r = DailyReport(
        report_date=date.today(),
        status=ReportStatus.ready,
        included_article_ids=[1, 2, 3],
        keyword_summary={"keywords": ["gpt", "claude", "llm"], "editorial": "Good day"},
    )
    db.add(r)
    await db.flush()
    v = ReportVersion(
        report_id=r.id,
        version_number=1,
        is_active=True,
        subject_line="AI Trend Newsletter 2026-03-17",
        html_content="<html><body>Newsletter content</body></html>",
        llm_model="gpt-4o",
        generation_tokens=1000,
        edited_by_operator=False,
    )
    db.add(v)
    await db.commit()
    await db.refresh(r)
    return r


@pytest.fixture
async def recipient(db):
    r = Recipient(email="user@example.com", name="Test User", subscribed=True, tags=["dev"])
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


@pytest.fixture
async def job_log(db):
    log = JobExecutionLog(
        job_type=JobType.collect,
        status=JobStatus.success,
        triggered_by="manual",
        result_summary={"articles_collected": 10},
        started_at=datetime(2026, 3, 17, 9, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 3, 17, 9, 1, tzinfo=timezone.utc),
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


# ─── Articles API ────────────────────────────────────────────────────────────

class TestArticlesAPI:
    async def test_list_articles_empty(self, client):
        r = await client.get("/api/v1/articles/")
        assert r.status_code == 200
        assert r.json() == []

    async def test_list_articles_with_data(self, client, article):
        r = await client.get("/api/v1/articles/")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Article: GPT-5 Released"
        assert data[0]["composite_score"] == pytest.approx(0.82)
        assert data[0]["summary_excerpt"] == "Summary excerpt"

    async def test_list_articles_filter_by_category(self, client, article):
        r = await client.get("/api/v1/articles/?category=model_llm")
        assert r.status_code == 200
        assert len(r.json()) == 1

        r2 = await client.get("/api/v1/articles/?category=ai_agent")
        assert r2.status_code == 200
        assert len(r2.json()) == 0

    async def test_list_articles_filter_by_duplicate(self, client, article):
        r = await client.get("/api/v1/articles/?is_duplicate=false")
        assert r.status_code == 200
        assert len(r.json()) == 1

        r2 = await client.get("/api/v1/articles/?is_duplicate=true")
        assert r2.status_code == 200
        assert len(r2.json()) == 0

    async def test_list_articles_filter_by_source(self, client, article, source):
        r = await client.get(f"/api/v1/articles/?source_id={source.id}")
        assert r.status_code == 200
        assert len(r.json()) == 1

        r2 = await client.get("/api/v1/articles/?source_id=9999")
        assert r2.status_code == 200
        assert len(r2.json()) == 0

    async def test_list_articles_pagination(self, client, article):
        r = await client.get("/api/v1/articles/?limit=10&offset=0")
        assert r.status_code == 200
        assert len(r.json()) == 1

        r2 = await client.get("/api/v1/articles/?limit=10&offset=10")
        assert r2.status_code == 200
        assert len(r2.json()) == 0

    async def test_get_article_detail(self, client, article):
        r = await client.get(f"/api/v1/articles/{article.id}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == article.id
        assert data["title"] == "Test Article: GPT-5 Released"
        assert data["cleaned_text"] == "Test content"
        assert data["tags"] == ["gpt", "openai"]

    async def test_get_article_not_found(self, client):
        r = await client.get("/api/v1/articles/9999")
        assert r.status_code == 404


# ─── Reports API ─────────────────────────────────────────────────────────────

class TestReportsAPI:
    async def test_list_reports_empty(self, client):
        r = await client.get("/api/v1/reports/")
        assert r.status_code == 200
        assert r.json() == []

    async def test_list_reports_with_data(self, client, report):
        r = await client.get("/api/v1/reports/")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["status"] == "ready"
        assert data[0]["included_article_count"] == 3
        assert data[0]["version_count"] == 1

    async def test_get_report_by_id(self, client, report):
        r = await client.get(f"/api/v1/reports/{report.id}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == report.id
        assert data["status"] == "ready"

    async def test_get_report_not_found(self, client):
        r = await client.get("/api/v1/reports/9999")
        assert r.status_code == 404

    async def test_approve_report(self, client, report):
        r = await client.post(f"/api/v1/reports/{report.id}/approve")
        assert r.status_code == 200
        assert r.json()["status"] == "approved"

    async def test_approve_report_not_found(self, client):
        r = await client.post("/api/v1/reports/9999/approve")
        assert r.status_code == 404

    async def test_list_report_versions(self, client, report):
        r = await client.get(f"/api/v1/reports/{report.id}/versions")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["subject_line"] == "AI Trend Newsletter 2026-03-17"
        assert data[0]["is_active"] is True

    async def test_get_version_html(self, client, report, db):
        versions = await db.execute(
            __import__("sqlalchemy", fromlist=["select"]).select(ReportVersion).where(
                ReportVersion.report_id == report.id
            )
        )
        version = versions.scalar_one()
        r = await client.get(f"/api/v1/reports/{report.id}/versions/{version.id}/html")
        assert r.status_code == 200
        assert "Newsletter content" in r.text

    async def test_get_version_html_not_found(self, client, report):
        r = await client.get(f"/api/v1/reports/{report.id}/versions/9999/html")
        assert r.status_code == 404

    async def test_edit_version_content(self, client, report, db):
        from sqlalchemy import select as sa_select
        versions = await db.execute(sa_select(ReportVersion).where(ReportVersion.report_id == report.id))
        version = versions.scalar_one()
        r = await client.patch(
            f"/api/v1/reports/{report.id}/versions/{version.id}",
            json={"html_content": "<html><body>Updated content</body></html>", "subject_line": "New Subject"},
        )
        assert r.status_code == 200
        assert r.json()["edited_by_operator"] is True

    async def test_list_reports_filter_by_status(self, client, report):
        r = await client.get("/api/v1/reports/?status=ready")
        assert r.status_code == 200
        assert len(r.json()) == 1

        r2 = await client.get("/api/v1/reports/?status=sent")
        assert r2.status_code == 200
        assert len(r2.json()) == 0


# ─── Recipients API (extended) ────────────────────────────────────────────────

class TestRecipientsAPIExtended:
    async def test_list_recipients_empty(self, client):
        r = await client.get("/api/v1/recipients/")
        assert r.status_code == 200
        assert r.json() == []

    async def test_list_recipients_with_data(self, client, recipient):
        r = await client.get("/api/v1/recipients/")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["email"] == "user@example.com"

    async def test_list_recipients_filter_subscribed(self, client, recipient):
        r = await client.get("/api/v1/recipients/?subscribed=true")
        assert r.status_code == 200
        assert len(r.json()) == 1

        r2 = await client.get("/api/v1/recipients/?subscribed=false")
        assert r2.status_code == 200
        assert len(r2.json()) == 0

    async def test_list_recipients_filter_by_tag(self, client, recipient):
        r = await client.get("/api/v1/recipients/?tag=dev")
        assert r.status_code == 200
        assert len(r.json()) == 1

        r2 = await client.get("/api/v1/recipients/?tag=nonexistent")
        assert r2.status_code == 200
        assert len(r2.json()) == 0

    async def test_get_recipient_by_id(self, client, recipient):
        r = await client.get(f"/api/v1/recipients/{recipient.id}")
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "user@example.com"
        assert data["name"] == "Test User"

    async def test_get_recipient_not_found(self, client):
        r = await client.get("/api/v1/recipients/9999")
        assert r.status_code == 404

    async def test_update_recipient(self, client, recipient):
        r = await client.patch(
            f"/api/v1/recipients/{recipient.id}",
            json={"name": "Updated Name", "subscribed": False},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Updated Name"
        assert data["subscribed"] is False

    async def test_update_recipient_not_found(self, client):
        r = await client.patch("/api/v1/recipients/9999", json={"name": "X"})
        assert r.status_code == 404

    async def test_csv_import(self, client):
        csv_content = b"email,name\ntest1@example.com,User One\ntest2@example.com,User Two\n"
        r = await client.post(
            "/api/v1/recipients/import/csv",
            files={"file": ("recipients.csv", csv_content, "text/csv")},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["created"] == 2
        assert data["skipped"] == 0

    async def test_csv_import_skips_duplicates(self, client, recipient):
        csv_content = b"email,name\nuser@example.com,Duplicate User\nnew@example.com,New User\n"
        r = await client.post(
            "/api/v1/recipients/import/csv",
            files={"file": ("recipients.csv", csv_content, "text/csv")},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["created"] == 1
        assert data["skipped"] == 1


# ─── Analytics API ────────────────────────────────────────────────────────────

class TestAnalyticsAPI:
    async def test_trends_last7_empty(self, client):
        r = await client.get("/api/v1/analytics/trends/last7")
        assert r.status_code == 200
        data = r.json()
        assert "error" in data
        assert data["error"] == "no_reports"

    async def test_trends_last7_with_data(self, client, report):
        r = await client.get("/api/v1/analytics/trends/last7")
        assert r.status_code == 200
        data = r.json()
        assert "top_keywords" in data
        assert "rising_keywords" in data

    async def test_trends_custom_range(self, client, report):
        r = await client.get("/api/v1/analytics/trends?start_date=2026-03-10&end_date=2026-03-17")
        assert r.status_code == 200

    async def test_trends_range_too_large(self, client):
        r = await client.get("/api/v1/analytics/trends?start_date=2026-01-01&end_date=2026-05-01")
        assert r.status_code == 400

    async def test_diff_reports_no_data(self, client):
        r = await client.get("/api/v1/analytics/diff?report_id_a=1&report_id_b=2")
        assert r.status_code == 200
        data = r.json()
        assert "new_keywords" in data
        assert "removed_keywords" in data

    async def test_diff_reports_with_data(self, client, db):
        r1 = DailyReport(
            report_date=date(2026, 3, 16),
            status=ReportStatus.sent,
            included_article_ids=[1, 2],
            keyword_summary={"keywords": ["gpt", "claude"]},
        )
        r2 = DailyReport(
            report_date=date(2026, 3, 17),
            status=ReportStatus.ready,
            included_article_ids=[2, 3],
            keyword_summary={"keywords": ["claude", "gemini"]},
        )
        db.add(r1)
        db.add(r2)
        await db.commit()

        r = await client.get(f"/api/v1/analytics/diff?report_id_a={r1.id}&report_id_b={r2.id}")
        assert r.status_code == 200
        data = r.json()
        assert "gemini" in data["new_keywords"]
        assert "gpt" in data["removed_keywords"]
        assert "claude" in data["common_keywords"]


# ─── Jobs API ────────────────────────────────────────────────────────────────

class TestJobsAPI:
    async def test_list_logs_empty(self, client):
        r = await client.get("/api/v1/jobs/logs")
        assert r.status_code == 200
        assert r.json() == []

    async def test_list_logs_with_data(self, client, job_log):
        r = await client.get("/api/v1/jobs/logs")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["job_type"] == "collect"
        assert data[0]["status"] == "success"
        assert data[0]["duration_seconds"] == pytest.approx(60.0)

    async def test_list_logs_filter_by_type(self, client, job_log):
        r = await client.get("/api/v1/jobs/logs?job_type=collect")
        assert r.status_code == 200
        assert len(r.json()) == 1

        r2 = await client.get("/api/v1/jobs/logs?job_type=generate_report")
        assert r2.status_code == 200
        assert len(r2.json()) == 0


# ─── Deliveries API ──────────────────────────────────────────────────────────

class TestDeliveriesAPI:
    async def test_list_deliveries_empty(self, client):
        r = await client.get("/api/v1/deliveries/")
        assert r.status_code == 200
        assert r.json() == []

    async def _create_delivery(self, db, report, recipient):
        from sqlalchemy import select as sa_select
        versions = await db.execute(sa_select(ReportVersion).where(ReportVersion.report_id == report.id))
        version = versions.scalar_one()
        delivery = EmailDelivery(
            report_id=report.id,
            version_id=version.id,
            recipient_id=recipient.id,
            status=DeliveryStatus.sent,
            is_test=False,
            sent_at=datetime(2026, 3, 17, 9, 0, tzinfo=timezone.utc),
        )
        db.add(delivery)
        await db.commit()
        return delivery

    async def test_list_deliveries_with_data(self, client, report, recipient, db):
        await self._create_delivery(db, report, recipient)
        r = await client.get("/api/v1/deliveries/")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["status"] == "sent"

    async def test_list_deliveries_filter_by_report(self, client, report, recipient, db):
        await self._create_delivery(db, report, recipient)
        r = await client.get(f"/api/v1/deliveries/?report_id={report.id}")
        assert r.status_code == 200
        assert len(r.json()) == 1

        r2 = await client.get("/api/v1/deliveries/?report_id=9999")
        assert r2.status_code == 200
        assert len(r2.json()) == 0


# ─── Dashboard API (extended) ────────────────────────────────────────────────

class TestDashboardAPIExtended:
    async def test_dashboard_with_data(self, client, article, report):
        r = await client.get("/api/v1/dashboard/summary")
        assert r.status_code == 200
        data = r.json()
        assert "today" in data
        assert "articles_today" in data
        assert "article_trend_7d" in data
        assert len(data["article_trend_7d"]) == 7
        assert "recent_jobs" in data

    async def test_dashboard_shows_report_status(self, client, db):
        r = DailyReport(
            report_date=date.today(),
            status=ReportStatus.approved,
            included_article_ids=[],
            keyword_summary={},
        )
        db.add(r)
        await db.commit()

        resp = await client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_status"] == "approved"
        assert data["report_id"] == r.id

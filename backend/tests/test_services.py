"""Unit tests for services and generators using mocks."""
from __future__ import annotations

import pytest
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.source import Source, SourceType, PollStrategy
from app.models.article import Article, ArticleContent, ArticleScore, ArticleCategory
from app.models.report import DailyReport, ReportStatus, ReportVersion
from app.services.analytics_service import analyze_period, diff_reports
from app.services.report_service import get_or_create_daily_report, generate_daily_report
from app.generators.email_template import render_email_html


# ─── Analytics Service ────────────────────────────────────────────────────────

class TestAnalyticsService:
    async def test_analyze_period_no_reports(self, db):
        result = await analyze_period(db, date(2026, 1, 1), date(2026, 1, 7))
        assert result["error"] == "no_reports"

    async def test_analyze_period_with_reports(self, db):
        r1 = DailyReport(
            report_date=date(2026, 3, 15),
            status=ReportStatus.sent,
            included_article_ids=[1],
            keyword_summary={"keywords": ["gpt", "claude"], "editorial": "Day 1"},
        )
        r2 = DailyReport(
            report_date=date(2026, 3, 16),
            status=ReportStatus.sent,
            included_article_ids=[2],
            keyword_summary={"keywords": ["claude", "gemini"], "editorial": "Day 2"},
        )
        db.add(r1)
        db.add(r2)
        await db.commit()

        with patch("app.services.analytics_service.generate_trend_analysis", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "summary": "Test summary",
                "key_observations": ["obs1"],
                "vendor_mentions": {},
                "category_trend": {},
            }
            result = await analyze_period(db, date(2026, 3, 14), date(2026, 3, 17))

        assert result["total_reports"] == 2
        assert "top_keywords" in result
        assert "rising_keywords" in result
        assert result["llm_summary"] == "Test summary"
        # claude appears in both, gpt only in first (early), gemini only in second (late)
        assert "gemini" in result["rising_keywords"]
        assert "gpt" in result["declining_keywords"]

    async def test_analyze_period_llm_failure(self, db):
        r = DailyReport(
            report_date=date(2026, 3, 17),
            status=ReportStatus.sent,
            included_article_ids=[],
            keyword_summary={"keywords": ["ai"], "editorial": ""},
        )
        db.add(r)
        await db.commit()

        with patch("app.services.analytics_service.generate_trend_analysis", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("LLM unavailable")
            result = await analyze_period(db, date(2026, 3, 17), date(2026, 3, 17))

        # Should degrade gracefully
        assert "error" not in result
        assert result["llm_summary"] == "분석 중 오류가 발생했습니다."

    async def test_diff_reports_nonexistent(self, db):
        result = await diff_reports(db, 9999, 8888)
        assert result["new_keywords"] == []
        assert result["removed_keywords"] == []
        assert result["report_a_date"] is None
        assert result["report_b_date"] is None

    async def test_diff_reports_with_data(self, db):
        r1 = DailyReport(
            report_date=date(2026, 3, 15),
            status=ReportStatus.sent,
            included_article_ids=[1, 2],
            keyword_summary={"keywords": ["gpt", "claude"]},
        )
        r2 = DailyReport(
            report_date=date(2026, 3, 16),
            status=ReportStatus.sent,
            included_article_ids=[2, 3],
            keyword_summary={"keywords": ["claude", "gemini"]},
        )
        db.add(r1)
        db.add(r2)
        await db.commit()

        result = await diff_reports(db, r1.id, r2.id)
        assert "gemini" in result["new_keywords"]
        assert "gpt" in result["removed_keywords"]
        assert "claude" in result["common_keywords"]
        assert 3 in result["new_article_ids"]
        assert 1 in result["removed_article_ids"]
        assert str(r1.report_date) == result["report_a_date"]
        assert str(r2.report_date) == result["report_b_date"]


# ─── Report Service ───────────────────────────────────────────────────────────

class TestReportService:
    async def test_get_or_create_daily_report_creates_new(self, db):
        report = await get_or_create_daily_report(db, date(2026, 3, 17))
        assert report.report_date == date(2026, 3, 17)
        assert report.id is not None
        await db.commit()

    async def test_get_or_create_daily_report_returns_existing(self, db):
        r = DailyReport(
            report_date=date(2026, 3, 17),
            status=ReportStatus.draft,
            included_article_ids=[],
            keyword_summary={},
        )
        db.add(r)
        await db.commit()

        report = await get_or_create_daily_report(db, date(2026, 3, 17))
        assert report.id == r.id

    async def test_generate_daily_report_with_articles(self, db):
        # Create source and articles
        source = Source(
            name="Test",
            source_type=SourceType.rss,
            base_url="https://ex.com",
            poll_strategy=PollStrategy.rss,
            parser_config={},
        )
        db.add(source)
        await db.flush()

        report_date = date(2026, 3, 17)
        collected_at = datetime(2026, 3, 17, 9, 0, tzinfo=timezone.utc)

        article = Article(
            source_id=source.id,
            title="GPT-5 Released",
            canonical_url="https://ex.com/gpt5",
            category=ArticleCategory.model_llm,
            is_duplicate=False,
            full_content_fetched=True,
            collected_at=collected_at,
            tags=[],
        )
        db.add(article)
        await db.flush()

        score = ArticleScore(
            article_id=article.id,
            importance_score=0.9,
            novelty_score=0.8,
            developer_relevance_score=0.9,
            composite_score=0.87,
            score_details={},
        )
        db.add(score)
        content = ArticleContent(
            article_id=article.id,
            summary_excerpt="GPT-5 is out",
        )
        db.add(content)
        await db.commit()

        mock_report_dict = {
            "subject_line": "AI Trend | 2026-03-17 - GPT-5",
            "sections": [
                {
                    "type": "top_issues",
                    "title": "Top Issues",
                    "items": [
                        {
                            "headline": "GPT-5 Released",
                            "why_important": "Major update",
                            "developer_point": "Check API changes",
                            "keywords": ["gpt"],
                            "source_url": "https://ex.com/gpt5",
                            "source_title": "GPT-5 Released",
                            "importance": "high",
                        }
                    ],
                }
            ],
            "editorial_summary": "Big day for AI",
            "keywords": ["gpt", "openai"],
            "_model": "gpt-4o",
            "_tokens": 500,
        }

        with patch("app.services.report_service.generate_report", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_report_dict
            version = await generate_daily_report(db, report_date)

        assert version.subject_line == "AI Trend | 2026-03-17 - GPT-5"
        assert version.llm_model == "gpt-4o"
        assert version.generation_tokens == 500
        assert "<!DOCTYPE html>" in version.html_content

    async def test_generate_daily_report_no_articles(self, db):
        report_date = date(2026, 3, 17)
        mock_report_dict = {
            "subject_line": "AI Trend | 2026-03-17",
            "sections": [],
            "editorial_summary": "Quiet day",
            "keywords": [],
            "_model": "gpt-4o",
            "_tokens": 100,
        }

        with patch("app.services.report_service.generate_report", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_report_dict
            version = await generate_daily_report(db, report_date)

        assert version is not None
        assert version.version_number == 1


# ─── Email Template ──────────────────────────────────────────────────────────

class TestEmailTemplate:
    def test_render_with_all_sections(self):
        html = render_email_html(
            subject_line="Test",
            report_date=date(2026, 3, 17),
            sections=[
                {
                    "title": "Top Issues",
                    "type": "top_issues",
                    "items": [
                        {
                            "headline": "Big News",
                            "why_important": "Important",
                            "developer_point": "Dev note",
                            "keywords": ["ai", "ml"],
                            "source_url": "https://example.com",
                            "source_title": "Example",
                            "importance": "high",
                        }
                    ],
                },
                {
                    "title": "Tech Changes",
                    "type": "tech_changes",
                    "items": [
                        {
                            "headline": "New Framework",
                            "why_important": "Faster",
                            "developer_point": "Try it",
                            "keywords": ["framework"],
                            "source_url": "https://example.com/2",
                            "source_title": "Framework News",
                            "importance": "medium",
                        }
                    ],
                },
            ],
            editorial_summary="Great week for AI.",
            global_keywords=["ai", "ml", "llm"],
        )
        assert "<!DOCTYPE html>" in html
        assert "Big News" in html
        assert "New Framework" in html
        assert "Great week for AI." in html

    def test_render_minimal(self):
        html = render_email_html(
            subject_line="Minimal",
            report_date=date(2026, 1, 1),
            sections=[],
            editorial_summary=None,
            global_keywords=[],
        )
        assert "<!DOCTYPE html>" in html

    def test_render_keywords_appear_in_output(self):
        html = render_email_html(
            subject_line="KW Test",
            report_date=date(2026, 3, 17),
            sections=[],
            global_keywords=["python", "rust", "golang"],
        )
        assert "python" in html


# ─── Collectors (unit level, mocked) ─────────────────────────────────────────

class TestDeduplicatorEdgeCases:
    def test_empty_title_simhash(self):
        from app.analyzers.deduplicator import title_simhash, hamming_distance
        h = title_simhash("")
        assert len(h) == 16
        # Empty titles should match each other
        h2 = title_simhash("")
        assert hamming_distance(h, h2) == 0

    def test_hamming_distance_identical(self):
        from app.analyzers.deduplicator import hamming_distance
        assert hamming_distance("aaaa0000aaaa0000", "aaaa0000aaaa0000") == 0

    def test_hamming_distance_all_different(self):
        from app.analyzers.deduplicator import hamming_distance
        # All bits differ: 0000... vs ffff...
        result = hamming_distance("0" * 16, "f" * 16)
        assert result == 64

    def test_is_duplicate_empty_list(self):
        from app.analyzers.deduplicator import title_simhash, is_duplicate_title
        h = title_simhash("some title")
        assert not is_duplicate_title(h, [])


class TestScorerEdgeCases:
    def test_score_with_none_text(self):
        from app.analyzers.scorer import score_article
        result = score_article("Some title", None)
        assert "composite_score" in result
        assert 0.0 <= result["composite_score"] <= 1.0

    def test_score_with_empty_strings(self):
        from app.analyzers.scorer import score_article
        result = score_article("", "")
        assert result["category"] == "other"
        assert result["composite_score"] == 0.0

    def test_all_categories_detectable(self):
        from app.analyzers.scorer import score_article
        test_cases = [
            ("new agent autonomous tool use workflow", "ai_agent"),
            ("cuda gpu triton vllm serving inference", "infra_serving"),
            ("github open source pytorch hugging face", "opensource_framework"),
            ("launch release announce available beta", "product_launch"),
            ("arxiv paper benchmark dataset evaluation", "research_paper"),
            ("safety alignment bias regulation policy", "security_policy"),
            ("ide plugin extension copilot cursor code", "dev_tools"),
        ]
        for text, expected_cat in test_cases:
            result = score_article(text, "")
            assert result["category"] == expected_cat, f"Expected {expected_cat} for '{text}', got {result['category']}"

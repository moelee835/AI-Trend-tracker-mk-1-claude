"""Unit tests for collectors and report generator (with mocks)."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.collectors.base import BaseCollector, RawArticle
from app.collectors.rss_collector import RssCollector
from app.collectors.api_collector import NewsApiCollector
from app.collectors import get_collector


# ─── BaseCollector ────────────────────────────────────────────────────────────

class TestBaseCollector:
    def test_normalize_url_strips_utm(self):
        class ConcreteCollector(BaseCollector):
            async def collect(self):
                return []

        collector = ConcreteCollector(source_id=1, config={})
        raw = "https://example.com/article?utm_source=twitter&utm_medium=social&id=123"
        result = collector._normalize_url(raw)
        assert "utm_source" not in result
        assert "id=123" in result

    def test_normalize_url_strips_fragment(self):
        class ConcreteCollector(BaseCollector):
            async def collect(self):
                return []

        collector = ConcreteCollector(source_id=1, config={})
        raw = "https://example.com/article#section-1"
        result = collector._normalize_url(raw)
        assert "#" not in result
        assert "section-1" not in result

    def test_raw_article_defaults(self):
        article = RawArticle(title="Test", url="https://ex.com", source_id=1)
        assert article.published_at is None
        assert article.author is None
        assert article.summary is None
        assert article.tags == []


# ─── RssCollector ─────────────────────────────────────────────────────────────

class TestRssCollector:
    async def test_collect_no_feed_url_returns_empty(self):
        collector = RssCollector(source_id=1, config={})
        result = await collector.collect()
        assert result == []

    async def test_collect_success(self):
        rss_content = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Test Feed</title>
            <item>
              <title>GPT-5 Released</title>
              <link>https://example.com/gpt5</link>
              <description>OpenAI releases GPT-5</description>
              <author>OpenAI</author>
            </item>
            <item>
              <title>New LLM Benchmark</title>
              <link>https://example.com/bench</link>
              <description>MMLU scores improved</description>
            </item>
          </channel>
        </rss>"""

        mock_response = MagicMock()
        mock_response.text = rss_content
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)

            collector = RssCollector(source_id=1, config={"feed_url": "https://example.com/rss"})
            articles = await collector.collect()

        assert len(articles) == 2
        assert articles[0].title == "GPT-5 Released"
        assert articles[0].source_id == 1
        assert "example.com/gpt5" in articles[0].url

    async def test_collect_http_error_raises(self):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            collector = RssCollector(source_id=1, config={"feed_url": "https://example.com/rss"})
            with pytest.raises(httpx.ConnectError):
                await collector.collect()

    async def test_collect_skips_entries_without_url(self):
        rss_content = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Test Feed</title>
            <item>
              <title>No URL Article</title>
              <description>This has no link</description>
            </item>
            <item>
              <title>Has URL</title>
              <link>https://example.com/article</link>
            </item>
          </channel>
        </rss>"""

        mock_response = MagicMock()
        mock_response.text = rss_content
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)

            collector = RssCollector(source_id=1, config={"feed_url": "https://example.com/rss"})
            articles = await collector.collect()

        assert len(articles) == 1
        assert articles[0].title == "Has URL"

    def test_parse_date_from_published_parsed(self):
        collector = RssCollector(source_id=1, config={})
        entry = {"published_parsed": (2026, 3, 17, 10, 0, 0, 0, 0, 0)}
        dt = collector._parse_date(entry)
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 3

    def test_parse_date_missing_returns_none(self):
        collector = RssCollector(source_id=1, config={})
        dt = collector._parse_date({})
        assert dt is None

    def test_clean_html(self):
        collector = RssCollector(source_id=1, config={})
        html = "<p>Hello <b>World</b></p><script>alert('xss')</script>"
        result = collector._clean_html(html)
        assert "<p>" not in result
        assert "Hello" in result
        assert "World" in result


# ─── NewsApiCollector ─────────────────────────────────────────────────────────

class TestNewsApiCollector:
    async def test_collect_no_api_key_returns_empty(self):
        with patch("app.collectors.api_collector.settings") as mock_settings:
            mock_settings.NEWS_API_KEY = ""
            collector = NewsApiCollector(source_id=1, config={})
            result = await collector.collect()
        assert result == []

    async def test_collect_success(self):
        api_response = {
            "articles": [
                {
                    "title": "AI Advances in 2026",
                    "url": "https://example.com/ai-advances",
                    "author": "Jane Doe",
                    "publishedAt": "2026-03-17T10:00:00Z",
                    "description": "AI made huge progress",
                    "source": {"name": "TechCrunch"},
                },
                {
                    "title": "[Removed]",
                    "url": "https://example.com/removed",
                    "author": None,
                    "publishedAt": None,
                    "description": "",
                    "source": {"name": "Unknown"},
                },
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = api_response
        mock_response.raise_for_status = MagicMock()

        with patch("app.collectors.api_collector.settings") as mock_settings:
            mock_settings.NEWS_API_KEY = "test-key-123"
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)
                mock_client.get = AsyncMock(return_value=mock_response)

                collector = NewsApiCollector(source_id=2, config={})
                articles = await collector.collect()

        assert len(articles) == 1  # [Removed] should be filtered
        assert articles[0].title == "AI Advances in 2026"
        assert articles[0].source_id == 2


# ─── Collector Factory ─────────────────────────────────────────────────────────

class TestCollectorFactory:
    def test_get_rss_collector(self):
        collector = get_collector("rss", source_id=1, config={"feed_url": "https://ex.com/rss"})
        assert isinstance(collector, RssCollector)

    def test_get_api_collector(self):
        collector = get_collector("api", source_id=2, config={})
        assert isinstance(collector, NewsApiCollector)

    def test_get_unknown_collector_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown poll_strategy"):
            get_collector("playwright", source_id=3, config={})


# ─── Report Generator ─────────────────────────────────────────────────────────

class TestReportGenerator:
    async def test_generate_report_with_api_key(self):
        from app.generators.report_generator import generate_report
        from datetime import date

        mock_result = {
            "subject_line": "AI Trend | 2026-03-17",
            "sections": [],
            "editorial_summary": "Test summary",
            "keywords": ["gpt"],
        }
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='{"subject_line":"AI Trend | 2026-03-17","sections":[],"editorial_summary":"Test","keywords":["gpt"]}'))]
        mock_response.usage = MagicMock(total_tokens=500, model="gpt-4o")

        with patch("app.generators.report_generator.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "sk-test"
            mock_settings.LLM_MODEL = "gpt-4o"
            mock_settings.LLM_MAX_TOKENS = 4096
            with patch("app.generators.report_generator._make_client") as mock_make_client:
                mock_openai = MagicMock()
                mock_make_client.return_value = mock_openai
                mock_openai.chat = MagicMock()
                mock_openai.chat.completions = MagicMock()
                mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)

                result = await generate_report(date(2026, 3, 17), [])

        assert "subject_line" in result
        assert "_tokens" in result

    async def test_generate_report_no_api_key_uses_placeholder(self):
        from app.generators.report_generator import generate_report
        from datetime import date

        with patch("app.generators.report_generator.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.LLM_MODEL = "gpt-4o"
            mock_settings.LLM_MAX_TOKENS = 4096

            result = await generate_report(date(2026, 3, 17), [])

        assert result["_model"] == "placeholder"
        assert "_tokens" in result

    def test_strip_fences_with_json_fences(self):
        from app.generators.report_generator import _strip_fences
        raw = '```json\n{"key": "value"}\n```'
        result = _strip_fences(raw)
        assert result == '{"key": "value"}'

    def test_strip_fences_without_fences(self):
        from app.generators.report_generator import _strip_fences
        raw = '{"key": "value"}'
        result = _strip_fences(raw)
        assert result == '{"key": "value"}'

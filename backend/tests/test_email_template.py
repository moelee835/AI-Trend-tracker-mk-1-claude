"""Tests for email HTML template rendering."""
from datetime import date

from app.generators.email_template import render_email_html


def test_render_email_html_basic():
    html = render_email_html(
        subject_line="Test Newsletter",
        report_date=date(2024, 1, 15),
        sections=[
            {
                "title": "🔥 오늘의 AI 이슈",
                "type": "top_issues",
                "items": [
                    {
                        "headline": "GPT-5 출시",
                        "why_important": "성능 향상",
                        "developer_point": "API 변경 확인 필요",
                        "keywords": ["gpt", "openai"],
                        "source_url": "https://openai.com",
                        "source_title": "OpenAI Blog",
                        "importance": "high",
                    }
                ],
            }
        ],
        editorial_summary="오늘 AI 생태계에 큰 변화가 있었습니다.",
        global_keywords=["gpt", "llm", "agent"],
    )

    assert "<!DOCTYPE html>" in html
    assert "GPT-5 출시" in html
    assert "오늘 AI 생태계에 큰 변화가 있었습니다." in html
    assert "gpt" in html
    assert "2024-01-15" in html


def test_render_email_html_empty_sections():
    html = render_email_html(
        subject_line="Empty Report",
        report_date=date(2024, 1, 1),
        sections=[],
    )
    assert "<!DOCTYPE html>" in html
    assert "Empty Report" in html

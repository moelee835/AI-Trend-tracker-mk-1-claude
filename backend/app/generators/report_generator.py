"""LLM-based report generation using Anthropic Claude."""
from __future__ import annotations

import json
import logging
from datetime import date

import anthropic

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


REPORT_SYSTEM_PROMPT = """당신은 AI 기술 트렌드를 개발자 관점에서 큐레이션하는 전문가입니다.
다음 원칙을 반드시 따르세요:
1. 단순 요약이 아닌 "개발자가 왜 신경써야 하는가"를 중심으로 작성
2. 기술적 정확성을 유지하면서 한국어로 명료하게 작성
3. 과장 표현 지양, 실질적 영향 중심
4. 반드시 JSON 형식으로 응답"""

REPORT_USER_TEMPLATE = """오늘({date}) 수집된 AI 관련 기사들입니다.

기사 목록:
{articles_json}

다음 JSON 구조로 뉴스레터 리포트를 생성해주세요:

{{
  "subject_line": "📡 AI Trend | {date} - [핵심 이슈 한 줄]",
  "sections": [
    {{
      "type": "top_issues",
      "title": "🔥 오늘 가장 중요한 AI 이슈",
      "items": [
        {{
          "headline": "한 줄 요약",
          "why_important": "왜 중요한가",
          "developer_point": "개발자가 주목할 포인트",
          "keywords": ["키워드1", "키워드2"],
          "source_url": "URL",
          "source_title": "원문 제목",
          "importance": "high|medium"
        }}
      ]
    }},
    {{
      "type": "tech_changes",
      "title": "💡 개발자가 꼭 알아야 할 기술 변화",
      "items": [...]
    }},
    {{
      "type": "new_services",
      "title": "🚀 새롭게 등장한 서비스·에이전트·오픈소스",
      "items": [...]
    }}
  ],
  "editorial_summary": "오늘 AI 생태계의 전반적인 흐름을 2-3문장으로 요약",
  "keywords": ["오늘 가장 많이 언급된 키워드 목록 (최대 15개)"]
}}

상위 10-15개의 중요한 기사만 선별하고, 유사한 기사는 묶어서 하나로 처리하세요.
각 섹션에 최소 2개, 최대 6개 아이템.
반드시 유효한 JSON만 응답하세요."""


async def generate_report(report_date: date, articles: list[dict]) -> dict:
    """Call Claude API and return structured report dict."""
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set — returning placeholder report")
        return _placeholder_report(report_date)

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Prepare article summaries for the prompt (truncate long text)
    article_summaries = []
    for a in articles[:30]:  # cap at 30 articles
        article_summaries.append({
            "title": a.get("title", ""),
            "url": a.get("canonical_url", ""),
            "category": a.get("category", "other"),
            "summary": (a.get("summary") or "")[:400],
            "composite_score": a.get("composite_score", 0),
        })

    articles_json = json.dumps(article_summaries, ensure_ascii=False, indent=2)
    user_message = REPORT_USER_TEMPLATE.format(
        date=report_date.strftime("%Y-%m-%d"),
        articles_json=articles_json,
    )

    logger.info("Generating report via Claude for date=%s with %d articles", report_date, len(articles))

    try:
        response = await client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=settings.LLM_MAX_TOKENS,
            system=REPORT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text
        # Strip markdown code fences if present
        if raw.strip().startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        result["_tokens"] = response.usage.input_tokens + response.usage.output_tokens
        result["_model"] = settings.LLM_MODEL
        return result
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse LLM JSON response: %s", exc)
        raise
    except Exception as exc:
        logger.error("Claude API error: %s", exc)
        raise


async def generate_trend_analysis(reports: list[dict], period_label: str) -> dict:
    """Analyze keyword/category trends across multiple reports."""
    if not settings.ANTHROPIC_API_KEY:
        return {"summary": "API key not configured", "keywords": [], "trends": []}

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    summaries = [
        {
            "date": r.get("report_date"),
            "keywords": r.get("keyword_summary", {}).get("keywords", []),
            "editorial": r.get("editorial_summary", ""),
        }
        for r in reports
    ]

    prompt = f"""다음은 {period_label} 동안의 AI 뉴스레터 리포트 요약입니다:

{json.dumps(summaries, ensure_ascii=False, indent=2)}

다음 JSON 형식으로 트렌드 분석 결과를 생성하세요:
{{
  "summary": "기간 전체 흐름 요약 (3-5문장)",
  "rising_keywords": ["새롭게 부상한 키워드"],
  "declining_keywords": ["사라진 키워드"],
  "stable_keywords": ["꾸준히 등장한 키워드"],
  "category_trend": {{"model_llm": "증가|감소|유지", ...}},
  "key_observations": ["관찰 포인트 1", "관찰 포인트 2"],
  "vendor_mentions": {{"OpenAI": 5, "Anthropic": 3, ...}}
}}"""

    response = await client.messages.create(
        model=settings.LLM_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text
    if raw.strip().startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _placeholder_report(report_date: date) -> dict:
    """Fallback when LLM is not available."""
    return {
        "subject_line": f"📡 AI Trend | {report_date} - 테스트 리포트",
        "sections": [
            {
                "type": "top_issues",
                "title": "🔥 오늘 가장 중요한 AI 이슈",
                "items": [
                    {
                        "headline": "LLM API 키 미설정 - 실제 리포트가 아닙니다",
                        "why_important": "ANTHROPIC_API_KEY 환경변수를 설정해주세요",
                        "developer_point": ".env 파일에 ANTHROPIC_API_KEY=sk-ant-... 추가 필요",
                        "keywords": ["setup", "configuration"],
                        "source_url": "#",
                        "source_title": "시스템 메시지",
                        "importance": "high",
                    }
                ],
            },
            {"type": "tech_changes", "title": "💡 개발자가 꼭 알아야 할 기술 변화", "items": []},
            {"type": "new_services", "title": "🚀 새롭게 등장한 서비스·에이전트·오픈소스", "items": []},
        ],
        "editorial_summary": "API 키가 설정되지 않아 플레이스홀더 리포트를 표시합니다.",
        "keywords": [],
        "_tokens": 0,
        "_model": "placeholder",
    }

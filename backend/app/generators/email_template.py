"""HTML email template rendering using Jinja2."""
from __future__ import annotations

from datetime import date

from jinja2 import Environment, DictLoader

_EMAIL_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ subject_line }}</title>
  <style>
    body { margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #1a1a1a; }
    .wrapper { max-width: 680px; margin: 0 auto; background: #ffffff; }
    .header { background: linear-gradient(135deg, #1e3a5f 0%, #0d2137 100%); padding: 32px 40px; }
    .header h1 { margin: 0; color: #ffffff; font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }
    .header .date { color: #7eb8e8; font-size: 14px; margin-top: 6px; }
    .editorial { background: #f0f7ff; border-left: 4px solid #2563eb; padding: 16px 20px; margin: 24px 40px; border-radius: 0 8px 8px 0; font-size: 15px; line-height: 1.7; color: #374151; }
    .section { padding: 24px 40px; border-bottom: 1px solid #f0f0f0; }
    .section-title { font-size: 18px; font-weight: 700; color: #111827; margin: 0 0 20px; }
    .item { background: #fafafa; border: 1px solid #e5e7eb; border-radius: 10px; padding: 18px 20px; margin-bottom: 14px; }
    .item .headline { font-size: 16px; font-weight: 600; color: #111827; margin: 0 0 8px; line-height: 1.4; }
    .item .importance-badge { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 99px; margin-bottom: 10px; }
    .importance-high { background: #fee2e2; color: #991b1b; }
    .importance-medium { background: #fef3c7; color: #92400e; }
    .item .label { font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin: 10px 0 4px; }
    .item .value { font-size: 14px; color: #374151; line-height: 1.6; }
    .item .keywords { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
    .keyword { background: #eff6ff; color: #1d4ed8; font-size: 12px; padding: 3px 10px; border-radius: 99px; font-weight: 500; }
    .source-link { display: inline-block; margin-top: 12px; color: #2563eb; font-size: 13px; text-decoration: none; font-weight: 500; }
    .source-link:hover { text-decoration: underline; }
    .keywords-cloud { padding: 20px 40px; }
    .keywords-cloud h3 { font-size: 14px; font-weight: 600; color: #6b7280; margin-bottom: 12px; }
    .keywords-cloud .cloud { display: flex; flex-wrap: wrap; gap: 8px; }
    .footer { background: #1f2937; padding: 28px 40px; text-align: center; }
    .footer p { color: #9ca3af; font-size: 13px; margin: 0 0 8px; }
    .footer a { color: #60a5fa; text-decoration: none; }
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>📡 AI Trend Newsletter</h1>
      <div class="date">{{ report_date }}</div>
    </div>

    {% if editorial_summary %}
    <div class="editorial">{{ editorial_summary }}</div>
    {% endif %}

    {% for section in sections %}
    <div class="section">
      <h2 class="section-title">{{ section.title }}</h2>
      {% for item in section.items %}
      <div class="item">
        <div class="headline">{{ item.headline }}</div>
        <span class="importance-badge importance-{{ item.importance | default('medium') }}">
          {{ '🔴 HIGH' if item.importance == 'high' else '🟡 MEDIUM' }}
        </span>
        <div class="label">왜 중요한가</div>
        <div class="value">{{ item.why_important }}</div>
        <div class="label">개발자 관점</div>
        <div class="value">{{ item.developer_point }}</div>
        {% if item.keywords %}
        <div class="keywords">
          {% for kw in item.keywords %}
          <span class="keyword"># {{ kw }}</span>
          {% endfor %}
        </div>
        {% endif %}
        <a class="source-link" href="{{ item.source_url }}" target="_blank">
          📄 {{ item.source_title }} →
        </a>
      </div>
      {% endfor %}
    </div>
    {% endfor %}

    {% if global_keywords %}
    <div class="keywords-cloud">
      <h3>오늘의 키워드</h3>
      <div class="cloud">
        {% for kw in global_keywords %}
        <span class="keyword"># {{ kw }}</span>
        {% endfor %}
      </div>
    </div>
    {% endif %}

    <div class="footer">
      <p>AI Trend Newsletter — 개발자를 위한 AI 큐레이션</p>
      <p><a href="{{ unsubscribe_url }}">수신 거부</a></p>
    </div>
  </div>
</body>
</html>"""

_env = Environment(loader=DictLoader({"email.html": _EMAIL_HTML}))


def render_email_html(
    subject_line: str,
    report_date: date | str,
    sections: list[dict],
    editorial_summary: str = "",
    global_keywords: list[str] | None = None,
    unsubscribe_url: str = "#",
) -> str:
    tmpl = _env.get_template("email.html")
    return tmpl.render(
        subject_line=subject_line,
        report_date=str(report_date),
        sections=sections,
        editorial_summary=editorial_summary,
        global_keywords=global_keywords or [],
        unsubscribe_url=unsubscribe_url,
    )

# 시스템 운영 관리 가이드

> 장기 운영·확장·유지보수를 위한 개발자 참조 문서
> 최종 갱신: 2026-03-16

---

## 목차

1. [초기 설정 및 배포](#1-초기-설정-및-배포)
2. [일상적인 운영 작업](#2-일상적인-운영-작업)
3. [모니터링 및 알림](#3-모니터링-및-알림)
4. [데이터베이스 관리](#4-데이터베이스-관리)
5. [뉴스 소스 관리](#5-뉴스-소스-관리)
6. [LLM 프롬프트 관리](#6-llm-프롬프트-관리)
7. [이메일 시스템 관리](#7-이메일-시스템-관리)
8. [장애 대응 (Runbook)](#8-장애-대응-runbook)
9. [시스템 확장 가이드](#9-시스템-확장-가이드)
10. [비용 관리](#10-비용-관리)
11. [보안 관리](#11-보안-관리)
12. [백업 및 복구](#12-백업-및-복구)

---

## 1. 초기 설정 및 배포

### 1.1 환경변수 설정

`.env.example`을 복사하여 `.env` 생성 후 실제 값으로 채움:

```bash
cp .env.example .env
```

| 변수 | 필수 | 설명 | 획득 방법 |
|------|------|------|-----------|
| `OPENAI_API_KEY` | 필수 | GPT-4o API 키 | platform.openai.com → API Keys |
| `SMTP_PASSWORD` | 필수 | Gmail 앱 비밀번호 | Google 계정 → 보안 → 앱 비밀번호 |
| `SMTP_USER` | 필수 | Gmail 발신 주소 | Gmail 주소 |
| `POSTGRES_PASSWORD` | 필수 | DB 비밀번호 | 임의 생성 (`openssl rand -hex 16`) |
| `SECRET_KEY` | 필수 | FastAPI 보안 키 | `openssl rand -hex 32` |
| `NEWS_API_KEY` | 선택 | NewsAPI 키 | newsapi.org → 무료 100 req/day |
| `GNEWS_API_KEY` | 선택 | GNews API 키 | gnews.io → 무료 100 req/day |

### 1.2 최초 실행

```bash
# 1. 모든 컨테이너 빌드 및 시작
docker compose up -d --build

# 2. DB 마이그레이션 확인 (backend 시작 시 자동 실행)
docker compose logs backend | grep -E "alembic|migration"

# 3. 기본 소스 시드 (최초 1회)
docker compose exec backend python scripts/seed_sources.py

# 4. 서비스 정상 동작 확인
curl http://localhost:8000/health
# → {"status": "ok", "env": "development"}
```

### 1.3 서비스 URL

| 서비스 | URL | 용도 |
|--------|-----|------|
| 관리자 대시보드 | http://localhost:3000 | 프론트엔드 UI |
| FastAPI (Swagger) | http://localhost:8000/docs | API 문서 / 테스트 |
| FastAPI (ReDoc) | http://localhost:8000/redoc | API 참조 문서 |
| PostgreSQL | localhost:5432 | DB 직접 접속 |
| Redis | localhost:6379 | 태스크 큐 모니터링 |

---

## 2. 일상적인 운영 작업

### 2.1 서비스 관리 명령어

```bash
# 전체 서비스 상태 확인
docker compose ps

# 특정 서비스 로그 실시간 확인
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f beat

# 서비스 재시작 (코드 변경 없을 때)
docker compose restart backend worker beat

# 코드 변경 후 재빌드
docker compose up -d --build backend worker beat

# 전체 중지
docker compose down

# 데이터 포함 전체 초기화 (주의: 데이터 삭제)
docker compose down -v
```

### 2.2 수동 작업 실행

관리자 대시보드의 "빠른 실행" 버튼 또는 API 직접 호출:

```bash
# 기사 수집 수동 실행
curl -X POST http://localhost:8000/api/v1/jobs/run/collect

# 특정 날짜 리포트 생성
curl -X POST "http://localhost:8000/api/v1/jobs/run/report" \
  -H "Content-Type: application/json" \
  -d '{"report_date": "2026-03-16"}'

# 이메일 발송 (가장 최근 리포트)
curl -X POST http://localhost:8000/api/v1/jobs/run/send

# 테스트 이메일 발송 (구독자에게 발송하기 전 확인)
curl -X POST http://localhost:8000/api/v1/deliveries/test-send \
  -H "Content-Type: application/json" \
  -d '{"report_id": 1, "test_email": "your@email.com"}'
```

### 2.3 Celery 태스크 모니터링

```bash
# 현재 활성 태스크 확인
docker compose exec worker celery -A app.workers.celery_app inspect active

# 예약된 태스크 확인
docker compose exec worker celery -A app.workers.celery_app inspect scheduled

# Beat 스케줄 확인
docker compose exec beat celery -A app.workers.celery_app beat --dry-run
```

### 2.4 DB 직접 접속

```bash
# psql 접속
docker compose exec postgres psql -U aitracker -d aitracker

# 유용한 쿼리
-- 오늘 수집된 기사 수
SELECT COUNT(*) FROM articles WHERE collected_at::date = CURRENT_DATE;

-- 최근 작업 로그
SELECT job_type, status, started_at, finished_at,
       EXTRACT(EPOCH FROM (finished_at - started_at)) AS duration_sec
FROM job_execution_logs
ORDER BY started_at DESC LIMIT 10;

-- 구독자 수
SELECT COUNT(*) FROM recipients WHERE subscribed = true;

-- 리포트 상태 요약
SELECT status, COUNT(*) FROM daily_reports GROUP BY status;
```

---

## 3. 모니터링 및 알림

### 3.1 핵심 모니터링 지표

| 지표 | 정상 범위 | 점검 방법 |
|------|---------|---------|
| 일일 수집 기사 수 | 50–500개 | 대시보드 → 오늘 통계 |
| 중복 제거율 | 10–40% | `SELECT AVG(is_duplicate::int) FROM articles` |
| GPT 토큰 사용량 | 2000–4096 토큰/일 | `SELECT generation_tokens FROM report_versions ORDER BY created_at DESC LIMIT 1` |
| 이메일 발송 성공률 | >95% | 대시보드 → 최근 작업 로그 |
| 소스 수집 실패 횟수 | <3회/소스 | `SELECT name, failure_count FROM sources ORDER BY failure_count DESC` |

### 3.2 작업 로그 점검

```bash
# 실패한 작업만 필터링
curl "http://localhost:8000/api/v1/jobs/logs?limit=50" | \
  python -c "import sys,json; logs=json.load(sys.stdin); \
  [print(l['job_type'], l['error_detail']) for l in logs if l['status']=='failed']"
```

### 3.3 외부 모니터링 도구 연동 (권장)

#### Flower (Celery 웹 모니터링)

```yaml
# docker-compose.yml에 추가
flower:
  image: mher/flower
  command: celery -A app.workers.celery_app flower --port=5555
  ports:
    - "5555:5555"
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/0
  depends_on:
    - redis
```

접속: http://localhost:5555

#### Uptime Kuma (헬스체크 모니터링)

```yaml
# docker-compose.yml에 추가
uptime-kuma:
  image: louislam/uptime-kuma:1
  ports:
    - "3001:3001"
  volumes:
    - uptime_kuma_data:/app/data
```

모니터링 대상 URL:
- `http://backend:8000/health` — Backend 헬스
- `http://frontend:3000` — Frontend 헬스

---

## 4. 데이터베이스 관리

### 4.1 스키마 마이그레이션

새로운 컬럼이나 테이블이 필요할 때:

```bash
# 1. 모델 파일 수정 (app/models/*.py)

# 2. 마이그레이션 파일 자동 생성
docker compose exec backend alembic revision --autogenerate -m "add column xxx"

# 3. 생성된 파일 검토 (alembic/versions/에 생성됨)

# 4. 마이그레이션 실행
docker compose exec backend alembic upgrade head

# 5. 롤백이 필요한 경우
docker compose exec backend alembic downgrade -1
```

**마이그레이션 파일 명명 규칙:**
```
alembic/versions/
├── 001_initial_schema.py
├── 002_add_embedding_column.py   # 다음 마이그레이션
└── 003_add_source_priority.py
```

### 4.2 데이터 정리 정책

오래된 데이터는 주기적으로 정리하여 DB 크기 관리:

```sql
-- 90일 이상 된 기사 삭제 (소스 정보는 유지)
-- 먼저 관련 데이터 삭제
DELETE FROM article_scores
WHERE article_id IN (
  SELECT id FROM articles WHERE collected_at < NOW() - INTERVAL '90 days'
);
DELETE FROM article_contents
WHERE article_id IN (
  SELECT id FROM articles WHERE collected_at < NOW() - INTERVAL '90 days'
);
DELETE FROM article_fingerprints
WHERE article_id IN (
  SELECT id FROM articles WHERE collected_at < NOW() - INTERVAL '90 days'
);
DELETE FROM articles WHERE collected_at < NOW() - INTERVAL '90 days';

-- 180일 이상 된 이메일 발송 기록 삭제
DELETE FROM email_deliveries WHERE created_at < NOW() - INTERVAL '180 days';

-- 90일 이상 된 작업 로그 삭제
DELETE FROM job_execution_logs WHERE started_at < NOW() - INTERVAL '90 days';
```

> 위 쿼리를 월 1회 Celery 태스크로 자동화하는 것을 권장 (9.3항 참조).

### 4.3 인덱스 관리

성능 저하가 발생하면 실행 계획 확인:

```sql
-- 느린 쿼리 확인 (pg_stat_statements 확장 필요)
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC LIMIT 10;

-- 누락된 인덱스 추가 예시
CREATE INDEX CONCURRENTLY idx_articles_collected_at
  ON articles (collected_at DESC);

CREATE INDEX CONCURRENTLY idx_articles_category_score
  ON articles (category, composite_score DESC)
  WHERE is_duplicate = false;
```

---

## 5. 뉴스 소스 관리

### 5.1 새 RSS 소스 추가

관리자 대시보드 → Sources → 소스 추가, 또는 API:

```bash
curl -X POST http://localhost:8000/api/v1/sources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "새 소스 이름",
    "source_type": "rss",
    "base_url": "https://example.com",
    "feed_url": "https://example.com/feed.xml",
    "enabled": true,
    "poll_strategy": "rss",
    "parser_config": {}
  }'
```

**source_type 선택 기준:**

| 값 | 사용 시기 |
|----|---------|
| `rss` | RSS/Atom 피드를 제공하는 블로그/뉴스 사이트 |
| `vendor_blog` | 주요 AI 기업 공식 블로그 |
| `research` | 학술 논문 피드 (arXiv 등) |
| `opensource` | 오픈소스 프로젝트 릴리즈 노트 |
| `news_api` | NewsAPI, GNews 같은 API 기반 수집 |
| `html_scrape` | RSS가 없어서 HTML 직접 파싱이 필요한 경우 |

### 5.2 소스 상태 점검

```sql
-- 수집 실패가 많은 소스
SELECT name, failure_count, last_error, last_collected_at
FROM sources
WHERE failure_count > 3
ORDER BY failure_count DESC;

-- 오랫동안 수집되지 않은 소스
SELECT name, last_collected_at
FROM sources
WHERE enabled = true
  AND last_collected_at < NOW() - INTERVAL '2 days';
```

### 5.3 소스 피드 URL 업데이트

RSS 피드 URL이 변경되거나 폐지된 경우:

```bash
# API로 업데이트
curl -X PATCH http://localhost:8000/api/v1/sources/{source_id} \
  -H "Content-Type: application/json" \
  -d '{"feed_url": "https://new-feed-url.com/feed.xml"}'

# 실패 카운터 리셋
docker compose exec postgres psql -U aitracker -d aitracker \
  -c "UPDATE sources SET failure_count=0, last_error=NULL WHERE id={source_id};"
```

---

## 6. LLM 프롬프트 관리

### 6.1 프롬프트 위치

```
backend/app/generators/report_generator.py
├── REPORT_SYSTEM_PROMPT   # 시스템 프롬프트 (역할, 언어, 형식)
└── generate_report()      # user prompt 구성 로직
```

### 6.2 프롬프트 수정 가이드

**수정 시 주의사항:**
1. `response_format={"type": "json_object"}` 모드이므로 반드시 JSON 반환을 요청해야 함
2. 필수 JSON 키: `subject_line`, `sections[]`, `sections[].items[]`, `closing_message`
3. 섹션 타입은 `top_issues`, `tech_changes`, `new_services` 중 하나여야 함

**JSON 응답 구조 변경 시:**
`email_template.py`의 Jinja2 템플릿도 함께 수정 필요.

### 6.3 LLM 모델 변경

`.env` 파일에서:

```env
# GPT-4o (기본, 고품질)
LLM_MODEL=gpt-4o

# GPT-4o mini (저비용, 약간 낮은 품질)
LLM_MODEL=gpt-4o-mini

# 최신 모델 (출시 시)
LLM_MODEL=gpt-4.5-turbo
```

모델 변경 후 `docker compose restart worker beat` 실행.

### 6.4 리포트 품질 관리

생성된 리포트가 마음에 들지 않으면:
1. 대시보드 → Reports → 해당 리포트 선택
2. 버전의 HTML 직접 편집 (Operator Edit 기능)
3. 승인(Approve) 후 발송

리포트 재생성이 필요하면:
```bash
curl -X POST "http://localhost:8000/api/v1/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{"report_date": "2026-03-16"}'
```
새 버전이 생성되며 이전 버전은 보존됨.

---

## 7. 이메일 시스템 관리

### 7.1 Gmail 설정 유지

Gmail SMTP는 다음 제한이 있음:

| 제한 | 무료 계정 | Google Workspace |
|------|---------|-----------------|
| 일일 발송 한도 | 500통 | 2,000통 |
| 분당 발송 | 20통 | 20통 |

구독자가 500명을 초과하면 Google Workspace 계정으로 전환하거나 SendGrid, Mailgun 같은 전문 ESP로 이전 필요.

### 7.2 Gmail 앱 비밀번호 갱신

Google 계정의 앱 비밀번호는 수동 삭제 전까지 유효하지만, 정기적 갱신 권장:

1. Google 계정 → 보안 → 2단계 인증 → 앱 비밀번호
2. 기존 비밀번호 삭제 후 새 비밀번호 생성
3. `.env`의 `SMTP_PASSWORD` 업데이트
4. `docker compose restart worker` 실행

### 7.3 이메일 발송 실패 재처리

```bash
# 특정 리포트의 실패한 발송만 재시도
curl -X POST http://localhost:8000/api/v1/deliveries/send \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": 1,
    "recipient_ids": [3, 7, 12]  // 실패한 수신자 ID만
  }'
```

### 7.4 이메일 템플릿 수정

```
backend/app/generators/email_template.py
```

Jinja2 템플릿 문법 사용. 수정 후 `docker compose restart worker`.

**주의:** `section['items']`는 딕셔너리 키 접근. `section.items()`는 Python dict 메서드이므로 혼동 주의.

---

## 8. 장애 대응 (Runbook)

### 8.1 기사 수집 실패

**증상:** 대시보드 오늘 기사 수 = 0, 작업 로그에 `collect` 실패

**점검 순서:**
```bash
# 1. Worker 로그 확인
docker compose logs worker --tail=50

# 2. 네트워크 연결 테스트 (컨테이너 내부에서)
docker compose exec worker curl -I https://openai.com/blog/rss.xml

# 3. 개별 소스 수동 수집 테스트
curl -X POST "http://localhost:8000/api/v1/jobs/run/collect" \
  -H "Content-Type: application/json" \
  -d '{"source_ids": [1]}'

# 4. 특정 소스의 피드 URL 직접 확인
curl https://openai.com/blog/rss.xml | head -50
```

**해결책:**
- 피드 URL 변경: 소스 편집에서 새 URL로 업데이트
- 일시적 네트워크 오류: 30분 후 재시도
- 모든 소스 실패: Docker 네트워크 상태 점검

### 8.2 리포트 생성 실패

**증상:** 작업 로그에 `generate_report` 실패

**점검 순서:**
```bash
# 1. Worker 로그에서 에러 확인
docker compose logs worker --tail=100 | grep -A 10 "ERROR"

# 2. OpenAI API 상태 확인
curl https://status.openai.com/api/v2/status.json

# 3. API 키 유효성 확인
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | head -5

# 4. 오늘 수집된 기사가 있는지 확인
docker compose exec postgres psql -U aitracker -d aitracker \
  -c "SELECT COUNT(*) FROM articles WHERE collected_at::date = CURRENT_DATE AND is_duplicate=false;"
```

**해결책:**
- OpenAI API 오류: 잠시 후 수동 재실행 (`/api/v1/jobs/run/report`)
- 수집 기사 0개: 먼저 수집 태스크 실행 후 리포트 생성
- 토큰 초과: `LLM_MAX_TOKENS` 값 줄이거나 기사 수 제한 조정

### 8.3 이메일 발송 실패

**증상:** 발송 기록에 `failed` 상태, 구독자 수신 없음

**점검 순서:**
```bash
# 1. SMTP 연결 테스트
docker compose exec worker python -c "
import asyncio, aiosmtplib
async def test():
    smtp = aiosmtplib.SMTP(hostname='smtp.gmail.com', port=587)
    await smtp.connect()
    await smtp.starttls()
    await smtp.login('your@gmail.com', 'app_password')
    print('SMTP OK')
    await smtp.quit()
asyncio.run(test())
"

# 2. 실패한 발송 기록 확인
docker compose exec postgres psql -U aitracker -d aitracker \
  -c "SELECT recipient_id, error_message FROM email_deliveries WHERE status='failed' ORDER BY created_at DESC LIMIT 10;"
```

**해결책:**
- SMTP 인증 실패: Gmail 앱 비밀번호 재확인 및 갱신
- 수신자 이메일 형식 오류: `recipients` 테이블에서 잘못된 이메일 정정
- 일일 발송 한도 초과: 다음 날 재시도 또는 ESP 이전

### 8.4 DB 연결 실패

**증상:** Backend/Worker 로그에 `psycopg2.OperationalError` 또는 `asyncpg.exceptions.ConnectionError`

```bash
# DB 컨테이너 상태 확인
docker compose ps postgres
docker compose logs postgres --tail=20

# DB 헬스체크 수동 실행
docker compose exec postgres pg_isready -U aitracker -d aitracker

# DB 재시작
docker compose restart postgres

# 연결 수 확인 (너무 많으면 연결 풀 문제)
docker compose exec postgres psql -U aitracker -d aitracker \
  -c "SELECT COUNT(*) FROM pg_stat_activity;"
```

### 8.5 Redis 연결 실패

**증상:** Celery 태스크가 실행되지 않음, `ConnectionError: Redis connection failed`

```bash
# Redis 상태 확인
docker compose exec redis redis-cli ping
# → PONG이 반환되어야 정상

# Redis 재시작
docker compose restart redis

# 재시작 후 Worker/Beat도 재시작
docker compose restart worker beat
```

---

## 9. 시스템 확장 가이드

### 9.1 새 수집기(Collector) 추가

1. `backend/app/collectors/base.py`의 `BaseCollector` 상속
2. `collect()` 추상 메서드 구현
3. `backend/app/services/collector_service.py`에서 `PollStrategy` 분기 추가

```python
# collectors/playwright_collector.py 예시
from .base import BaseCollector, RawArticle
from playwright.async_api import async_playwright

class PlaywrightCollector(BaseCollector):
    async def collect(self) -> list[RawArticle]:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            # ... 스크래핑 로직
        return articles
```

**필요 의존성 추가:**
```toml
# pyproject.toml
"playwright>=1.44.0",
```

### 9.2 새 분석 카테고리 추가

1. `backend/app/models/article.py`의 `ArticleCategory` enum에 값 추가
2. `backend/app/analyzers/scorer.py`의 `CATEGORY_KEYWORDS`에 키워드 추가
3. Alembic 마이그레이션 생성 및 실행 (PostgreSQL enum 변경)
4. Frontend의 `src/lib/utils.ts`의 카테고리 레이블 맵에 추가

```python
# scorer.py - CATEGORY_KEYWORDS 예시
CATEGORY_KEYWORDS = {
    "model_llm": ["gpt", "claude", "gemini", "llama", ...],
    "ai_agent": ["agent", "autonomous", "mcp", "tool use", ...],
    # 새 카테고리 추가
    "robotics": ["robot", "humanoid", "actuator", "embodied"],
}
```

### 9.3 새 Celery 태스크 추가

1. `backend/app/workers/tasks.py`에 태스크 함수 추가
2. `backend/app/workers/celery_app.py`의 `beat_schedule`에 스케줄 추가 (선택)
3. `backend/app/api/v1/jobs.py`에 수동 트리거 엔드포인트 추가 (선택)

```python
# tasks.py 예시 - 데이터 정리 태스크
@celery_app.task(bind=True, base=LoggedTask, name="cleanup_old_data")
def cleanup_old_data_task(self):
    """90일 이상 된 기사 및 로그 삭제"""
    with get_sync_db_session() as db:
        # 정리 로직
        ...

# celery_app.py - beat_schedule에 추가
"monthly-cleanup": {
    "task": "cleanup_old_data",
    "schedule": crontab(hour=3, minute=0, day_of_month=1),  # 매월 1일 03:00 UTC
},
```

### 9.4 구독자 규모별 이메일 발송 전략

| 구독자 수 | 발송 전략 | 예상 비용 |
|---------|---------|---------|
| ~100명 | Gmail SMTP (현재) | 무료 |
| 100–500명 | Gmail SMTP 유지 | 무료 |
| 500–2,000명 | Google Workspace | $6/월 |
| 2,000–10,000명 | SendGrid (무료: 100/일, 유료: $19.95/월) | ~$20/월 |
| 10,000명+ | Amazon SES ($0.10/1,000통) | 사용량 기반 |

**SendGrid 전환 시 수정 파일:**
- `backend/app/services/email_service.py` — SMTP 대신 SendGrid API 클라이언트
- `backend/app/config.py` — SENDGRID_API_KEY 환경변수 추가

### 9.5 운영 환경 배포 (서버 이전)

Docker Compose는 단일 서버 배포에 적합. 트래픽 증가 시 다음 단계:

```
단계 1 (현재): Docker Compose (1서버)
단계 2: Docker Swarm (2–3서버, 무중단 업데이트)
단계 3: Kubernetes (5서버+, 자동 확장)
```

**운영 서버 권장 사양 (단계 1):**
- CPU: 2코어 이상
- RAM: 4GB 이상 (PostgreSQL + Redis + 3개 Python 프로세스)
- 디스크: 50GB SSD (DB 성장 여유분 포함)
- OS: Ubuntu 22.04 LTS

---

## 10. 비용 관리

### 10.1 OpenAI API 비용

GPT-4o 요금 (2026년 기준):
- Input: $2.50 / 1M tokens
- Output: $10.00 / 1M tokens

**일일 예상 비용 계산:**
```
기사 40개 × 평균 200토큰/기사 = 8,000 input tokens
리포트 출력 = 약 4,000 output tokens

일일 비용 = (8,000 × $2.50 + 4,000 × $10.00) / 1,000,000
          ≈ $0.02 + $0.04 = $0.06/일
월 비용 ≈ $1.80
```

**비용 절감 방법:**
```env
# 저비용 모델로 전환 (품질 약간 저하)
LLM_MODEL=gpt-4o-mini  # 약 1/15 비용

# 토큰 한도 조정
LLM_MAX_TOKENS=2048  # 기본 4096에서 축소
```

### 10.2 NewsAPI 요금

| 플랜 | 요청 수 | 가격 |
|------|---------|------|
| Free | 100 req/day | 무료 |
| Developer | 1,000 req/day | $449/월 |

현재 Free 플랜으로 운영 가능. 키워드 수집을 RSS로 대체하면 API 불필요.

### 10.3 인프라 비용

클라우드 운영 시 예상 비용 (AWS ap-northeast-2 기준):

| 서비스 | 인스턴스 | 예상 비용 |
|--------|---------|---------|
| EC2 (t3.small) | 1대 | $15/월 |
| RDS PostgreSQL | db.t3.micro | $15/월 |
| ElastiCache Redis | cache.t3.micro | $12/월 |
| 합계 | | ~$42/월 |

> Docker Compose 단일 서버 사용 시 t3.medium 1대 (~$30/월)로 모두 운영 가능.

---

## 11. 보안 관리

### 11.1 정기 점검 항목

**월간 점검:**
- [ ] `pip-audit` / `npm audit`로 취약점 점검
- [ ] Gmail 앱 비밀번호 갱신
- [ ] Docker 이미지 최신 버전 확인 (`docker compose pull`)

**분기 점검:**
- [ ] OpenAI API 키 갱신 (platform.openai.com → API Keys)
- [ ] PostgreSQL 비밀번호 변경
- [ ] SECRET_KEY 갱신 (갱신 시 기존 세션 무효화됨)
- [ ] 의존성 메이저 버전 업그레이드 검토

### 11.2 API 접근 제어

현재 API는 인증 없이 접근 가능. 운영 환경에서는 반드시 보호 필요:

**옵션 A: Nginx 기본 인증 (간단)**
```nginx
# /etc/nginx/conf.d/aitracker.conf
server {
    location /api/ {
        auth_basic "AI Tracker Admin";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://localhost:8000;
    }
}
```

**옵션 B: FastAPI JWT 인증 (권장)**
```python
# backend/pyproject.toml에 추가
"python-jose[cryptography]>=3.3.0",
"passlib[bcrypt]>=1.7.4",
```

### 11.3 네트워크 보안

```yaml
# docker-compose.yml - 포트 노출 최소화 (운영 환경)
postgres:
  # ports: 제거 (외부에서 직접 접근 차단)
  expose:
    - "5432"  # 내부 네트워크에서만 접근 가능

redis:
  # ports: 제거
  expose:
    - "6379"
```

---

## 12. 백업 및 복구

### 12.1 PostgreSQL 백업

```bash
# 수동 백업
docker compose exec postgres pg_dump -U aitracker aitracker | \
  gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# 복구
zcat backup_20260316_070000.sql.gz | \
  docker compose exec -T postgres psql -U aitracker aitracker
```

### 12.2 자동 백업 설정 (cron)

```bash
# 호스트 서버의 crontab에 추가
# 매일 새벽 3시 백업, 30일 보관
0 3 * * * cd /path/to/project && \
  docker compose exec postgres pg_dump -U aitracker aitracker | \
  gzip > /backups/aitracker_$(date +\%Y\%m\%d).sql.gz && \
  find /backups -name "aitracker_*.sql.gz" -mtime +30 -delete
```

### 12.3 복구 시나리오

**시나리오 1: 단순 설정 변경으로 인한 장애**
```bash
# 환경변수 수정 후 재시작
nano .env
docker compose restart backend worker beat
```

**시나리오 2: 코드 배포 후 장애**
```bash
# 이전 버전으로 롤백
git log --oneline -5  # 이전 커밋 해시 확인
git checkout {이전_커밋_해시}
docker compose up -d --build backend worker beat
```

**시나리오 3: DB 데이터 손상**
```bash
# 1. 서비스 중지
docker compose down

# 2. 손상된 DB 볼륨 제거
docker volume rm ai-trend-tracker-mk-1-claude_postgres_data

# 3. 서비스 재시작 (빈 DB로 시작)
docker compose up -d

# 4. 백업에서 복구
zcat /backups/aitracker_최신.sql.gz | \
  docker compose exec -T postgres psql -U aitracker aitracker

# 5. 마이그레이션 상태 확인
docker compose exec backend alembic current
```

### 12.4 재해 복구 체크리스트

장애 발생 시 다음 순서로 복구:

- [ ] `docker compose ps`로 컨테이너 상태 확인
- [ ] `docker compose logs [서비스명]`으로 에러 메시지 확인
- [ ] 에러 유형에 따라 [8. 장애 대응](#8-장애-대응-runbook) 섹션의 runbook 실행
- [ ] 복구 불가 시 최신 백업에서 복원
- [ ] 복구 완료 후 수동으로 당일 파이프라인 실행 (수집 → 리포트 → 발송)
- [ ] 장애 원인 및 해결 방법 기록 (운영 일지)

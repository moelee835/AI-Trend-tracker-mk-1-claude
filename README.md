# 📡 AI Trend Newsletter Service

개발자를 위한 AI 트렌드 뉴스레터 자동 발송 서비스.
매일 AI 관련 최신 이슈를 수집·분류·요약하여 이메일로 발송합니다.

---

## 아키텍처

```
┌─────────────────────────────────────────────────┐
│                Admin Dashboard (Next.js)         │
│  대시보드 | 소스관리 | 기사 | 리포트 | 분석 | 수신자  │
└──────────────────────┬──────────────────────────┘
                       │ HTTP (REST API)
┌──────────────────────▼──────────────────────────┐
│              FastAPI Backend                     │
│  /api/v1/dashboard | sources | articles |        │
│  reports | recipients | deliveries | analytics  │
└────────┬──────────────────────────┬─────────────┘
         │                          │
┌────────▼──────────┐   ┌──────────▼──────────────┐
│   PostgreSQL      │   │   Redis (Celery Broker)  │
│ (pgvector ready)  │   │                          │
└───────────────────┘   └──────────┬───────────────┘
                                   │
                ┌──────────────────▼───────────────────┐
                │         Celery Workers               │
                │  ① collect_articles_task             │
                │  ② generate_report_task (Claude API) │
                │  ③ send_daily_email_task (SMTP)      │
                └──────────────────────────────────────┘
```

## 기술 스택

| 영역 | 선택 | 이유 |
|------|------|------|
| Backend | Python FastAPI | async 지원, AI/ML 생태계, 자동 OpenAPI |
| DB | PostgreSQL + pgvector | 관계형 + 벡터 검색 확장성 |
| Task Queue | Celery + Redis | 성숙한 스케줄링, 재시도, 모니터링 |
| Frontend | Next.js 15 + Tailwind | 빠른 개발, App Router, SSR |
| LLM | Anthropic Claude | 한국어 품질, Tool use, 긴 컨텍스트 |
| Email | aiosmtplib / SMTP | 범용, SendGrid로 교체 가능 |

## 빠른 시작

### 1. 환경 설정

```bash
cp .env.example .env
# .env에서 다음 값을 반드시 설정하세요:
# ANTHROPIC_API_KEY, SMTP_* , NEWS_API_KEY
```

### 2. Docker로 실행

```bash
docker compose up -d
```

### 3. DB 초기화 및 기본 소스 등록

```bash
docker compose exec backend python -m alembic upgrade head
docker compose exec backend python scripts/seed_sources.py
```

### 4. 관리자 대시보드 접속

- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

### 5. 로컬 개발 (Docker 없이)

```bash
# 백엔드
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Celery 워커
celery -A app.workers.celery_app worker --loglevel=info

# Celery Beat 스케줄러
celery -A app.workers.celery_app beat --loglevel=info

# 프론트엔드
cd frontend
npm install
npm run dev
```

---

## 수집 소스 기본 제공

| 소스 | 유형 | 전략 |
|------|------|------|
| OpenAI Blog | vendor_blog | RSS |
| Anthropic News | vendor_blog | RSS |
| Google DeepMind | vendor_blog | RSS |
| Hugging Face Blog | vendor_blog | RSS |
| Meta AI Blog | vendor_blog | RSS |
| Microsoft AI Blog | vendor_blog | RSS |
| AWS ML Blog | vendor_blog | RSS |
| arXiv cs.AI | research | RSS |
| arXiv cs.LG | research | RSS |
| arXiv cs.CL | research | RSS |
| NewsAPI AI | news_api | API |
| LangChain Blog | opensource | RSS |

---

## 스케줄 파이프라인

```
매일 UTC 22:00  → ① 기사 수집 (collect_articles_task)
매일 UTC 23:00  → ② Claude로 리포트 생성 (generate_report_task)
매일 UTC 00:00  → ③ 이메일 발송 (send_daily_email_task)
```

각 시각은 `.env`에서 `DAILY_COLLECT_HOUR` 등으로 조정 가능합니다.

---

## 관리자 화면

| 화면 | 경로 | 기능 |
|------|------|------|
| 대시보드 | `/` | 오늘 통계, 트렌드 차트, 빠른 실행 |
| 소스 관리 | `/sources` | CRUD, 활성화/비활성화 |
| 기사 목록 | `/articles` | 필터, 중요도 점수, 원문 링크 |
| 리포트 | `/reports` | 목록, 버전, HTML 미리보기, 승인, 발송 |
| 수신자 | `/recipients` | CRUD, CSV 가져오기, 구독 토글 |
| 트렌드 분석 | `/analytics` | 기간 선택, 키워드 차트, AI 요약 |
| 작업 로그 | `/jobs` | 수집/생성/발송 이력, 수동 실행 |

---

## 데이터 모델

```
sources              → 뉴스 수집 소스
articles             → 수집된 기사 메타데이터
article_contents     → 기사 본문
article_fingerprints → 중복 제거용 SimHash
article_scores       → 중요도/신선도/개발자관련성 점수
daily_reports        → 일별 리포트
report_versions      → 버전 관리 (수동 편집 지원)
report_sections      → 리포트 섹션 (3개 고정)
recipients           → 수신자 목록
email_deliveries     → 발송 이력
job_execution_logs   → 배치 작업 로그
```

---

## MVP 이후 확장 로드맵

| 단계 | 기능 |
|------|------|
| MVP | 현재 구현 완료 |
| v1.1 | Playwright 기반 JS 크롤링 (GitHub Trending 등) |
| v1.2 | pgvector 임베딩 기반 고급 중복 제거 |
| v1.3 | 수신자별 관심 태그 세그먼트 발송 |
| v2.0 | 웹훅 알림, Slack 연동 |
| v2.1 | 공개 구독 페이지 |

---

## 테스트

```bash
cd backend
pytest tests/ -v --cov=app
```

---

## 보안 고려사항

- API 서버는 내부망 전용으로 운영 권장
- `SECRET_KEY`는 32자 이상 랜덤 문자열 사용
- SMTP 자격증명은 앱 전용 비밀번호 사용
- `ALLOWED_ORIGINS`에 실제 프론트엔드 도메인만 허용

# AI Trend Newsletter Service — Architecture

> 한국 개발자를 위한 AI 기술 트렌드 자동 수집·분석·발송 시스템
> 아키텍처 문서 | 최종 갱신: 2026-03-16

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [서비스 구성 (컨테이너)](#2-서비스-구성-컨테이너)
3. [전체 데이터 흐름](#3-전체-데이터-흐름)
4. [일일 자동화 파이프라인](#4-일일-자동화-파이프라인)
5. [기사 수집 알고리즘](#5-기사-수집-알고리즘)
6. [중복 제거 알고리즘 (SimHash)](#6-중복-제거-알고리즘-simhash)
7. [기사 점수 산정 알고리즘](#7-기사-점수-산정-알고리즘)
8. [리포트 생성 파이프라인 (LLM)](#8-리포트-생성-파이프라인-llm)
9. [이메일 발송 파이프라인](#9-이메일-발송-파이프라인)
10. [데이터베이스 스키마 (ERD)](#10-데이터베이스-스키마-erd)
11. [API 엔드포인트 구조](#11-api-엔드포인트-구조)
12. [Frontend 페이지 구조](#12-frontend-페이지-구조)
13. [Celery 태스크 상태 전환](#13-celery-태스크-상태-전환)
14. [디렉토리 구조](#14-디렉토리-구조)

---

## 1. 시스템 개요

```mermaid
graph TB
    subgraph External["외부 데이터 소스"]
        RSS[RSS/Atom 피드<br/>OpenAI, Anthropic<br/>HuggingFace, arXiv 등]
        NAPI[NewsAPI.org<br/>키워드 검색]
        GPT[OpenAI GPT-4o<br/>리포트 생성]
        SMTP[Gmail SMTP<br/>이메일 발송]
    end

    subgraph Docker["Docker Compose 클러스터"]
        FE[Frontend<br/>Next.js 15<br/>:3000]
        BE[Backend<br/>FastAPI<br/>:8000]
        WK[Worker<br/>Celery Worker<br/>concurrency=4]
        BT[Beat<br/>Celery Beat<br/>스케줄러]
        DB[(PostgreSQL 16<br/>+ pgvector<br/>:5432)]
        RD[(Redis 7<br/>:6379)]
    end

    subgraph Users["사용자"]
        OP[운영자<br/>Admin Dashboard]
        SUB[구독자<br/>이메일 수신]
    end

    OP -->|브라우저| FE
    FE -->|REST API| BE
    BE -->|ORM async| DB
    BE -->|태스크 발행| RD
    WK -->|태스크 소비| RD
    WK -->|DB 읽기/쓰기| DB
    BT -->|스케줄 발행| RD
    WK -->|기사 수집| RSS
    WK -->|기사 수집| NAPI
    WK -->|LLM 호출| GPT
    WK -->|이메일 발송| SMTP
    SMTP -->|수신| SUB
```

---

## 2. 서비스 구성 (컨테이너)

```mermaid
graph LR
    subgraph compose["docker-compose.yml"]
        direction TB

        postgres["postgres<br/>pgvector/pgvector:pg16<br/>Port: 5432<br/>Volume: postgres_data"]
        redis["redis<br/>redis:7-alpine<br/>Port: 6379<br/>Volume: redis_data"]

        backend["backend<br/>FastAPI + Uvicorn<br/>Port: 8000<br/>--reload (dev)"]
        worker["worker<br/>Celery Worker<br/>concurrency=4<br/>loglevel=info"]
        beat["beat<br/>Celery Beat<br/>스케줄 관리<br/>loglevel=info"]
        frontend["frontend<br/>Next.js 15<br/>Port: 3000<br/>next dev"]
    end

    postgres -->|healthy 이후| backend
    postgres -->|healthy 이후| worker
    postgres -->|healthy 이후| beat
    redis -->|healthy 이후| backend
    redis -->|healthy 이후| worker
    redis -->|healthy 이후| beat
    backend -->|시작 이후| frontend

    style postgres fill:#336791,color:#fff
    style redis fill:#DC382D,color:#fff
    style backend fill:#009688,color:#fff
    style worker fill:#FF9800,color:#fff
    style beat fill:#9C27B0,color:#fff
    style frontend fill:#0070F3,color:#fff
```

| 서비스 | 이미지 | 역할 | 의존성 |
|--------|--------|------|--------|
| `postgres` | pgvector/pgvector:pg16 | 주 데이터베이스 + 벡터 확장 | — |
| `redis` | redis:7-alpine | Celery 브로커 / 결과 백엔드 | — |
| `backend` | 로컬 빌드 | REST API 서버 + DB 마이그레이션 | postgres, redis |
| `worker` | 로컬 빌드 | 비동기 태스크 실행 (수집·생성·발송) | postgres, redis |
| `beat` | 로컬 빌드 | 일별 스케줄 발행 | postgres, redis |
| `frontend` | 로컬 빌드 | 관리자 대시보드 UI | backend |

**Redis DB 분리**

| DB 번호 | 용도 |
|---------|------|
| `redis:6379/0` | Celery 브로커 (태스크 큐) |
| `redis:6379/1` | Celery 결과 백엔드 |

---

## 3. 전체 데이터 흐름

```mermaid
flowchart TD
    A([RSS 피드 / NewsAPI]) -->|HTTP 요청| B[Collector]
    B -->|RawArticle| C{URL 중복?}
    C -->|이미 존재| D[스킵]
    C -->|신규| E{제목 SimHash<br/>유사도 검사}
    E -->|해밍거리 ≤ 5| F[중복 마킹<br/>is_duplicate=true]
    E -->|해밍거리 > 5| G[정상 저장]
    G --> H[ArticleScore 산정<br/>importance/novelty/dev_relevance]
    H --> I[(articles DB)]
    F --> I

    I -->|상위 40개 조회| J[ReportGenerator]
    J -->|system + user prompt| K[OpenAI GPT-4o]
    K -->|JSON 응답| L[섹션 파싱<br/>top_issues / tech_changes / new_services]
    L --> M[HTML 템플릿 렌더링<br/>Jinja2]
    M --> N[(report_versions DB)]

    N -->|HTML + 수신자 목록| O[EmailService]
    O -->|aiosmtplib| P[Gmail SMTP]
    P -->|이메일| Q([구독자])

    style A fill:#f5f5f5
    style K fill:#10a37f,color:#fff
    style P fill:#EA4335,color:#fff
    style Q fill:#f5f5f5
```

---

## 4. 일일 자동화 파이프라인

```mermaid
gantt
    title 일일 자동화 스케줄 (KST 기준)
    dateFormat HH:mm
    axisFormat %H:%M

    section 수집 (Collect)
    RSS/API 기사 수집       :collect, 07:00, 30m
    중복 제거 & 점수 산정   :score,   after collect, 15m

    section 생성 (Generate)
    상위 기사 선별          :select,  08:00, 10m
    GPT-4o 리포트 생성      :gpt,     after select, 20m
    HTML 렌더링 & DB 저장   :render,  after gpt, 10m

    section 발송 (Send)
    구독자 조회             :query,   09:00, 5m
    비동기 이메일 발송      :send,    after query, 20m
```

```mermaid
sequenceDiagram
    participant Beat as Celery Beat
    participant Redis as Redis Queue
    participant Worker as Celery Worker
    participant DB as PostgreSQL
    participant GPT as OpenAI API
    participant SMTP as Gmail SMTP

    Note over Beat: 22:00 UTC (07:00 KST)
    Beat->>Redis: publish: collect_articles_task
    Redis->>Worker: consume task
    Worker->>Worker: RssCollector / NewsApiCollector
    Worker->>Worker: SimHash 중복 제거
    Worker->>Worker: score_article() 점수 산정
    Worker->>DB: INSERT articles, scores
    Worker->>DB: UPDATE job_execution_logs (success)

    Note over Beat: 23:00 UTC (08:00 KST)
    Beat->>Redis: publish: generate_report_task
    Redis->>Worker: consume task
    Worker->>DB: SELECT top 40 articles
    Worker->>GPT: chat.completions.create()
    GPT-->>Worker: JSON (sections)
    Worker->>Worker: render_email_html()
    Worker->>DB: INSERT report_versions, report_sections
    Worker->>DB: UPDATE job_execution_logs (success)

    Note over Beat: 00:00 UTC (09:00 KST)
    Beat->>Redis: publish: send_daily_email_task
    Redis->>Worker: consume task
    Worker->>DB: SELECT subscribed recipients
    Worker->>DB: SELECT active report_version
    loop 각 수신자
        Worker->>SMTP: aiosmtplib.send()
        SMTP-->>Worker: OK
        Worker->>DB: INSERT email_deliveries (sent)
    end
    Worker->>DB: UPDATE job_execution_logs (success)
```

---

## 5. 기사 수집 알고리즘

```mermaid
flowchart TD
    subgraph RSS["RssCollector"]
        R1[feedparser.parse(feed_url)] --> R2[각 entry 순회]
        R2 --> R3[제목 / URL / 날짜 추출]
        R3 --> R4[_normalize_url()<br/>UTM 파라미터 제거]
        R4 --> R5[_clean_html()<br/>HTML 태그 제거]
        R5 --> R6[RawArticle 반환]
    end

    subgraph API["NewsApiCollector"]
        A1[httpx.get(newsapi.org/v2/everything)] --> A2[파라미터: q, language, pageSize]
        A2 --> A3[articles[] 순회]
        A3 --> A4[publishedAt ISO 파싱]
        A4 --> A5[RawArticle 반환]
    end

    subgraph Save["CollectorService.run_collection()"]
        S1[활성 소스 목록 조회] --> S2[소스별 Collector 선택]
        S2 --> S3[collector.collect()]
        S3 --> S4{canonical_url<br/>이미 DB에 존재?}
        S4 -->|YES| S5[스킵]
        S4 -->|NO| S6[deduplicator 호출]
        S6 --> S7[scorer.score_article() 호출]
        S7 --> S8[DB 저장<br/>articles + contents + fingerprints + scores]
        S8 --> S9[source.last_collected_at 업데이트]
    end

    RSS --> Save
    API --> Save
```

**URL 정규화 규칙** (`_normalize_url`):
- `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term` 파라미터 제거
- `#` 앵커(fragment) 제거
- 소문자로 통일 후 trailing slash 제거

---

## 6. 중복 제거 알고리즘 (SimHash)

```mermaid
flowchart TD
    A[기사 제목 텍스트] --> B[소문자 변환 + 특수문자 제거]
    B --> C[공백 기준 토큰화]
    C --> D[각 토큰에 MD5 해시 적용<br/>→ 64비트 정수]
    D --> E["SimHash 벡터 V[64] 초기화 (0)"]
    E --> F["각 비트 위치: hash bit=1 → V+1<br/>hash bit=0 → V-1"]
    F --> G["V[i] > 0 → 최종 비트=1<br/>V[i] ≤ 0 → 최종 비트=0"]
    G --> H[64비트 SimHash 생성]

    H --> I{DB에서 기존<br/>fingerprints 조회}
    I --> J[hamming_distance 계산<br/>XOR 후 popcount]
    J --> K{거리 ≤ 5?}
    K -->|YES| L[중복 판정<br/>is_duplicate=true<br/>duplicate_of_id 설정]
    K -->|NO| M[신규 기사 판정]
```

**임계값 설명:**
- 해밍거리 0: 완전 동일한 제목
- 해밍거리 1–5: 단어 1–3개 차이 (동일 기사의 변형 제목으로 판단)
- 해밍거리 6+: 다른 기사로 판단

---

## 7. 기사 점수 산정 알고리즘

```mermaid
flowchart TD
    A[RawArticle<br/>title + content] --> B[_keyword_score()]
    A --> C[_novelty_indicators()]
    A --> D[_dev_relevance()]

    B --> B1["HIGH_IMPORTANCE_KEYWORDS 매칭<br/>예: GPT, Claude, Gemini, API, LLM"]
    B1 --> B2[importance_score<br/>0.0 ~ 1.0]

    C --> C1["신규성 지표 단어 매칭<br/>예: launch, release, first, announce"]
    C1 --> C2[novelty_score<br/>0.0 ~ 1.0]

    D --> D1["개발자 신호 매칭<br/>예: API, SDK, GitHub, Docker, benchmark"]
    D1 --> D2[developer_relevance_score<br/>0.0 ~ 1.0]

    B2 --> E["composite_score<br/>= importance × 0.4<br/>+ novelty × 0.2<br/>+ dev_relevance × 0.4"]
    C2 --> E
    D2 --> E

    E --> F[_guess_category()<br/>카테고리 자동 분류]
    F --> F1["model_llm / ai_agent / infra_serving<br/>opensource_framework / product_launch<br/>research_paper / security_policy<br/>dev_tools / other"]
    F1 --> G[ArticleScore DB 저장]
```

**점수 가중치 설계 의도:**
- `importance (40%)`: 얼마나 중요한 AI 기술인지
- `novelty (20%)`: 새로운 발표/출시인지
- `dev_relevance (40%)`: 실제 개발자 업무에 관련이 있는지

---

## 8. 리포트 생성 파이프라인 (LLM)

```mermaid
sequenceDiagram
    participant RS as ReportService
    participant DB as PostgreSQL
    participant RG as ReportGenerator
    participant GPT as OpenAI GPT-4o
    participant ET as EmailTemplate

    RS->>DB: get_or_create_daily_report(date)
    DB-->>RS: DailyReport (id)
    RS->>DB: SELECT top 40 articles<br/>(composite_score DESC, not duplicate)
    DB-->>RS: Article list

    RS->>RG: generate_report(articles, date)
    RG->>RG: 기사 요약 텍스트 조합<br/>(title + summary_excerpt)

    RG->>GPT: chat.completions.create()<br/>model=gpt-4o<br/>response_format=json_object<br/>max_tokens=4096

    Note over GPT: SYSTEM PROMPT:<br/>한국 개발자 대상<br/>AI 트렌드 뉴스레터 작성자

    GPT-->>RG: JSON {<br/>  subject_line,<br/>  sections: [{<br/>    title, type,<br/>    items: [{title, summary, url, why_important}]<br/>  }],<br/>  closing_message<br/>}

    RG->>RG: _strip_fences() — 마크다운 코드블록 제거
    RG->>ET: render_email_html(report_data)
    ET->>ET: Jinja2 템플릿 렌더링
    ET-->>RG: HTML 문자열

    RG-->>RS: {subject_line, html, sections, tokens}
    RS->>DB: INSERT report_versions (is_active=true)
    RS->>DB: INSERT report_sections (per section)
    RS->>DB: UPDATE daily_reports (status=ready)
```

**GPT 응답 JSON 구조:**
```json
{
  "subject_line": "이메일 제목",
  "sections": [
    {
      "title": "섹션 제목",
      "type": "top_issues | tech_changes | new_services",
      "items": [
        {
          "title": "기사 제목",
          "summary": "한국어 요약",
          "url": "원문 URL",
          "why_important": "개발자에게 중요한 이유"
        }
      ]
    }
  ],
  "closing_message": "마무리 메시지"
}
```

---

## 9. 이메일 발송 파이프라인

```mermaid
flowchart TD
    A[send_email_task 호출<br/>report_id] --> B[DB: 활성 report_version 조회]
    B --> C{is_active=true<br/>버전 존재?}
    C -->|NO| D[ValueError 발생<br/>작업 실패 기록]
    C -->|YES| E[DB: subscribed=true<br/>수신자 목록 조회]

    E --> F[aiosmtplib.SMTP 연결<br/>SMTP_HOST:SMTP_PORT]
    F --> G[STARTTLS 또는 SSL 협상]
    G --> H[SMTP_USER/PASSWORD 인증]

    H --> I[수신자 리스트 순회]
    I --> J["EmailMessage 구성<br/>From: SMTP_FROM_EMAIL<br/>To: recipient.email<br/>Subject: subject_line<br/>Content-Type: text/html"]
    J --> K[_send_single() 호출]
    K --> L{발송 성공?}
    L -->|YES| M[DB: email_deliveries<br/>status=sent, sent_at=now]
    L -->|NO| N[DB: email_deliveries<br/>status=failed, error_message]
    M --> I
    N --> I

    I -->|완료| O[결과 집계<br/>sent_count / failed_count]
    O --> P[DB: job_execution_logs 업데이트]
```

---

## 10. 데이터베이스 스키마 (ERD)

```mermaid
erDiagram
    sources {
        int id PK
        varchar name
        enum source_type "vendor_blog|research|opensource|news_api|rss|html_scrape"
        varchar base_url
        varchar feed_url
        bool enabled
        enum poll_strategy "rss|api|html|playwright"
        json parser_config
        timestamp last_collected_at
        int failure_count
        text last_error
        timestamp created_at
        timestamp updated_at
    }

    articles {
        int id PK
        int source_id FK
        text title
        text canonical_url
        varchar author
        timestamp published_at
        json tags
        enum category
        bool is_duplicate
        int duplicate_of_id FK
        bool full_content_fetched
        text fetch_error
        timestamp collected_at
        timestamp updated_at
    }

    article_contents {
        int id PK
        int article_id FK
        text raw_html
        text cleaned_text
        text summary_excerpt
        timestamp created_at
    }

    article_fingerprints {
        int id PK
        int article_id FK
        varchar title_hash
        bigint content_simhash
    }

    article_scores {
        int id PK
        int article_id FK
        float importance_score
        float novelty_score
        float developer_relevance_score
        float composite_score
        json score_details
        timestamp scored_at
    }

    recipients {
        int id PK
        varchar email UK
        varchar name
        bool subscribed
        json tags
        timestamp created_at
        timestamp updated_at
    }

    daily_reports {
        int id PK
        date report_date UK
        enum status "draft|ready|approved|sent"
        json included_article_ids
        json keyword_summary
        timestamp created_at
        timestamp updated_at
    }

    report_versions {
        int id PK
        int report_id FK
        int version_number
        bool is_active
        text subject_line
        text html_content
        text plain_content
        text web_preview_content
        varchar llm_model
        text generation_prompt
        int generation_tokens
        bool edited_by_operator
        timestamp created_at
    }

    report_sections {
        int id PK
        int version_id FK
        int order
        varchar title
        enum section_type "top_issues|tech_changes|new_services"
        json content_json
        text html_content
        timestamp created_at
    }

    email_deliveries {
        int id PK
        int report_id FK
        int version_id FK
        int recipient_id FK
        enum status "pending|sent|failed|bounced"
        timestamp sent_at
        text error_message
        bool is_test
        timestamp created_at
    }

    job_execution_logs {
        int id PK
        enum job_type "collect|analyze|generate_report|send_email|manual_resend"
        enum status "running|success|failed|partial"
        varchar celery_task_id
        varchar triggered_by
        json result_summary
        text error_detail
        timestamp started_at
        timestamp finished_at
    }

    sources ||--o{ articles : "수집됨"
    articles ||--o| article_contents : "본문"
    articles ||--o| article_fingerprints : "지문"
    articles ||--o| article_scores : "점수"
    articles }o--o| articles : "중복 참조"
    daily_reports ||--o{ report_versions : "버전"
    report_versions ||--o{ report_sections : "섹션"
    daily_reports ||--o{ email_deliveries : "발송"
    report_versions ||--o{ email_deliveries : "버전 참조"
    recipients ||--o{ email_deliveries : "수신"
```

---

## 11. API 엔드포인트 구조

```mermaid
graph LR
    subgraph API["FastAPI /api/v1"]
        subgraph dashboard["/dashboard"]
            D1["GET /summary"]
        end
        subgraph articles["/articles"]
            AR1["GET /"]
            AR2["GET /{id}"]
        end
        subgraph sources["/sources"]
            SO1["GET /"]
            SO2["POST /"]
            SO3["GET /{id}"]
            SO4["PATCH /{id}"]
            SO5["DELETE /{id}"]
            SO6["POST /{id}/toggle"]
        end
        subgraph recipients["/recipients"]
            RE1["GET /"]
            RE2["POST /"]
            RE3["GET /{id}"]
            RE4["PATCH /{id}"]
            RE5["DELETE /{id}"]
            RE6["POST /import/csv"]
        end
        subgraph reports["/reports"]
            RP1["GET /"]
            RP2["GET /{id}"]
            RP3["POST /generate"]
            RP4["GET /{id}/versions"]
            RP5["GET /{id}/versions/{vid}/html"]
            RP6["PATCH /{id}/versions/{vid}"]
            RP7["POST /{id}/approve"]
        end
        subgraph deliveries["/deliveries"]
            DL1["POST /send"]
            DL2["POST /test-send"]
            DL3["GET /"]
        end
        subgraph jobs["/jobs"]
            JB1["GET /logs"]
            JB2["POST /run/collect"]
            JB3["POST /run/report"]
            JB4["POST /run/send"]
        end
        subgraph analytics["/analytics"]
            AN1["GET /trends"]
            AN2["GET /trends/last7"]
            AN3["GET /trends/last30"]
            AN4["GET /diff"]
        end
    end
```

---

## 12. Frontend 페이지 구조

```mermaid
graph TD
    subgraph Next.js["Next.js 15 App Router"]
        Layout["layout.tsx<br/>Sidebar + Providers"]

        Layout --> Home["/ (page.tsx)<br/>대시보드<br/>오늘 통계 / 7일 추이 / 작업 로그"]
        Layout --> Articles["/articles<br/>기사 목록<br/>카테고리 필터 / 점수 필터"]
        Layout --> Sources["sources<br/>소스 관리<br/>CRUD / 활성화 토글"]
        Layout --> Recipients["recipients<br/>구독자 관리<br/>CRUD / CSV 가져오기"]
        Layout --> Reports["reports<br/>리포트 목록<br/>상태 관리 / 승인 / 발송"]
        Reports --> ReportDetail["reports/[id]<br/>리포트 상세<br/>버전 관리 / HTML 편집"]
        Layout --> Analytics["analytics<br/>트렌드 분석<br/>기간 선택 / 키워드 차트"]
        Layout --> Jobs["jobs<br/>작업 로그<br/>상태 / 소요시간 / 결과"]
    end

    subgraph Lib["lib/"]
        API["api.ts<br/>Axios 클라이언트<br/>80+ API 함수"]
        Utils["utils.ts<br/>날짜 포맷 / 레이블 변환"]
    end

    Home --> API
    Articles --> API
    Sources --> API
    Recipients --> API
    Reports --> API
    ReportDetail --> API
    Analytics --> API
    Jobs --> API
```

---

## 13. Celery 태스크 상태 전환

```mermaid
stateDiagram-v2
    [*] --> PENDING: Beat 스케줄 발행<br/>또는 수동 API 트리거

    PENDING --> RUNNING: Worker 태스크 수신
    RUNNING --> SUCCESS: 정상 완료
    RUNNING --> FAILED: 예외 발생
    FAILED --> RUNNING: 자동 재시도<br/>(collect: 3회 / report: 2회)
    RUNNING --> PARTIAL: 일부 성공<br/>(일부 소스 실패)

    SUCCESS --> [*]
    PARTIAL --> [*]
    FAILED --> [*]: 재시도 초과

    note right of RUNNING
        job_execution_logs.status
        = "running"
    end note

    note right of SUCCESS
        result_summary JSON 저장
        finished_at 기록
    end note
```

---

## 14. 디렉토리 구조

```
AI-Trend-tracker-mk-1-claude/
├── backend/
│   ├── alembic/                    # DB 마이그레이션
│   │   ├── env.py                  # Alembic 환경 설정
│   │   └── versions/
│   │       └── 001_initial_schema.py  # 초기 스키마 (11개 테이블)
│   ├── app/
│   │   ├── analyzers/
│   │   │   ├── deduplicator.py     # SimHash 중복 제거 (MD5 + 해밍거리)
│   │   │   └── scorer.py           # 기사 점수 산정 (importance/novelty/dev)
│   │   ├── api/v1/
│   │   │   ├── analytics.py        # 트렌드 분석 엔드포인트
│   │   │   ├── articles.py         # 기사 조회 엔드포인트
│   │   │   ├── dashboard.py        # 대시보드 요약 엔드포인트
│   │   │   ├── deliveries.py       # 이메일 발송 엔드포인트
│   │   │   ├── jobs.py             # 작업 로그 / 수동 트리거 엔드포인트
│   │   │   ├── recipients.py       # 구독자 관리 엔드포인트
│   │   │   ├── reports.py          # 리포트 관리 엔드포인트
│   │   │   └── sources.py          # 소스 관리 엔드포인트
│   │   ├── collectors/
│   │   │   ├── base.py             # BaseCollector 추상 클래스
│   │   │   ├── rss_collector.py    # RSS/Atom 피드 수집기
│   │   │   └── api_collector.py    # NewsAPI 수집기
│   │   ├── generators/
│   │   │   ├── report_generator.py # GPT-4o LLM 리포트 생성
│   │   │   └── email_template.py   # Jinja2 HTML 이메일 템플릿
│   │   ├── models/
│   │   │   ├── source.py           # Source, SourceType, PollStrategy
│   │   │   ├── article.py          # Article, ArticleContent, Score, Fingerprint
│   │   │   ├── report.py           # DailyReport, ReportVersion, Section, Delivery
│   │   │   ├── recipient.py        # Recipient
│   │   │   └── job.py              # JobExecutionLog
│   │   ├── services/
│   │   │   ├── collector_service.py  # 수집 오케스트레이션
│   │   │   ├── report_service.py     # 리포트 생성 오케스트레이션
│   │   │   ├── email_service.py      # 이메일 발송 (aiosmtplib)
│   │   │   └── analytics_service.py  # 트렌드 분석 집계
│   │   ├── workers/
│   │   │   ├── celery_app.py       # Celery 앱 + Beat 스케줄 정의
│   │   │   └── tasks.py            # 태스크 함수 (LoggedTask 기반)
│   │   ├── config.py               # Pydantic Settings (환경변수)
│   │   ├── database.py             # AsyncEngine + Session
│   │   └── main.py                 # FastAPI 앱 진입점
│   ├── scripts/
│   │   └── seed_sources.py         # 기본 12개 뉴스 소스 시드
│   ├── Dockerfile
│   └── pyproject.toml              # 의존성 정의 (setuptools.build_meta)
├── frontend/
│   ├── src/
│   │   ├── app/                    # Next.js App Router 페이지
│   │   ├── components/layout/      # Sidebar 컴포넌트
│   │   └── lib/
│   │       ├── api.ts              # Axios API 클라이언트 (80+ 함수)
│   │       └── utils.ts            # 유틸리티 함수
│   ├── Dockerfile
│   ├── next.config.js
│   ├── tailwind.config.js
│   └── package.json
├── scripts/
│   └── init_db.sh                  # DB 초기화 스크립트
├── docker-compose.yml
├── .env.example                    # 환경변수 템플릿
├── .gitignore
├── ARCHITECTURE.md                 # 본 문서
├── DEPENDENCIES.md
├── MANAGEMENT.md
└── README.md
```

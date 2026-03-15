# Dependencies 상세 가이드

> 모든 의존성의 선택 이유, 사용 위치, 버전 제약 정리
> 최종 갱신: 2026-03-16

---

## 목차

1. [Backend Python 의존성](#1-backend-python-의존성)
2. [Frontend Node.js 의존성](#2-frontend-nodejs-의존성)
3. [인프라 이미지 의존성](#3-인프라-이미지-의존성)
4. [의존성 업그레이드 전략](#4-의존성-업그레이드-전략)
5. [보안 취약점 점검](#5-보안-취약점-점검)

---

## 1. Backend Python 의존성

> 정의 파일: `backend/pyproject.toml`

### 1.1 웹 프레임워크

| 패키지 | 버전 | 용도 | 사용 위치 |
|--------|------|------|-----------|
| `fastapi` | ≥0.111 | REST API 서버 프레임워크 | `app/main.py`, `app/api/v1/*.py` |
| `uvicorn[standard]` | ≥0.29 | ASGI 서버 (FastAPI 실행) | `docker-compose.yml` CMD |
| `python-multipart` | ≥0.0.9 | 파일 업로드 (CSV import) | `app/api/v1/recipients.py` |

**선택 이유:**
- FastAPI: Python 최고 성능 비동기 프레임워크. `async/await` 네이티브 지원, OpenAPI 자동 생성
- uvicorn[standard]: WebSocket, HTTP/2 지원 포함. `--reload` 플래그로 개발 편의성
- python-multipart: FastAPI의 `UploadFile` 처리에 필수

---

### 1.2 데이터베이스 (ORM + 드라이버)

| 패키지 | 버전 | 용도 | 사용 위치 |
|--------|------|------|-----------|
| `sqlalchemy[asyncio]` | ≥2.0 | ORM (비동기 세션) | `app/database.py`, `app/models/*.py` |
| `asyncpg` | ≥0.29 | PostgreSQL 비동기 드라이버 | `DATABASE_URL` 스킴 (`postgresql+asyncpg://`) |
| `psycopg2-binary` | ≥2.9 | PostgreSQL 동기 드라이버 | Alembic 마이그레이션 (`DATABASE_SYNC_URL`) |
| `alembic` | ≥1.13 | DB 스키마 마이그레이션 | `alembic/env.py`, `alembic/versions/` |

**선택 이유:**
- SQLAlchemy 2.0: `async with AsyncSession()` 패턴으로 비동기 ORM 지원. 관계형 쿼리를 Python 객체로 추상화
- asyncpg: PostgreSQL 전용 최고 성능 비동기 드라이버. psycopg2의 2–3배 처리량
- psycopg2-binary: Alembic은 동기 실행이므로 별도 드라이버 필요. `-binary` 변형으로 시스템 라이브러리 의존성 제거
- alembic: SQLAlchemy 공식 마이그레이션 도구. 버전별 업/다운 마이그레이션 관리

**주의사항:**
```
asyncpg  → DATABASE_URL      (FastAPI 런타임)
psycopg2 → DATABASE_SYNC_URL (Alembic CLI)
두 URL이 동시에 설정되어야 함 (docker-compose.yml environment 참조)
```

---

### 1.3 비동기 태스크 큐

| 패키지 | 버전 | 용도 | 사용 위치 |
|--------|------|------|-----------|
| `celery[redis]` | ≥5.3 | 비동기 태스크 큐 + Beat 스케줄러 | `app/workers/celery_app.py`, `tasks.py` |
| `redis` | ≥5.0 | Celery 브로커 / 결과 백엔드 Python 클라이언트 | `celery_app.py` 설정 |

**선택 이유:**
- Celery: Python 생태계 표준 분산 태스크 큐. `@app.task(bind=True, max_retries=3)` 자동 재시도 내장
- Celery Beat: 별도 프로세스로 cron 스케줄을 Redis에 발행. 서버 재시작에도 스케줄 유지
- `celery[redis]`: Redis 브로커 전용 최적화 코드 포함

**스케줄 정의 위치:** `app/workers/celery_app.py`의 `beat_schedule` 딕셔너리

---

### 1.4 LLM (OpenAI)

| 패키지 | 버전 | 용도 | 사용 위치 |
|--------|------|------|-----------|
| `openai` | ≥1.30 | GPT-4o API 클라이언트 | `app/generators/report_generator.py` |

**선택 이유:**
- 공식 OpenAI Python SDK. `AsyncOpenAI` 클라이언트로 비동기 호출 지원
- `response_format={"type": "json_object"}` 파라미터로 JSON 강제 응답 보장
- `usage.total_tokens` 자동 집계로 비용 추적 가능

**전환 이력:** 초기 구현은 Anthropic Claude SDK였으나 GPT-4o로 전환 (2026-03-15)

---

### 1.5 HTTP / 피드 수집

| 패키지 | 버전 | 용도 | 사용 위치 |
|--------|------|------|-----------|
| `httpx` | ≥0.27 | 비동기 HTTP 클라이언트 | `app/collectors/api_collector.py` |
| `feedparser` | ≥6.0 | RSS/Atom 피드 파싱 | `app/collectors/rss_collector.py` |
| `beautifulsoup4` | ≥4.12 | HTML 파싱 / 텍스트 정제 | `app/collectors/rss_collector.py` |
| `lxml` | ≥5.2 | BeautifulSoup HTML 파서 엔진 | BeautifulSoup `parser="lxml"` |

**선택 이유:**
- httpx: requests의 비동기 버전. `async with httpx.AsyncClient()` 패턴으로 HTTP 연결 재사용
- feedparser: RSS 1.0/2.0, Atom 0.3/1.0 모두 지원. 날짜 형식 자동 파싱
- beautifulsoup4 + lxml: HTML 태그 제거 및 텍스트 추출. lxml은 C 기반으로 순수 Python 파서보다 5–10배 빠름

---

### 1.6 이메일 발송

| 패키지 | 버전 | 용도 | 사용 위치 |
|--------|------|------|-----------|
| `aiosmtplib` | ≥3.0 | 비동기 SMTP 이메일 발송 | `app/services/email_service.py` |
| `jinja2` | ≥3.1 | HTML 이메일 템플릿 렌더링 | `app/generators/email_template.py` |

**선택 이유:**
- aiosmtplib: Python 표준 `smtplib`의 비동기 버전. `asyncio` 이벤트 루프에서 블로킹 없이 다수 이메일 병렬 발송
- jinja2: FastAPI 자체도 내부적으로 사용하는 템플릿 엔진. 조건문/반복문으로 동적 HTML 이메일 생성

**STARTTLS vs SSL:**
```python
# SMTP_PORT=587 → STARTTLS (Gmail 권장)
# SMTP_PORT=465 → SSL/TLS
```

---

### 1.7 데이터 검증 / 설정

| 패키지 | 버전 | 용도 | 사용 위치 |
|--------|------|------|-----------|
| `pydantic` | ≥2.7 | 요청/응답 스키마 검증 | `app/api/v1/*.py` (BaseModel) |
| `pydantic[email]` | ≥2.7 | `EmailStr` 타입 지원 | `app/api/v1/deliveries.py` |
| `pydantic-settings` | ≥2.2 | 환경변수 기반 설정 | `app/config.py` (Settings) |
| `email-validator` | ≥2.1 | pydantic EmailStr 실제 검증 라이브러리 | pydantic 내부 의존성 |

**선택 이유:**
- pydantic v2: Rust 기반 코어로 v1 대비 5–50배 빠른 검증. FastAPI의 기본 검증 엔진
- pydantic-settings: `.env` 파일과 환경변수를 `Settings` 클래스로 자동 로드. 타입 강제 적용
- email-validator: `pydantic[email]` 설치 시 자동 포함. RFC 5322 이메일 형식 검증

---

### 1.8 빌드 시스템

| 패키지 | 버전 | 용도 | 사용 위치 |
|--------|------|------|-----------|
| `setuptools` | ≥68 | Python 패키지 빌드 백엔드 | `pyproject.toml` |
| `wheel` | — | `.whl` 배포 형식 생성 | `pyproject.toml` |

**주의사항:**
```toml
# pyproject.toml
[build-system]
build-backend = "setuptools.build_meta"  # 올바른 설정
# 잘못된 설정 (과거 오류): "setuptools.backends.legacy:build"
```

---

### 1.9 유틸리티

| 패키지 | 버전 | 용도 | 사용 위치 |
|--------|------|------|-----------|
| `python-dotenv` | ≥1.0 | `.env` 파일 로드 | `app/config.py` |
| `python-dateutil` | ≥2.9 | 날짜 파싱 유연성 | `app/collectors/rss_collector.py` |

---

### 전체 `pyproject.toml` 의존성 목록

```toml
[project]
dependencies = [
    # 웹 프레임워크
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "python-multipart>=0.0.9",
    # 데이터베이스
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "psycopg2-binary>=2.9.9",
    "alembic>=1.13.0",
    # 태스크 큐
    "celery[redis]>=5.3.0",
    "redis>=5.0.0",
    # LLM
    "openai>=1.30.0",
    # HTTP / 수집
    "httpx>=0.27.0",
    "feedparser>=6.0.11",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.2.0",
    # 이메일
    "aiosmtplib>=3.0.0",
    "jinja2>=3.1.4",
    # 검증 / 설정
    "pydantic>=2.7.0",
    "pydantic[email]>=2.7.0",
    "pydantic-settings>=2.2.0",
    "email-validator>=2.1.0",
    # 유틸리티
    "python-dotenv>=1.0.0",
    "python-dateutil>=2.9.0",
]
```

---

## 2. Frontend Node.js 의존성

> 정의 파일: `frontend/package.json`

### 2.1 핵심 프레임워크

| 패키지 | 버전 | 용도 | 사용 위치 |
|--------|------|------|-----------|
| `next` | 15.1.3 | React 풀스택 프레임워크 (App Router) | `src/app/` 전체 |
| `react` | ^19 | UI 컴포넌트 라이브러리 | 모든 페이지/컴포넌트 |
| `react-dom` | ^19 | React DOM 렌더러 | `src/app/layout.tsx` |

**선택 이유:**
- Next.js 15 + App Router: 서버 컴포넌트, 스트리밍, 레이아웃 중첩을 기본 지원
- React 19: 동시 렌더링(Concurrent) 정식 지원, 더 나은 Suspense 경험

---

### 2.2 상태 관리 / 데이터 페칭

| 패키지 | 버전 | 용도 | 사용 위치 |
|--------|------|------|-----------|
| `@tanstack/react-query` | ^5 | 서버 상태 관리 / 캐싱 / 리페치 | `src/app/providers.tsx`, 모든 페이지 |
| `axios` | ^1.6 | HTTP 클라이언트 | `src/lib/api.ts` |

**선택 이유:**
- TanStack Query v5: 자동 백그라운드 리페치, 캐시 무효화, 로딩/에러 상태 내장. `useQuery`/`useMutation` 훅으로 선언적 데이터 관리
- axios: 요청/응답 인터셉터, 자동 JSON 직렬화. `fetch` API 대비 에러 처리가 명확

---

### 2.3 차트 / 시각화

| 패키지 | 버전 | 용도 | 사용 위치 |
|--------|------|------|-----------|
| `recharts` | ^2.12 | 트렌드 차트 (선 그래프, 막대 그래프) | `src/app/analytics/page.tsx`, `src/app/page.tsx` |

**선택 이유:**
- SVG 기반, React 컴포넌트 API. `<LineChart>`, `<BarChart>` 선언적 사용
- 반응형 컨테이너(`<ResponsiveContainer>`) 내장

---

### 2.4 UI / 스타일링

| 패키지 | 버전 | 용도 | 사용 위치 |
|--------|------|------|-----------|
| `tailwindcss` | ^3.4 | 유틸리티 CSS 프레임워크 | 모든 컴포넌트 className |
| `postcss` | ^8 | CSS 변환 파이프라인 | `postcss.config.js` |
| `autoprefixer` | ^10 | 브라우저 벤더 prefix 자동 추가 | `postcss.config.js` |

**선택 이유:**
- Tailwind: 별도 CSS 파일 없이 클래스명만으로 스타일링. 번들 크기를 사용된 클래스만 포함하도록 자동 최적화

---

### 2.5 UX 유틸리티

| 패키지 | 버전 | 용도 | 사용 위치 |
|--------|------|------|-----------|
| `react-hot-toast` | ^2.4 | 알림 토스트 (성공/실패 메시지) | `src/app/layout.tsx`, 각 페이지 액션 |
| `react-dropzone` | ^14 | 파일 드래그앤드롭 업로드 | `src/app/recipients/page.tsx` (CSV 가져오기) |
| `date-fns` | ^3.6 | 날짜 포맷팅 / 계산 | `src/lib/utils.ts` |

**선택 이유:**
- react-hot-toast: Promise 기반 API (`toast.promise(api.call(), {...})`)로 API 요청 상태 알림 자동화
- react-dropzone: `<input type="file">` 대체. 드래그앤드롭 UX + 파일 타입 검증
- date-fns: moment.js 대비 트리 쉐이킹(tree-shaking) 지원. 필요한 함수만 번들에 포함

---

### 2.6 TypeScript / 타입 정의

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `typescript` | ^5 | TypeScript 컴파일러 |
| `@types/node` | ^20 | Node.js 타입 정의 |
| `@types/react` | ^19 | React 타입 정의 |
| `@types/react-dom` | ^19 | ReactDOM 타입 정의 |

---

### 전체 `package.json` 의존성 요약

```json
{
  "dependencies": {
    "next": "15.1.3",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@tanstack/react-query": "^5.0.0",
    "axios": "^1.6.0",
    "recharts": "^2.12.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.0.0",
    "autoprefixer": "^10.0.0",
    "react-hot-toast": "^2.4.0",
    "react-dropzone": "^14.0.0",
    "date-fns": "^3.6.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "@types/node": "^20.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0"
  }
}
```

---

## 3. 인프라 이미지 의존성

> 정의 파일: `docker-compose.yml`

| 이미지 | 버전 | 선택 이유 |
|--------|------|-----------|
| `pgvector/pgvector:pg16` | pg16 | PostgreSQL 16 + pgvector 확장 사전 설치. 향후 임베딩 검색 기능 추가 시 즉시 활용 가능 |
| `redis:7-alpine` | 7-alpine | Alpine 기반으로 이미지 크기 최소화 (~30MB). Celery 브로커 및 결과 백엔드로 사용 |
| `python:3.12-slim` | 3.12-slim | 최신 Python 안정 버전. slim 변형으로 불필요한 시스템 도구 제외 |
| `node:20-alpine` | 20-alpine | LTS 버전. Alpine 기반으로 프론트엔드 빌드 환경 최소화 |

**pgvector를 선택한 이유:**
현재 SimHash 기반 중복 제거를 사용하지만, 향후 Embedding 기반 의미적 중복 제거나 유사 기사 검색으로 업그레이드 시 DB 교체 없이 `vector` 컬럼만 추가하면 됨.

---

## 4. 의존성 업그레이드 전략

### 4.1 위험도별 분류

```
낮은 위험 (자유롭게 업그레이드)
├── date-fns        — 유틸리티, 변경사항 없음
├── python-dateutil — 유틸리티
└── react-hot-toast — UI 독립적

중간 위험 (CHANGELOG 확인 후 업그레이드)
├── fastapi         — 마이너 버전에서 Pydantic 연동 변경 가능
├── sqlalchemy      — 2.x → 3.x 마이그레이션 시 ORM 문법 변경
├── celery          — Beat 스케줄 형식이 버전별로 다름
├── openai          — API 응답 형식이 메이저 버전에서 변경
└── next            — App Router API가 RC/Stable 간 변경됨

높은 위험 (충분한 테스트 후 업그레이드)
├── pydantic        — v1→v2 마이그레이션이 주요 파괴적 변경
├── alembic         — 마이그레이션 파일 형식 변경 가능
└── asyncpg         — PostgreSQL 프로토콜 변경
```

### 4.2 업그레이드 명령어

```bash
# Backend 의존성 최신 버전 확인
pip list --outdated

# 특정 패키지 업그레이드
pip install --upgrade fastapi sqlalchemy

# Frontend 의존성 최신 버전 확인
npm outdated

# 대화형 업그레이드
npx npm-check-updates -i
```

### 4.3 보안 패치 자동화

GitHub Dependabot 또는 Renovate Bot을 사용하면 취약점이 있는 의존성의 PR을 자동 생성할 수 있음.

`.github/dependabot.yml` 예시:
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
```

---

## 5. 보안 취약점 점검

### 5.1 Backend

```bash
# pip-audit: PyPI 취약점 DB 기반 점검
pip install pip-audit
pip-audit -r requirements.txt

# safety: Snyk 취약점 DB 기반 점검 (pip-audit 대안)
pip install safety
safety check
```

### 5.2 Frontend

```bash
# npm 내장 취약점 점검
npm audit

# 자동 수정 시도
npm audit fix

# 강제 수정 (메이저 버전 업그레이드 포함, 주의 필요)
npm audit fix --force
```

### 5.3 Docker 이미지

```bash
# Docker Scout로 이미지 취약점 점검
docker scout cves ai-trend-tracker-mk-1-claude-backend
docker scout cves ai-trend-tracker-mk-1-claude-frontend
```

### 5.4 민감 정보 관리

| 환경변수 | 보안 등급 | 관리 방법 |
|---------|---------|---------|
| `OPENAI_API_KEY` | 최고 | 절대 커밋 금지. `.env`는 `.gitignore`에 포함 |
| `POSTGRES_PASSWORD` | 높음 | 운영 환경에서 Docker Secret 또는 Vault 사용 |
| `SMTP_PASSWORD` | 높음 | Gmail App Password 사용 (계정 비밀번호 대신) |
| `SECRET_KEY` | 높음 | 최소 32자 랜덤 문자열 (`openssl rand -hex 32`) |
| `NEWS_API_KEY` | 중간 | 유출 시 API 할당량 소진 위험 |

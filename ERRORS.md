# Error Memory

## StringDataRightTruncationError on author column — 2026-03-17

**Location**: `backend/app/models/article.py:38`
**Error**:
```
asyncpg.exceptions.StringDataRightTruncationError: value too long for type character varying(200)
```
arXiv papers have very long author lists (400+ characters) that exceeded VARCHAR(200).

**Root cause**: `author` column defined as `String(200)` instead of `Text`.
**Fix**: Changed to `Text` type + Alembic migration `f8aa067a3718_change_author_to_text`.
**Verified by**: Collection job ran successfully after fix with 0 errors for arXiv sources.

---

## pytest not installed in Docker container — 2026-03-17

**Location**: `backend/Dockerfile:17`
**Error**:
```
OCI runtime exec failed: exec: "pytest": executable file not found in $PATH
/usr/local/bin/python: No module named pytest
```

**Root cause**: Dockerfile only ran `pip install -e .` which installs main deps but not `[dev]` extras.
**Fix**: Changed to `pip install -e .[dev]` in Dockerfile, rebuilt containers.
**Verified by**: `python -m pytest tests/ --cov=app` runs successfully in container.

---

## aiosqlite missing for in-container tests — 2026-03-17

**Location**: `backend/tests/conftest.py:12`
**Error**:
```
ModuleNotFoundError: No module named 'aiosqlite'
```

**Root cause**: `aiosqlite` needed for SQLite async test DB but not in dev dependencies.
**Fix**: Added `aiosqlite==0.20.0` to `[project.optional-dependencies] dev` in pyproject.toml.
**Verified by**: All tests run without import errors.

---

## SQLite :memory: isolation — db fixture and override_get_db use different connections — 2026-03-17

**Location**: `backend/tests/conftest.py`
**Error**:
```
AssertionError: assert 'top_keywords' in {'error': 'no_reports', 'message': '선택한 기간에 리포트가 없습니다.'}
```
The `db` fixture created a report and committed, but the `override_get_db` (used by the API client) opened a different connection to the same `:memory:` database, which is a completely separate SQLite instance.

**Root cause**: SQLite `:memory:` creates a unique DB per connection. `db` and `override_get_db` use different `TestSessionLocal()` calls = different connections = different databases.
**Fix**: Added `StaticPool` (forces single connection) + `_current_test_session` global so `override_get_db` reuses the test session when one is active.
**Verified by**: All analytics tests pass including `test_trends_last7_with_data`.

---

## Analytics test hardcoded future date causing no_reports response — 2026-03-17

**Location**: `backend/tests/test_api_extended.py:70`
**Error**:
```
AssertionError: assert 'top_keywords' in {'error': 'no_reports', ...}
```
Test fixture created report with `report_date=date(2026, 3, 17)` (hardcoded). Docker container clock runs UTC which was `2026-03-16`. The `trends_last7` endpoint queried `today - 6 days` to `today` = `2026-03-10` to `2026-03-16`, so the `2026-03-17` report was outside the range.

**Root cause**: Hardcoded date in test fixture didn't match container's `date.today()`.
**Fix**: Changed `date(2026, 3, 17)` to `date.today()` in the `report` fixture.
**Verified by**: Analytics tests all pass.

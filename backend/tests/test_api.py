"""Integration tests for FastAPI endpoints (uses in-memory SQLite)."""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


class TestHealth:
    async def test_health(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestSourcesAPI:
    async def test_list_sources_empty(self, client):
        r = await client.get("/api/v1/sources/")
        assert r.status_code == 200
        assert r.json() == []

    async def test_create_source(self, client):
        payload = {
            "name": "Test Blog",
            "source_type": "vendor_blog",
            "base_url": "https://example.com",
            "feed_url": "https://example.com/rss.xml",
            "poll_strategy": "rss",
            "enabled": True,
            "parser_config": {},
        }
        r = await client.post("/api/v1/sources/", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Test Blog"
        assert data["enabled"] is True

    async def test_toggle_source(self, client):
        # Create
        r = await client.post(
            "/api/v1/sources/",
            json={
                "name": "Toggle Test",
                "source_type": "rss",
                "base_url": "https://ex.com",
                "poll_strategy": "rss",
                "parser_config": {},
            },
        )
        src_id = r.json()["id"]
        # Toggle off
        r2 = await client.post(f"/api/v1/sources/{src_id}/toggle")
        assert r2.status_code == 200
        assert r2.json()["enabled"] is False


class TestRecipientsAPI:
    async def test_create_recipient(self, client):
        r = await client.post(
            "/api/v1/recipients/",
            json={"email": "test@example.com", "name": "Test User"},
        )
        assert r.status_code == 201
        assert r.json()["email"] == "test@example.com"

    async def test_duplicate_email_rejected(self, client):
        await client.post("/api/v1/recipients/", json={"email": "dup@example.com"})
        r = await client.post("/api/v1/recipients/", json={"email": "dup@example.com"})
        assert r.status_code == 409

    async def test_delete_recipient(self, client):
        r = await client.post("/api/v1/recipients/", json={"email": "del@example.com"})
        rid = r.json()["id"]
        r2 = await client.delete(f"/api/v1/recipients/{rid}")
        assert r2.status_code == 204


class TestDashboardAPI:
    async def test_dashboard_summary(self, client):
        r = await client.get("/api/v1/dashboard/summary")
        assert r.status_code == 200
        data = r.json()
        assert "articles_today" in data
        assert "article_trend_7d" in data
        assert len(data["article_trend_7d"]) == 7

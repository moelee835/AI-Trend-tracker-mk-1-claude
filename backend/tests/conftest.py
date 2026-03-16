"""Shared pytest fixtures and test database setup."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from app.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

# StaticPool ensures all sessions share the same in-memory DB connection
engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Holds the active test session so the API override shares the same session
_current_test_session: AsyncSession | None = None


async def override_get_db():
    """Yield the current test session if available, else create a new one."""
    if _current_test_session is not None:
        yield _current_test_session
    else:
        async with TestSessionLocal() as session:
            yield session


# Apply the override once globally
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


@pytest.fixture
async def db():
    global _current_test_session
    async with TestSessionLocal() as session:
        _current_test_session = session
        yield session
        _current_test_session = None

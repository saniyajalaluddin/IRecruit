"""Pytest fixtures and configuration."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from backend.app.core.config import Settings, get_settings
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app


def get_test_settings() -> Settings:
    """Provides test-specific isolated settings."""
    return Settings(
        ENVIRONMENT="testing",
        DEBUG=True,
        APP_NAME="AI Resume Intelligence (Test)",
        SECRET_KEY="test-secret-key-for-testing-purposes-only",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        UPLOAD_TEMP_DIR="./storage/test_temp",
        DEFAULT_LLM_PROVIDER="mock",
        DEFAULT_EMBEDDING_PROVIDER="mock",
    )


@pytest_asyncio.fixture(loop_scope="function")
async def test_db_session():
    """Provides a fresh isolated in-memory SQLite database session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def async_client(test_db_session: AsyncSession):
    """Async HTTP client fixture with DB and settings overrides configured."""
    test_settings = get_test_settings()

    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()

"""Pytest fixtures and configuration."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import Settings, get_settings


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


@pytest.fixture(autouse=True)
def override_settings():
    """Overrides settings dependency with test configuration."""
    test_settings = get_test_settings()
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield test_settings
    app.dependency_overrides.clear()


@pytest.fixture
def sync_client():
    """Synchronous test client fixture for rapid integration testing."""
    with TestClient(app=app) as client:
        yield client


@pytest_asyncio.fixture(loop_scope="function")
async def async_client():
    """Async HTTP client fixture configured for ASGI transport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

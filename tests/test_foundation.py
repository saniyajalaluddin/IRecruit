"""Foundation layer tests: configuration, logging, security headers, error handling."""

import os
import subprocess
import pytest
from backend.app.core.config import Settings
from backend.app.core.logging import PrivacyFilter


def test_settings_initialization():
    """Verify settings defaults and configuration parsing."""
    settings = Settings(
        ENVIRONMENT="testing",
        APP_NAME="Custom Test App",
        CORS_ORIGINS="http://localhost:3000,http://localhost:5173",
    )
    assert settings.ENVIRONMENT == "testing"
    assert settings.APP_NAME == "Custom Test App"
    assert "http://localhost:3000" in settings.CORS_ORIGINS
    assert "http://localhost:5173" in settings.CORS_ORIGINS
    assert settings.MAX_UPLOAD_SIZE_BYTES == 5 * 1024 * 1024


def test_privacy_filter_string_masking():
    """Verify that email addresses and bearer tokens are masked from logs."""
    raw_message = "User candidate@example.com logged in with Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.xyz"
    masked = PrivacyFilter.mask_string(raw_message)
    assert "candidate@example.com" not in masked
    assert "[REDACTED_EMAIL]" in masked
    assert "[REDACTED_TOKEN]" in masked


def test_privacy_filter_dict_masking():
    """Verify that sensitive dictionary keys are masked."""
    data = {
        "user_email": "candidate@example.com",
        "password": "supersecretpassword123",
        "api_key": "sk-1234567890",
        "nested": {
            "auth_token": "secret-token-abc",
            "normal_field": "public_data",
        },
    }
    masked = PrivacyFilter.mask_dict(data)
    assert masked["password"] == "[REDACTED]"
    assert masked["api_key"] == "[REDACTED]"
    assert masked["nested"]["auth_token"] == "[REDACTED]"
    assert masked["nested"]["normal_field"] == "public_data"


@pytest.mark.asyncio
async def test_root_endpoint(async_client):
    """Verify root info endpoint returns application metadata."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["status"] == "operational"


@pytest.mark.asyncio
async def test_health_check_endpoint(async_client):
    """Verify /api/v1/health returns structured standard response envelope."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "healthy"
    assert "request_id" in payload
    assert payload["request_id"] != ""


@pytest.mark.asyncio
async def test_security_headers(async_client):
    """Verify security headers are attached to responses."""
    response = await async_client.get("/api/v1/health")
    headers = response.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert "Strict-Transport-Security" in headers
    assert "X-Request-ID" in headers


@pytest.mark.asyncio
async def test_custom_404_error_envelope(async_client):
    """Verify 404 responses conform to the standard error response envelope."""
    response = await async_client.get("/api/v1/non-existent-endpoint")
    assert response.status_code == 404
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "HTTP_404"
    assert "request_id" in payload


def test_gitignore_protects_env_file():
    """Verify that git check-ignore confirms .env is protected and ignored."""
    result = subprocess.run(
        ["git", "check-ignore", ".env", ".env.local", ".env.production"],
        capture_output=True,
        text=True,
    )
    # git check-ignore returns 0 when files are ignored
    assert result.returncode == 0
    ignored_lines = result.stdout.strip().splitlines()
    assert ".env" in ignored_lines

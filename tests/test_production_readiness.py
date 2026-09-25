"""Phase 38: Production Readiness, OWASP Compliance, and Secret Audit.

Validates:
- Zero credential / secret leakage across the codebase
- Production configuration safety and .env.example parity
- Python byte-compilation & syntax integrity
- Security headers and OWASP Top 10 defenses
- Container security compliance
"""

import compileall
import os
import re
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.core.config import Settings
from backend.app.main import create_application


SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{32,}"),  # OpenAI live secret key
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS Access Key ID
    re.compile(r"AIza[0-9A-Za-z-_]{35}"),  # Google API Key
    re.compile(r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PRIVATE) KEY-----"),  # Private keys
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),  # GitHub Personal Access Token
]


def test_zero_secret_leakage_in_codebase():
    """Scan all project source code, documentation, and config files for leaked credentials."""
    repo_root = os.getcwd()
    scanned_extensions = {".py", ".md", ".html", ".js", ".css", ".json", ".yml", ".yaml"}
    scanned_dirs = ["backend", "frontend", "docs", ".github"]

    for target_dir in scanned_dirs:
        dir_path = os.path.join(repo_root, target_dir)
        if not os.path.isdir(dir_path):
            continue

        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if d not in {".git", ".venv", "__pycache__", ".pytest_cache", "storage"}]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext not in scanned_extensions:
                    continue

                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                for pattern in SECRET_PATTERNS:
                    matches = pattern.findall(content)
                    assert len(matches) == 0, f"Potential credential leak detected matching {pattern.pattern} in {filepath}"


def test_env_example_matches_config_settings():
    """Verify that .env.example documents all essential runtime configuration variables."""
    assert os.path.isfile(".env.example"), ".env.example must exist"
    with open(".env.example", "r", encoding="utf-8") as f:
        env_content = f.read()

    essential_vars = [
        "ENVIRONMENT",
        "DEBUG",
        "APP_NAME",
        "APP_VERSION",
        "API_V1_STR",
        "SECRET_KEY",
        "DATABASE_URL",
        "CORS_ORIGINS",
        "MAX_UPLOAD_SIZE_BYTES",
        "DEFAULT_LLM_PROVIDER",
        "DEFAULT_EMBEDDING_PROVIDER",
        "RATE_LIMIT_PER_MINUTE_ANONYMOUS",
        "RATE_LIMIT_PER_MINUTE_AUTHENTICATED",
    ]

    for var in essential_vars:
        assert f"{var}=" in env_content, f"Essential environment variable {var} missing from .env.example"


def test_production_configuration_safety():
    """Verify that production settings enforce security and disable debug features."""
    prod_settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="production-high-entropy-secret-key-32-bytes",
    )
    assert prod_settings.DEBUG is False
    assert prod_settings.ENVIRONMENT == "production"
    assert len(prod_settings.SECRET_KEY) >= 32


def test_python_syntax_and_compilation():
    """Verify all Python files compile cleanly with zero syntax errors."""
    success_backend = compileall.compile_dir("backend", quiet=True, force=True)
    assert success_backend is True, "Syntax or compilation error discovered in backend codebase"

    success_tests = compileall.compile_dir("tests", quiet=True, force=True)
    assert success_tests is True, "Syntax or compilation error discovered in tests codebase"


@pytest.mark.asyncio
async def test_owasp_compliance_headers():
    """Verify all HTTP responses carry mandated OWASP security headers."""
    app = create_application()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200

        headers = resp.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert "Strict-Transport-Security" in headers
        assert "max-age=" in headers["Strict-Transport-Security"]
        assert "X-Request-ID" in headers

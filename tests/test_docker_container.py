"""Tests validating production Dockerfile, docker-compose, and container security specifications."""

import os
import re
import pytest


def test_dockerfile_multi_stage_and_security_configuration():
    """Verify Dockerfile uses multi-stage builds, non-root user, and health check."""
    dockerfile_path = "Dockerfile"
    assert os.path.isfile(dockerfile_path), "Dockerfile does not exist"

    with open(dockerfile_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Multi-stage validation
    assert "AS builder" in content, "Dockerfile must use a builder stage"
    assert "AS runtime" in content, "Dockerfile must use a runtime stage"

    # Non-root user validation (Least Privilege)
    assert "useradd" in content, "Dockerfile must create a dedicated non-root user"
    assert "USER appuser" in content, "Dockerfile must switch to non-root USER appuser"
    assert "10001" in content, "Dockerfile must define fixed non-root UID/GID"

    # Health check probe
    assert "HEALTHCHECK" in content, "Dockerfile must specify a HEALTHCHECK probe"
    assert "/api/v1/health" in content, "Health check probe must query /api/v1/health"

    # Clean executive CMD form for proper PID 1 signal propagation
    assert 'CMD ["uvicorn"' in content, "Dockerfile CMD must use exec JSON array format"


def test_docker_compose_configuration():
    """Verify docker-compose.yml defines required service, health check, and volume persistence."""
    compose_path = "docker-compose.yml"
    assert os.path.isfile(compose_path), "docker-compose.yml does not exist"

    with open(compose_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "services:" in content
    assert "web:" in content
    assert "8000:8000" in content
    assert "ENVIRONMENT=production" in content
    assert "healthcheck:" in content
    assert "app_storage:" in content


def test_dockerignore_security_exclusions():
    """Verify .dockerignore strictly prevents copying secrets, venv, and source control data."""
    ignore_path = ".dockerignore"
    assert os.path.isfile(ignore_path), ".dockerignore does not exist"

    with open(ignore_path, "r", encoding="utf-8") as f:
        content = f.read()

    required_exclusions = [
        ".git",
        ".venv",
        ".env",
        "__pycache__",
        "tests",
    ]
    for exclusion in required_exclusions:
        assert exclusion in content, f".dockerignore must exclude {exclusion}"

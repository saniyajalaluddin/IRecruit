"""Tests for CI/CD workflow definitions, static syntax compilation, and release packaging configurations."""

import os
import py_compile
import re
import pytest


def test_ci_workflow_structure():
    """Verify .github/workflows/ci.yml exists and has essential pipeline stages."""
    ci_path = os.path.join(".github", "workflows", "ci.yml")
    assert os.path.isfile(ci_path), "CI workflow file .github/workflows/ci.yml does not exist"

    with open(ci_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "python-version" in content
    assert "pytest" in content
    assert "requirements.txt" in content
    assert "Security & Secret Leak Audit" in content
    assert "Frontend Static Asset Integrity Check" in content


def test_release_workflow_structure():
    """Verify .github/workflows/release.yml triggers on release tags and tests health."""
    rel_path = os.path.join(".github", "workflows", "release.yml")
    assert os.path.isfile(rel_path), "Release workflow file .github/workflows/release.yml does not exist"

    with open(rel_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'tags:' in content
    assert 'v*.*.*' in content
    assert 'docker' in content.lower()
    assert '/api/v1/health' in content


def test_python_syntax_and_compilation():
    """Verify all Python files compile cleanly without syntax errors."""
    for root, _, files in os.walk("backend"):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                # Attempt to compile
                compiled = py_compile.compile(path, doraise=True)
                assert compiled is not None, f"Failed to compile {path}"

    for root, _, files in os.walk("tests"):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                compiled = py_compile.compile(path, doraise=True)
                assert compiled is not None, f"Failed to compile {path}"


def test_zero_committed_secrets():
    """Strictly assert no real credentials or private keys are committed in source."""
    secret_patterns = [
        re.compile(r"sk-[a-zA-Z0-9]{32,}"),
        re.compile(r"ghp_[a-zA-Z0-9]{36}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
    ]
    scan_dirs = ["backend", "frontend", ".github", "scripts"]
    for sdir in scan_dirs:
        if not os.path.exists(sdir):
            continue
        for root, _, files in os.walk(sdir):
            for f in files:
                if f.endswith((".py", ".html", ".js", ".css", ".json", ".yml", ".md")):
                    path = os.path.join(root, f)
                    with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                        text = fp.read()
                        for pattern in secret_patterns:
                            match = pattern.search(text)
                            assert match is None, f"Potential secret matched in {path}: {match.group(0)[:8]}..."


def test_frontend_distribution_assets_present():
    """Verify all required web application distribution files exist."""
    required_files = [
        "frontend/index.html",
        "frontend/styles.css",
        "frontend/app.js",
        "frontend/favicon.svg",
        "frontend/404.html",
    ]
    for rf in required_files:
        assert os.path.isfile(rf), f"Required frontend distribution asset missing: {rf}"

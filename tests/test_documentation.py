"""Tests validating the completeness, integrity, and accuracy of project documentation."""

import os
import re
import pytest
from backend.app.main import app


DOC_FILES = [
    "README.md",
    "docs/ARCHITECTURE.md",
    "docs/API_SPECIFICATION.md",
    "docs/BENCHMARK_REPORT.md",
]


def test_core_documentation_files_exist():
    """Verify that all core architectural and specification documents exist and are non-empty."""
    for doc in DOC_FILES:
        assert os.path.isfile(doc), f"Missing required documentation file: {doc}"
        assert os.path.getsize(doc) > 500, f"Documentation file {doc} appears suspiciously small or truncated"


def test_no_placeholder_or_todo_markers_in_docs():
    """Verify that documentation contains zero unresolved placeholders or TODO artifacts."""
    placeholder_patterns = [
        re.compile(r"\bTODO\b", re.IGNORECASE),
        re.compile(r"\bTBD\b", re.IGNORECASE),
        re.compile(r"\[INSERT\s+.*?\]", re.IGNORECASE),
        re.compile(r"\bREPLACE_ME\b", re.IGNORECASE),
        re.compile(r"Lorem ipsum", re.IGNORECASE),
    ]

    for doc in DOC_FILES:
        with open(doc, "r", encoding="utf-8") as f:
            content = f.read()

        for pattern in placeholder_patterns:
            matches = pattern.findall(content)
            assert len(matches) == 0, f"Found unresolved placeholder {matches} in {doc}"


def test_readme_contains_essential_sections():
    """Verify README.md contains mission, principles, architecture, benchmark metrics, and quickstart."""
    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()

    essential_sections = [
        "Non-Negotiable Core Principles",
        "System Architecture",
        "Key Technical Capabilities",
        "API Endpoints Reference",
        "Empirical Benchmark Results",
        "Quickstart & Installation",
        "Documentation Index",
        "License & Compliance",
    ]
    for section in essential_sections:
        assert section in readme, f"README.md missing section: {section}"


def test_architecture_doc_contains_diagrams_and_models():
    """Verify ARCHITECTURE.md contains Mermaid diagrams and STRIDE threat modeling."""
    with open("docs/ARCHITECTURE.md", "r", encoding="utf-8") as f:
        arch = f.read()

    assert "```mermaid" in arch, "ARCHITECTURE.md must include Mermaid architectural diagrams"
    assert "STRIDE Threat Model" in arch or "Threat Model" in arch, "ARCHITECTURE.md must include security/threat modeling"
    assert "PII Minimization" in arch, "ARCHITECTURE.md must document PII minimization"


def test_api_specification_endpoints_match_fastapi_routes():
    """Verify that API_SPECIFICATION.md accurately documents existing endpoints in FastAPI app."""
    with open("docs/API_SPECIFICATION.md", "r", encoding="utf-8") as f:
        api_spec = f.read()

    # Collect registered paths from the OpenAPI schema
    registered_paths = set(app.openapi()["paths"].keys())

    expected_endpoints = [
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/resumes/upload",
        "/api/v1/resumes/{resume_id}/versions",
        "/api/v1/resumes/{resume_id}/compare",
        "/api/v1/analyses/anonymous",
        "/api/v1/analyses/{analysis_id}/claim",
        "/api/v1/analyses/dashboard",
        "/api/v1/analyses/history",
        "/api/v1/analyses/{analysis_id}",
        "/api/v1/analyses/{analysis_id}/reproducibility",
        "/api/v1/health",
    ]

    for endpoint in expected_endpoints:
        assert endpoint in registered_paths, f"Expected endpoint {endpoint} not found in FastAPI app routes"
        assert endpoint in api_spec, f"Endpoint {endpoint} not documented in API_SPECIFICATION.md"


def test_benchmark_report_contains_metrics_and_formulas():
    """Verify BENCHMARK_REPORT.md specifies ground truth dataset, metrics, and confusion matrix."""
    with open("docs/BENCHMARK_REPORT.md", "r", encoding="utf-8") as f:
        report = f.read()

    assert "Precision" in report
    assert "Recall" in report
    assert "Accuracy" in report
    assert "Hallucination Rate" in report
    assert "Confusion Matrix" in report
    assert "100.0%" in report
    assert "0.0%" in report

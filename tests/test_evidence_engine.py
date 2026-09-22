"""Tests for Evidence Engine, grounded candidate citations, and absence-of-evidence verification."""

import pytest
from backend.app.modules.evidence.engine import NO_EVIDENCE_EXPLANATION, EvidenceEngine
from backend.app.modules.evidence.service import EvidenceService
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement, RequirementCategory, RequirementPriority
from backend.app.modules.matching.schemas import MatchLevel, MatchSignalBreakdown, RequirementMatchResult
from backend.app.modules.resumes.schemas import (
    EducationItem,
    ProjectItem,
    StructuredResume,
    WorkExperienceItem,
)


@pytest.fixture
def evidence_test_resume() -> StructuredResume:
    """Fixture providing candidate resume with varied sections and qualifications."""
    raw = (
        "Alex Rivera - Senior Full Stack Engineer\n"
        "Summary: Results-oriented software engineer with 6 years building high-availability cloud platforms.\n"
        "Skills: Python, TypeScript, React, Docker, PostgreSQL\n"
        "Experience:\n"
        "Lead Engineer at CloudScale Inc (2022 - Present)\n"
        "- Designed and deployed Python microservices handling over 50,000 requests per second.\n"
        "- Containerized legacy backend services with Docker, cutting deployment time by 40%.\n"
        "Full Stack Developer at AppWorks (2020 - 2022)\n"
        "- Built interactive responsive dashboards using React and TypeScript.\n"
        "- Basic knowledge of Kafka streaming pipelines.\n"
        "Projects:\n"
        "PostgreSQL Query Analyzer: Open-source telemetry tool for analyzing slow PostgreSQL queries.\n"
        "Education:\n"
        "B.S. in Computer Science from State University (2020)\n"
    )
    return StructuredResume(
        raw_text=raw,
        summary="Results-oriented software engineer with 6 years building high-availability cloud platforms.",
        skills=["Python", "TypeScript", "React", "Docker", "PostgreSQL"],
        work_experiences=[
            WorkExperienceItem(
                company="CloudScale Inc",
                job_title="Lead Engineer",
                start_date="2022",
                end_date="Present",
                highlights=[
                    "Designed and deployed Python microservices handling over 50,000 requests per second.",
                    "Containerized legacy backend services with Docker, cutting deployment time by 40%.",
                ],
            ),
            WorkExperienceItem(
                company="AppWorks",
                job_title="Full Stack Developer",
                start_date="2020",
                end_date="2022",
                highlights=[
                    "Built interactive responsive dashboards using React and TypeScript.",
                    "Basic knowledge of Kafka streaming pipelines.",
                ],
            ),
        ],
        projects=[
            ProjectItem(
                title="PostgreSQL Query Analyzer",
                description="Open-source telemetry tool for analyzing slow PostgreSQL queries.",
                technologies=["Python", "PostgreSQL"],
            )
        ],
        education=[
            EducationItem(
                degree="B.S.",
                field_of_study="Computer Science",
                institution="State University",
                graduation_year="2020",
            )
        ],
    )


@pytest.mark.asyncio
async def test_evidence_grounded_work_experience(evidence_test_resume: StructuredResume):
    """Verify matched requirement extracts verbatim quote and context from work experience."""
    engine = EvidenceEngine()
    req = ExtractedRequirement(
        id="req-python",
        text="Python backend microservices experience",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["python"],
    )
    match = RequirementMatchResult(
        requirement_id="req-python",
        requirement_text=req.text,
        match_level=MatchLevel.MATCHED,
        signals=MatchSignalBreakdown(exact_match=True, combined_score=1.0),
        matched_resume_terms=["python"],
        confidence=0.95,
    )

    evidence_list = await engine.evaluate_evidence([req], [match], evidence_test_resume)
    assert len(evidence_list) == 1
    ev = evidence_list[0]

    assert ev.requirement_id == "req-python"
    assert ev.classification == MatchLevel.MATCHED
    assert ev.has_evidence is True
    assert len(ev.snippets) > 0

    # Top snippet should be from work experience highlight
    top_snippet = ev.snippets[0]
    assert top_snippet.section_source == "work_experience"
    assert "CloudScale Inc" in top_snippet.context
    assert "Lead Engineer" in top_snippet.context
    assert "Designed and deployed Python microservices" in top_snippet.quote
    assert "Direct supporting evidence found" in ev.explanation


@pytest.mark.asyncio
async def test_evidence_missing_requirement_exact_wording(evidence_test_resume: StructuredResume):
    """Verify absence of evidence yields exact compliant wording without fabrication."""
    engine = EvidenceEngine()
    req = ExtractedRequirement(
        id="req-golang",
        text="Hands-on Golang concurrent programming",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["golang", "go"],
    )
    match = RequirementMatchResult(
        requirement_id="req-golang",
        requirement_text=req.text,
        match_level=MatchLevel.MISSING,
        signals=MatchSignalBreakdown(combined_score=0.0),
        matched_resume_terms=[],
        confidence=0.90,
    )

    evidence_list = await engine.evaluate_evidence([req], [match], evidence_test_resume)
    assert len(evidence_list) == 1
    ev = evidence_list[0]

    assert ev.classification == MatchLevel.MISSING
    assert ev.has_evidence is False
    assert len(ev.snippets) == 0
    # Strict Non-Negotiable Principle 1.1 compliance
    assert ev.explanation == NO_EVIDENCE_EXPLANATION
    assert ev.explanation == "No supporting evidence was found in the submitted resume."
    assert "does not know" not in ev.explanation.lower()
    assert "lacks" not in ev.explanation.lower()


@pytest.mark.asyncio
async def test_evidence_ambiguous_qualification(evidence_test_resume: StructuredResume):
    """Verify candidate qualification (e.g. 'basic knowledge') yields AMBIGUOUS evidence explanation."""
    engine = EvidenceEngine()
    req = ExtractedRequirement(
        id="req-kafka",
        text="Event-driven streaming architecture with Apache Kafka",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["kafka"],
    )
    match = RequirementMatchResult(
        requirement_id="req-kafka",
        requirement_text=req.text,
        match_level=MatchLevel.AMBIGUOUS,
        signals=MatchSignalBreakdown(exact_match=True, combined_score=0.50),
        matched_resume_terms=["kafka"],
        confidence=0.70,
    )

    evidence_list = await engine.evaluate_evidence([req], [match], evidence_test_resume)
    assert len(evidence_list) == 1
    ev = evidence_list[0]

    assert ev.classification == MatchLevel.AMBIGUOUS
    assert ev.has_evidence is True
    assert len(ev.snippets) > 0
    assert "Basic knowledge of Kafka streaming pipelines." in ev.snippets[0].quote
    assert "Ambiguous or qualified evidence found" in ev.explanation


@pytest.mark.asyncio
async def test_evidence_project_section(evidence_test_resume: StructuredResume):
    """Verify project work is properly cited as evidence source."""
    engine = EvidenceEngine()
    req = ExtractedRequirement(
        id="req-sql-perf",
        text="Database telemetry and query optimization",
        category=RequirementCategory.RESPONSIBILITY,
        priority=RequirementPriority.PREFERRED,
        normalized_terms=["postgresql", "telemetry"],
    )
    match = RequirementMatchResult(
        requirement_id="req-sql-perf",
        requirement_text=req.text,
        match_level=MatchLevel.MATCHED,
        signals=MatchSignalBreakdown(exact_match=True, combined_score=0.90),
        matched_resume_terms=["postgresql"],
        confidence=0.85,
    )

    evidence_list = await engine.evaluate_evidence([req], [match], evidence_test_resume)
    assert len(evidence_list) == 1
    ev = evidence_list[0]

    # Project snippet present
    project_snippets = [s for s in ev.snippets if s.section_source == "projects"]
    assert len(project_snippets) > 0
    assert "PostgreSQL Query Analyzer" in project_snippets[0].context


@pytest.mark.asyncio
async def test_evidence_service_wrapper(evidence_test_resume: StructuredResume):
    """Verify EvidenceService facade properly delegates and returns validated models."""
    service = EvidenceService()
    req = ExtractedRequirement(
        id="req-docker",
        text="Containerization using Docker",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["docker"],
    )
    match = RequirementMatchResult(
        requirement_id="req-docker",
        requirement_text=req.text,
        match_level=MatchLevel.MATCHED,
        signals=MatchSignalBreakdown(exact_match=True, combined_score=1.0),
        matched_resume_terms=["docker"],
        confidence=0.95,
    )

    results = await service.evaluate_evidence([req], [match], evidence_test_resume)
    assert len(results) == 1
    assert results[0].classification == MatchLevel.MATCHED
    assert results[0].has_evidence is True
    assert any("Docker" in s.quote for s in results[0].snippets)

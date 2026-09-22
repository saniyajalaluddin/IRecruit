"""Unit tests for Resume Intelligence extraction pipeline."""

import pytest
from backend.app.modules.resumes.parser import ResumeIntelligenceParser
from backend.app.modules.resumes.service import ResumeService


SAMPLE_FULL_RESUME = """
Johnathan Developer
johnathan@example.com | (555) 123-4567 | San Francisco, CA

Professional Summary:
Versatile Senior Software Engineer with 7+ years of experience designing high-throughput microservices using Python and Go.

Technical Skills:
Languages: Python, Go, TypeScript, SQL
Frameworks: FastAPI, Django, React, Node.js
Databases & Cloud: PostgreSQL, Redis, AWS, Docker, Kubernetes

Work Experience:
Senior Backend Engineer | Acme Technologies | Jan 2021 - Present
- Architected asynchronous event pipeline handling 2M daily messages using Kafka and Python.
- Reduced API response latency by 45% through Redis caching layer.

Software Engineer | Beta Corp | Jun 2018 - Dec 2020
- Developed REST APIs in FastAPI with automated pytest suites.
- Containerized legacy services with Docker and orchestrated deployment in Kubernetes.

Education:
Bachelor of Science in Computer Science | Stanford University | 2018

Projects:
Resume AI Parser | Python, FastAPI
- Built an evidence-grounded alignment engine analyzing job descriptions.

Certifications:
AWS Certified Solutions Architect - Associate (2022)
"""

SAMPLE_MINIMAL_RESUME = """
Jane Minimalist
jane@example.com

Skills:
Python, SQL

Experience:
Junior Developer | Startup Inc | 2022 - 2023
- Built internal web tools in Python.
"""


def test_full_resume_intelligence_parsing():
    """Verify all structured sections are accurately extracted from a comprehensive resume."""
    parsed = ResumeIntelligenceParser.parse(SAMPLE_FULL_RESUME)

    assert parsed.candidate_name == "Johnathan Developer"
    assert parsed.summary is not None
    assert "Versatile Senior Software Engineer" in parsed.summary

    # Skills check
    assert "Python" in parsed.skills
    assert "FastAPI" in parsed.skills
    assert "PostgreSQL" in parsed.skills
    assert "Kubernetes" in parsed.skills

    # Work experience check
    assert len(parsed.work_experiences) == 2
    exp1 = parsed.work_experiences[0]
    assert exp1.job_title == "Senior Backend Engineer"
    assert exp1.company == "Acme Technologies"
    assert exp1.start_date is not None
    assert len(exp1.highlights) == 2

    # Education check
    assert len(parsed.education) == 1
    assert parsed.education[0].degree is not None
    assert "Bachelor of Science" in parsed.education[0].degree or "Bachelor" in parsed.education[0].degree
    assert "2018" in parsed.education[0].graduation_year

    # Projects check
    assert len(parsed.projects) >= 1
    assert "Resume AI Parser" in parsed.projects[0].title

    # Certifications check
    assert len(parsed.certifications) == 1
    assert "AWS Certified Solutions Architect" in parsed.certifications[0].name


def test_missing_sections_tolerated_without_hallucination():
    """Verify that missing sections (e.g. no projects, no certs, no education) are cleanly handled."""
    parsed = ResumeIntelligenceParser.parse(SAMPLE_MINIMAL_RESUME)

    assert parsed.candidate_name == "Jane Minimalist"
    assert parsed.summary is None  # Never hallucinated
    assert len(parsed.skills) == 2
    assert "Python" in parsed.skills
    assert "SQL" in parsed.skills

    assert len(parsed.work_experiences) == 1
    assert parsed.work_experiences[0].company == "Startup Inc"

    # Missing sections must be empty, never invented
    assert len(parsed.education) == 0
    assert len(parsed.projects) == 0
    assert len(parsed.certifications) == 0


@pytest.mark.asyncio
async def test_resume_service_async_interface():
    """Verify async service wrapper conforms to protocol."""
    service = ResumeService()
    result = await service.parse(SAMPLE_FULL_RESUME)
    assert result.candidate_name == "Johnathan Developer"
    assert len(result.skills) > 0

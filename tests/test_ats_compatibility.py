"""Unit tests for Phase 20: ATS Compatibility Engine."""

import pytest
from backend.app.modules.ats.engine import ATSCompatibilityEngine
from backend.app.modules.ats.schemas import (
    ATSCategory,
    ATSIssueSeverity,
)
from backend.app.modules.ats.service import ATSCompatibilityService


@pytest.fixture
def ats_engine():
    return ATSCompatibilityEngine()


@pytest.fixture
def ats_service():
    return ATSCompatibilityService()


def test_clean_standard_resume_scores_high(ats_engine):
    clean_resume = """
    Jane Doe
    jane.doe@example.com | (555) 123-4567 | San Francisco, CA | linkedin.com/in/janedoe

    Professional Summary
    Senior Software Engineer with 7+ years of experience designing cloud distributed systems.

    Technical Skills
    Python, FastAPI, Docker, Kubernetes, PostgreSQL, AWS, CI/CD

    Work Experience
    Senior Backend Engineer | CloudScale Inc. | Jan 2021 - Present
    • Architected microservices pipeline handling 50M requests daily.
    • Optimized database query latency by 40% using PostgreSQL indexing.
    • Deployed automated CI/CD workflows reducing release cycles.

    Software Engineer | DataCorp | Jun 2018 - Dec 2020
    • Engineered data ingestion workers processing streaming sensor data.
    • Refactored legacy monolithic services into modular Python packages.

    Education
    B.S. in Computer Science | University of California, Berkeley | 2014 - 2018
    """

    report = ats_engine.analyze(clean_resume)

    assert report.overall_score >= 85.0
    assert report.grade in ("A", "B")
    assert len(report.critical_issues) == 0
    assert "EXPERIENCE" in report.standard_headings_detected
    assert "SKILLS" in report.standard_headings_detected
    assert "EDUCATION" in report.standard_headings_detected
    assert len(report.missing_standard_headings) == 0


def test_detects_table_formatting_and_emojis(ats_engine):
    table_emoji_resume = """
    🚀 Alex Smith 🚀
    📞 555-987-6543 | ✉️ alex@example.com

    Work Experience
    | Company | Role | Duration |
    | TechCorp | Lead Dev | 2020-2023 |
    | Startup | Engineer | 2018-2020 |

    • Responsible for managing developers.
    • Worked on building websites.

    Skills
    Python, JavaScript
    """

    report = ats_engine.analyze(table_emoji_resume)

    format_cat = report.category_scores.get(ATSCategory.FORMATTING_SAFETY.value)
    assert format_cat is not None
    assert format_cat.score < 80.0

    # Verify table detection issue exists
    table_issues = [i for i in report.critical_issues if "Table" in i.issue]
    assert len(table_issues) >= 1
    assert table_issues[0].severity == ATSIssueSeverity.HIGH

    # Verify emoji detection warning exists
    emoji_warnings = [i for i in report.warnings if "symbols or emojis" in i.issue]
    assert len(emoji_warnings) >= 1


def test_detects_missing_core_sections(ats_engine):
    bad_structure_resume = """
    Bob Builder
    bob@example.com | 555-111-2222

    Summary
    Experienced professional seeking new challenges.

    Random Stuff
    Did a lot of coding in various projects.
    """

    report = ats_engine.analyze(bad_structure_resume)

    assert "EXPERIENCE" in report.missing_standard_headings
    assert "SKILLS" in report.missing_standard_headings
    assert "EDUCATION" in report.missing_standard_headings

    # Critical issues should include missing experience and skills
    missing_heads = [i.issue for i in report.critical_issues]
    assert any("Work Experience" in h for h in missing_heads)
    assert any("Skills" in h for h in missing_heads)
    assert report.overall_score < 70.0


def test_detects_creative_headings_and_passive_bullets(ats_engine):
    creative_resume = """
    Jane Doe
    jane@example.com | 555-222-3333 | Jan 2020 - Dec 2022

    My Journey
    ➤ Duties included maintaining legacy code.
    ➤ Tasked with updating documentation.

    Ninja Skills
    Python, Git

    Education
    BS Software Engineering | 2016 - 2020
    """

    report = ats_engine.analyze(creative_resume)

    heading_issues = [i for i in report.warnings if "Non-standard section header" in i.issue]
    assert len(heading_issues) >= 1

    bullet_cat = report.category_scores.get(ATSCategory.BULLET_STANDARDIZATION.value)
    assert bullet_cat is not None
    assert bullet_cat.score < 85.0


def test_empty_resume_handling(ats_engine):
    report = ats_engine.analyze("")
    assert report.overall_score == 0.0
    assert report.grade == "F"
    assert len(report.critical_issues) >= 1


def test_ats_service_facade(ats_service):
    sample = """
    Dev Candidate
    dev@test.com | 555-000-1111
    Work Experience
    • Developed full-stack cloud applications in Jan 2022 - Present.
    Skills
    Python, SQL
    Education
    B.S. Information Systems, 2021
    """
    report = ats_service.analyze_resume_text(sample)
    assert report.overall_score > 70.0
    assert report.grade in ("A", "B", "C")

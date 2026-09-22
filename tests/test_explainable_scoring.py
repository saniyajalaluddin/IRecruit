"""Tests for Explainable Scoring Engine, deterministic calculation, and JD-driven priorities."""

import pytest
from backend.app.modules.evidence.schemas import EvidenceSnippet, RequirementEvidence
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement, RequirementCategory, RequirementPriority
from backend.app.modules.matching.schemas import MatchLevel
from backend.app.modules.resumes.schemas import StructuredResume, WorkExperienceItem
from backend.app.modules.scoring.engine import DEFAULT_COMPONENT_WEIGHTS, SCORING_VERSION, ScoringEngine
from backend.app.modules.scoring.schemas import AlignmentScoreResult
from backend.app.modules.scoring.service import ScoringService


@pytest.fixture
def sample_candidate_resume() -> StructuredResume:
    """Fixture providing a 6-year experienced backend engineer resume."""
    return StructuredResume(
        raw_text="Jane Doe. 6 years building distributed cloud platforms in Python and Docker.",
        summary="Senior Backend Engineer with 6 years experience.",
        skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
        work_experiences=[
            WorkExperienceItem(
                company="TechCorp",
                job_title="Senior Engineer",
                start_date="2021",
                end_date="2026",
                highlights=["Architected scalable Python microservices."],
            ),
            WorkExperienceItem(
                company="StartupCo",
                job_title="Backend Developer",
                start_date="2020",
                end_date="2021",
                highlights=["Built REST APIs with FastAPI."],
            ),
        ],
        education=[],
        projects=[],
    )


def test_scoring_weights_sum_to_one():
    """Verify default component weights sum to exactly 1.0 (100%)."""
    total_weight = sum(DEFAULT_COMPONENT_WEIGHTS.values())
    assert pytest.approx(total_weight, 0.0001) == 1.0


def test_deterministic_scoring_reproducibility(sample_candidate_resume: StructuredResume):
    """Verify scoring calculations are 100% deterministic with zero randomness."""
    engine = ScoringEngine()

    req1 = ExtractedRequirement(
        id="req-1",
        text="Python backend engineering",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["python"],
    )
    ev1 = RequirementEvidence(
        requirement_id="req-1",
        requirement_text=req1.text,
        classification=MatchLevel.MATCHED,
        snippets=[
            EvidenceSnippet(
                quote="Architected scalable Python microservices.",
                section_source="work_experience",
                relevance_score=1.0,
            )
        ],
        explanation="Direct evidence found in work_experience.",
        has_evidence=True,
    )

    req2 = ExtractedRequirement(
        id="req-2",
        text="Kubernetes container orchestration",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["kubernetes"],
    )
    ev2 = RequirementEvidence(
        requirement_id="req-2",
        requirement_text=req2.text,
        classification=MatchLevel.MISSING,
        snippets=[],
        explanation="No supporting evidence was found in the submitted resume.",
        has_evidence=False,
    )

    score_a = engine.calculate_score([req1, req2], [ev1, ev2], sample_candidate_resume)
    score_b = engine.calculate_score([req1, req2], [ev1, ev2], sample_candidate_resume)

    assert score_a.overall_score == score_b.overall_score
    assert score_a.components == score_b.components
    assert score_a.scoring_version == SCORING_VERSION
    assert 0.0 <= score_a.overall_score <= 100.0


def test_jd_priority_weighting_impact(sample_candidate_resume: StructuredResume):
    """Verify missing a REQUIRED skill penalizes the technical score more than missing a PREFERRED skill."""
    engine = ScoringEngine()

    # Scenario A: Missing a REQUIRED skill
    req_req = ExtractedRequirement(
        id="r-req",
        text="Core Python",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["python"],
    )
    ev_req_missing = RequirementEvidence(
        requirement_id="r-req",
        requirement_text="Core Python",
        classification=MatchLevel.MISSING,
        snippets=[],
        explanation="No supporting evidence was found in the submitted resume.",
        has_evidence=False,
    )

    req_pref = ExtractedRequirement(
        id="r-pref",
        text="GraphQL APIs",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.PREFERRED,
        normalized_terms=["graphql"],
    )
    ev_pref_matched = RequirementEvidence(
        requirement_id="r-pref",
        requirement_text="GraphQL APIs",
        classification=MatchLevel.MATCHED,
        snippets=[EvidenceSnippet(quote="Built GraphQL APIs", section_source="skills")],
        explanation="Found.",
        has_evidence=True,
    )

    # Missing REQUIRED (weight 2), matched PREFERRED (weight 1) -> earned 1 / 3 = 33.3%
    score_missing_required = engine.calculate_score([req_req, req_pref], [ev_req_missing, ev_pref_matched], sample_candidate_resume)

    # Scenario B: Matched REQUIRED (weight 2), missing PREFERRED (weight 1) -> earned 2 / 3 = 66.7%
    ev_req_matched = RequirementEvidence(
        requirement_id="r-req",
        requirement_text="Core Python",
        classification=MatchLevel.MATCHED,
        snippets=[EvidenceSnippet(quote="Core Python", section_source="skills")],
        explanation="Found.",
        has_evidence=True,
    )
    ev_pref_missing = RequirementEvidence(
        requirement_id="r-pref",
        requirement_text="GraphQL APIs",
        classification=MatchLevel.MISSING,
        snippets=[],
        explanation="No supporting evidence was found in the submitted resume.",
        has_evidence=False,
    )

    score_missing_preferred = engine.calculate_score([req_req, req_pref], [ev_req_matched, ev_pref_missing], sample_candidate_resume)

    assert score_missing_preferred.components.technical_skill_alignment > score_missing_required.components.technical_skill_alignment
    assert score_missing_preferred.overall_score > score_missing_required.overall_score


def test_experience_alignment_tenure_calculation(sample_candidate_resume: StructuredResume):
    """Verify experience alignment calculates candidate tenure against JD required years."""
    engine = ScoringEngine()

    req_senior = ExtractedRequirement(
        id="req-exp",
        text="Minimum 5+ years of software engineering experience",
        category=RequirementCategory.EXPERIENCE,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=[],
    )
    ev = RequirementEvidence(
        requirement_id="req-exp",
        requirement_text=req_senior.text,
        classification=MatchLevel.MATCHED,
        snippets=[],
        explanation="Experience satisfied.",
        has_evidence=True,
    )

    # Candidate has 2020-2026 = 6 years tenure (exceeds 5 years required)
    result = engine.calculate_score([req_senior], [ev], sample_candidate_resume)
    assert result.components.experience_alignment == 100.0


def test_explainable_summary_rationale(sample_candidate_resume: StructuredResume):
    """Verify summary rationale details component breakdown and respects Non-Negotiable Principle 1.1."""
    engine = ScoringEngine()
    req = ExtractedRequirement(
        id="req-k8s",
        text="Kubernetes container deployment",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["kubernetes"],
    )
    ev = RequirementEvidence(
        requirement_id="req-k8s",
        requirement_text=req.text,
        classification=MatchLevel.MISSING,
        snippets=[],
        explanation="No supporting evidence was found in the submitted resume.",
        has_evidence=False,
    )

    result = engine.calculate_score([req], [ev], sample_candidate_resume)
    rationale = result.summary_rationale

    assert "Technical Skill Alignment:" in rationale
    assert "Semantic Relevance:" in rationale
    assert "Evidence Strength:" in rationale
    assert "No supporting evidence was found in the submitted resume" in rationale
    assert "does not know" not in rationale.lower()


def test_scoring_service_facade(sample_candidate_resume: StructuredResume):
    """Verify ScoringService wraps ScoringEngine and returns validated models."""
    service = ScoringService()
    assert service.version == SCORING_VERSION

    req = ExtractedRequirement(
        id="req-1",
        text="FastAPI developer",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["fastapi"],
    )
    ev = RequirementEvidence(
        requirement_id="req-1",
        requirement_text=req.text,
        classification=MatchLevel.MATCHED,
        snippets=[EvidenceSnippet(quote="FastAPI", section_source="skills")],
        explanation="Found.",
        has_evidence=True,
    )

    res = service.calculate_score([req], [ev], sample_candidate_resume, ats_score=90.0)
    assert isinstance(res, AlignmentScoreResult)
    assert res.components.ats_compatibility == 90.0
    assert res.overall_score > 0

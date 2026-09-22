"""Tests for Evidence-Grounded Recommendation Engine and non-fabrication guarantees."""

import pytest
from backend.app.modules.evidence.schemas import EvidenceSnippet, RequirementEvidence
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement, RequirementCategory, RequirementPriority
from backend.app.modules.matching.schemas import MatchLevel
from backend.app.modules.recommendations.engine import RecommendationEngine
from backend.app.modules.recommendations.schemas import RecommendationItem, RecommendationType
from backend.app.modules.recommendations.service import RecommendationService
from backend.app.modules.resumes.schemas import StructuredResume, WorkExperienceItem


@pytest.fixture
def recommendation_test_data():
    """Provides test requirements, evidence, and structured resume."""
    req_postgres = ExtractedRequirement(
        id="req-pg",
        text="Relational database schema design in PostgreSQL",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["postgresql"],
    )
    ev_postgres = RequirementEvidence(
        requirement_id="req-pg",
        requirement_text=req_postgres.text,
        classification=MatchLevel.MATCHED,
        snippets=[EvidenceSnippet(quote="Used Postgres database.", section_source="skills")],
        explanation="Matched via Postgres.",
        has_evidence=True,
    )

    req_gql = ExtractedRequirement(
        id="req-gql",
        text="GraphQL API integration",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["graphql"],
    )
    ev_gql = RequirementEvidence(
        requirement_id="req-gql",
        requirement_text=req_gql.text,
        classification=MatchLevel.AMBIGUOUS,
        snippets=[EvidenceSnippet(quote="Basic exposure to GraphQL", section_source="work_experience")],
        explanation="Ambiguous evidence found.",
        has_evidence=True,
    )

    req_missing = ExtractedRequirement(
        id="req-k8s",
        text="Kubernetes cluster orchestration",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["kubernetes"],
    )
    ev_missing = RequirementEvidence(
        requirement_id="req-k8s",
        requirement_text=req_missing.text,
        classification=MatchLevel.MISSING,
        snippets=[],
        explanation="No supporting evidence was found in the submitted resume.",
        has_evidence=False,
    )

    resume = StructuredResume(
        raw_text="John Doe. Software Engineer with experience in Python and Postgres.",
        summary="Backend developer.",
        skills=["Python", "Postgres"],
        work_experiences=[
            WorkExperienceItem(
                company="OldTech",
                job_title="Software Developer",
                start_date="2022",
                end_date="2025",
                highlights=[
                    "Responsible for developing python batch jobs.",
                    "Basic exposure to GraphQL in internal hackathon.",
                ],
            )
        ],
        education=[],
        projects=[],
    )

    requirements = [req_postgres, req_gql, req_missing]
    evidence_list = [ev_postgres, ev_gql, ev_missing]
    return requirements, evidence_list, resume


@pytest.mark.asyncio
async def test_recommendation_resolve_ambiguity(recommendation_test_data):
    """Verify ambiguous qualifications generate guidance to clarify depth without fabricating."""
    requirements, evidence_list, resume = recommendation_test_data
    engine = RecommendationEngine()

    recs = await engine.generate_recommendations(requirements, evidence_list, resume)
    ambiguity_recs = [r for r in recs if r.type == RecommendationType.RESOLVE_AMBIGUITY]

    assert len(ambiguity_recs) == 1
    rec = ambiguity_recs[0]
    assert rec.requirement_id == "req-gql"
    assert "hedging" in rec.title.lower() or "clarify" in rec.title.lower()
    assert rec.is_evidence_grounded is True
    assert "Basic exposure to GraphQL" in rec.current_evidence_quote


@pytest.mark.asyncio
async def test_recommendation_keyword_alignment(recommendation_test_data):
    """Verify alias terminology (Postgres -> PostgreSQL) generates keyword alignment advice."""
    requirements, evidence_list, resume = recommendation_test_data
    engine = RecommendationEngine()

    recs = await engine.generate_recommendations(requirements, evidence_list, resume)
    kw_recs = [r for r in recs if r.type == RecommendationType.KEYWORD_ALIGNMENT]

    assert len(kw_recs) == 1
    rec = kw_recs[0]
    assert rec.requirement_id == "req-pg"
    assert "Postgres" in rec.title and "postgresql" in rec.title.lower()
    assert rec.is_evidence_grounded is True


@pytest.mark.asyncio
async def test_recommendation_improve_wording_weak_verbs(recommendation_test_data):
    """Verify passive verbs ('Responsible for...') trigger wording enhancement suggestions."""
    requirements, evidence_list, resume = recommendation_test_data
    engine = RecommendationEngine()

    recs = await engine.generate_recommendations(requirements, evidence_list, resume)
    wording_recs = [r for r in recs if r.type == RecommendationType.IMPROVE_WORDING]

    assert len(wording_recs) == 1
    rec = wording_recs[0]
    assert "Responsible for developing python batch jobs." in rec.current_evidence_quote
    assert "action verb" in rec.suggested_revision.lower()
    assert rec.is_evidence_grounded is True


@pytest.mark.asyncio
async def test_recommendation_missing_evidence_upskilling(recommendation_test_data):
    """Verify missing requirements recommend genuine upskilling or verified projects, never false claims."""
    requirements, evidence_list, resume = recommendation_test_data
    engine = RecommendationEngine()

    recs = await engine.generate_recommendations(requirements, evidence_list, resume)
    missing_recs = [r for r in recs if r.requirement_id == "req-k8s"]

    assert len(missing_recs) == 1
    rec = missing_recs[0]
    # Guarantees never advising false claims
    assert "No supporting evidence was found" in rec.rationale
    assert "verified" in rec.suggested_revision.lower() or "learning area" in rec.suggested_revision.lower()
    assert rec.is_evidence_grounded is True


@pytest.mark.asyncio
async def test_recommendation_service_facade(recommendation_test_data):
    """Verify RecommendationService delegates to engine and returns validated list."""
    requirements, evidence_list, resume = recommendation_test_data
    service = RecommendationService()

    recs = await service.generate_recommendations(requirements, evidence_list, resume)
    assert isinstance(recs, list)
    assert len(recs) >= 3
    assert all(isinstance(r, RecommendationItem) for r in recs)
    assert all(r.is_evidence_grounded is True for r in recs)


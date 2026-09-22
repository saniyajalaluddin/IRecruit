"""Tests for Controlled Resume Optimization, anti-hallucination verification, and metric preservation."""

import pytest
from backend.app.modules.evidence.schemas import EvidenceSnippet, RequirementEvidence
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement, RequirementCategory, RequirementPriority
from backend.app.modules.matching.schemas import MatchLevel
from backend.app.modules.optimization.engine import ControlledResumeOptimizer
from backend.app.modules.optimization.schemas import ControlledOptimizationResult
from backend.app.modules.optimization.service import OptimizationService
from backend.app.modules.resumes.schemas import StructuredResume, WorkExperienceItem


@pytest.fixture
def sales_forecasting_candidate_resume() -> StructuredResume:
    """Provides candidate resume with verified Python and Scikit-learn skills."""
    return StructuredResume(
        raw_text="Data Scientist with skills in Python, Scikit-learn, and Pandas.",
        summary="Data Scientist.",
        skills=["Python", "Scikit-learn", "Pandas"],
        work_experiences=[
            WorkExperienceItem(
                company="RetailCorp",
                job_title="Data Scientist",
                start_date="2022",
                end_date="2025",
                highlights=[
                    "Worked on sales forecasting.",
                    "Responsible for developing predictive pipeline.",
                ],
            )
        ],
        education=[],
        projects=[],
    )


@pytest.fixture
def empty_evidence_list():
    return []


def test_controlled_optimization_adds_only_verified_skills(
    sales_forecasting_candidate_resume: StructuredResume,
    empty_evidence_list,
):
    """Verify Master Prompt example: 'Worked on sales forecasting' incorporates verified Python and Scikit-learn."""
    optimizer = ControlledResumeOptimizer()
    result = optimizer.optimize_resume(
        resume=sales_forecasting_candidate_resume,
        evidence_list=empty_evidence_list,
        target_requirements=[],
    )

    assert isinstance(result, ControlledOptimizationResult)
    assert len(result.optimized_bullets) >= 1

    first_proposal = result.optimized_bullets[0]
    assert first_proposal.original_bullet == "Worked on sales forecasting."
    assert "Engineered" in first_proposal.optimized_bullet
    assert "sales forecasting" in first_proposal.optimized_bullet.lower()
    # Verified that added technologies are strictly subset of verified skills
    assert all(tech in ["python", "scikit-learn", "pandas"] for tech in [t.lower() for t in first_proposal.verified_technologies_added])
    assert first_proposal.factual_integrity_verified is True
    assert first_proposal.anti_hallucination_check_passed is True


def test_anti_hallucination_rejects_unverified_technology():
    """Verify optimizer rejects any proposal attempting to inject unverified technologies."""
    optimizer = ControlledResumeOptimizer()
    verified_pool = {"python", "pandas"}

    # Attempt to introduce "Kubernetes" when candidate only has Python and Pandas
    is_valid, reason = optimizer.verify_proposal_integrity(
        original="Worked on sales forecasting.",
        proposed="Engineered sales forecasting on Kubernetes clusters.",
        verified_pool=verified_pool,
    )

    assert is_valid is False
    assert "Fabricated technology detected" in reason
    assert "kubernetes" in reason.lower()


def test_metric_preservation_rejects_hallucinated_numbers_and_percentages():
    """Verify optimizer strictly rejects invented percentages or dollar metrics."""
    optimizer = ControlledResumeOptimizer()
    verified_pool = {"python", "scikit-learn"}

    # Attempt to invent "increased accuracy by 45%"
    is_valid_pct, reason_pct = optimizer.verify_proposal_integrity(
        original="Worked on sales forecasting.",
        proposed="Engineered sales forecasting using Python, increasing accuracy by 45%.",
        verified_pool=verified_pool,
    )
    assert is_valid_pct is False
    assert "Fabricated metric or percentage detected" in reason_pct
    assert "45%" in reason_pct

    # Attempt to invent "$2M in revenue"
    is_valid_dollar, reason_dollar = optimizer.verify_proposal_integrity(
        original="Worked on sales forecasting.",
        proposed="Engineered sales forecasting using Python, delivering $2M in value.",
        verified_pool=verified_pool,
    )
    assert is_valid_dollar is False
    assert "Fabricated metric or percentage detected" in reason_dollar


def test_metric_preservation_permits_existing_metrics():
    """Verify metrics already present in the original text are safely preserved."""
    optimizer = ControlledResumeOptimizer()
    verified_pool = {"python", "fastapi"}

    is_valid, reason = optimizer.verify_proposal_integrity(
        original="Responsible for cutting server costs by 30% using python.",
        proposed="Spearheaded cutting server costs by 30% using Python.",
        verified_pool=verified_pool,
    )
    assert is_valid is True


def test_optimization_service_facade(sales_forecasting_candidate_resume: StructuredResume):
    """Verify OptimizationService wraps optimizer and returns validated result."""
    service = OptimizationService()
    result = service.optimize_resume(
        resume=sales_forecasting_candidate_resume,
        evidence_list=[],
        target_requirements=[],
    )

    assert isinstance(result, ControlledOptimizationResult)
    assert "No ungrounded metrics" in result.disclaimer
    assert len(result.supported_skills_referenced) > 0


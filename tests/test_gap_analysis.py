"""Tests for Categorized Gap Analysis, JD-driven severity, and evidence-first compliance."""

import pytest
from backend.app.modules.evidence.schemas import EvidenceSnippet, RequirementEvidence
from backend.app.modules.gaps.engine import GapAnalysisEngine
from backend.app.modules.gaps.schemas import CategorizedGapAnalysisResult, GapSeverity
from backend.app.modules.gaps.service import GapAnalysisService
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement, RequirementCategory, RequirementPriority
from backend.app.modules.matching.schemas import MatchLevel


@pytest.fixture
def sample_analysis_data():
    """Generates requirements and evidence across MATCHED, PARTIAL, MISSING, and AMBIGUOUS levels."""
    req_matched = ExtractedRequirement(
        id="req-py",
        text="Python backend microservices",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["python"],
    )
    ev_matched = RequirementEvidence(
        requirement_id="req-py",
        requirement_text=req_matched.text,
        classification=MatchLevel.MATCHED,
        snippets=[EvidenceSnippet(quote="Built Python microservices", section_source="work_experience")],
        explanation="Direct evidence found.",
        has_evidence=True,
    )

    req_partial = ExtractedRequirement(
        id="req-cloud",
        text="Cloud infrastructure with AWS or GCP",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["aws", "gcp"],
    )
    ev_partial = RequirementEvidence(
        requirement_id="req-cloud",
        requirement_text=req_partial.text,
        classification=MatchLevel.PARTIAL,
        snippets=[EvidenceSnippet(quote="Local Docker deployments", section_source="projects")],
        explanation="Partial evidence found.",
        has_evidence=True,
    )

    req_missing_req = ExtractedRequirement(
        id="req-k8s",
        text="Production Kubernetes cluster administration",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["kubernetes"],
    )
    ev_missing_req = RequirementEvidence(
        requirement_id="req-k8s",
        requirement_text=req_missing_req.text,
        classification=MatchLevel.MISSING,
        snippets=[],
        explanation="No supporting evidence was found in the submitted resume.",
        has_evidence=False,
    )

    req_missing_pref = ExtractedRequirement(
        id="req-rust",
        text="Experience with Rust is a plus",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.PREFERRED,
        normalized_terms=["rust"],
    )
    ev_missing_pref = RequirementEvidence(
        requirement_id="req-rust",
        requirement_text=req_missing_pref.text,
        classification=MatchLevel.MISSING,
        snippets=[],
        explanation="No supporting evidence was found in the submitted resume.",
        has_evidence=False,
    )

    req_ambiguous = ExtractedRequirement(
        id="req-graphql",
        text="GraphQL schema design",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["graphql"],
    )
    ev_ambiguous = RequirementEvidence(
        requirement_id="req-graphql",
        requirement_text=req_ambiguous.text,
        classification=MatchLevel.AMBIGUOUS,
        snippets=[EvidenceSnippet(quote="Basic exposure to GraphQL", section_source="skills")],
        explanation="Ambiguous evidence found.",
        has_evidence=True,
    )

    requirements = [req_matched, req_partial, req_missing_req, req_missing_pref, req_ambiguous]
    evidence_list = [ev_matched, ev_partial, ev_missing_req, ev_missing_pref, ev_ambiguous]
    return requirements, evidence_list


def test_four_way_gap_categorization(sample_analysis_data):
    """Verify requirements are strictly partitioned into matched, partial, missing, and ambiguous."""
    requirements, evidence_list = sample_analysis_data
    engine = GapAnalysisEngine()

    result = engine.analyze_gaps(requirements, evidence_list)
    assert isinstance(result, CategorizedGapAnalysisResult)

    assert len(result.matched) == 1
    assert result.matched[0].requirement_id == "req-py"

    assert len(result.partial) == 1
    assert result.partial[0].requirement_id == "req-cloud"

    assert len(result.missing) == 2
    assert {m.requirement_id for m in result.missing} == {"req-k8s", "req-rust"}

    assert len(result.ambiguous) == 1
    assert result.ambiguous[0].requirement_id == "req-graphql"


def test_jd_driven_severity_derivation(sample_analysis_data):
    """Verify gap severity is strictly derived from JD priority, never invented independently."""
    requirements, evidence_list = sample_analysis_data
    engine = GapAnalysisEngine()

    result = engine.analyze_gaps(requirements, evidence_list)

    # Missing REQUIRED skill must be CRITICAL
    k8s_gap = next(g for g in result.missing if g.requirement_id == "req-k8s")
    assert k8s_gap.priority == RequirementPriority.REQUIRED
    assert k8s_gap.severity == GapSeverity.CRITICAL
    assert k8s_gap.suggested_remediation_type == "acquire_skill"

    # Missing PREFERRED skill must be LOW (not critical, because JD marked it optional)
    rust_gap = next(g for g in result.missing if g.requirement_id == "req-rust")
    assert rust_gap.priority == RequirementPriority.PREFERRED
    assert rust_gap.severity == GapSeverity.LOW
    assert rust_gap.suggested_remediation_type == "acquire_skill"

    # Partial REQUIRED skill must be MODERATE
    cloud_gap = result.partial[0]
    assert cloud_gap.severity == GapSeverity.MODERATE
    assert cloud_gap.suggested_remediation_type == "clarify_experience"

    # Ambiguous REQUIRED skill must be MODERATE
    gql_gap = result.ambiguous[0]
    assert gql_gap.severity == GapSeverity.MODERATE
    assert gql_gap.suggested_remediation_type == "clarify_experience"

    # Matched requirement must be INFO
    matched_item = result.matched[0]
    assert matched_item.severity == GapSeverity.INFO
    assert matched_item.suggested_remediation_type == "highlight_existing"


def test_gap_explanation_evidence_first_compliance(sample_analysis_data):
    """Verify missing gap explanations strictly use non-negotiable absence wording."""
    requirements, evidence_list = sample_analysis_data
    engine = GapAnalysisEngine()

    result = engine.analyze_gaps(requirements, evidence_list)

    for missing_gap in result.missing:
        # Strict Principle 1.1 compliance
        assert missing_gap.gap_explanation == "No supporting evidence was found in the submitted resume."
        assert "does not know" not in missing_gap.gap_explanation.lower()


def test_gap_counts_and_summary_breakdown(sample_analysis_data):
    """Verify aggregated metrics and descriptive summary reflect exact numbers."""
    requirements, evidence_list = sample_analysis_data
    engine = GapAnalysisEngine()

    result = engine.analyze_gaps(requirements, evidence_list)

    assert result.critical_gaps_count == 1  # req-k8s
    assert result.moderate_gaps_count == 2  # req-cloud, req-graphql
    assert result.low_gaps_count == 1       # req-rust

    assert "1 critical" in result.summary
    assert "2 moderate" in result.summary
    assert "1 low" in result.summary


def test_gap_analysis_service_facade(sample_analysis_data):
    """Verify GapAnalysisService wraps engine and exposes clean interface."""
    requirements, evidence_list = sample_analysis_data
    service = GapAnalysisService()

    result = service.analyze_gaps(requirements, evidence_list)
    assert isinstance(result, CategorizedGapAnalysisResult)
    assert len(result.matched) == 1
    assert len(result.missing) == 2


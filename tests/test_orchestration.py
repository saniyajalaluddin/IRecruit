"""Tests for Analysis Orchestrator, versioned prompt templates, and structured workflows."""

import pytest
from backend.app.core.errors import AIProviderError
from backend.app.modules.ai_providers.base import BaseLLMProvider, LLMResponse
from backend.app.modules.ai_providers.mock_provider import MockLLMProvider
from backend.app.modules.evidence.schemas import EvidenceSnippet, RequirementEvidence
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement, RequirementCategory, RequirementPriority
from backend.app.modules.matching.schemas import MatchLevel
from backend.app.modules.orchestration.engine import AnalysisOrchestrator
from backend.app.modules.orchestration.prompts import PROMPT_VERSION, get_prompt_template
from backend.app.modules.orchestration.schemas import (
    EvidenceInterpretationOutput,
    GroundedExplanationOutput,
    RecommendationOutput,
    RequirementInterpretationOutput,
    ResumeImprovementOutput,
)
from backend.app.modules.orchestration.service import OrchestrationService


# ---------------------------------------------------------------------------
# 1. Prompt Template & Versioning Tests
# ---------------------------------------------------------------------------

def test_prompt_template_retrieval():
    """Verify retrieval of all 5 versioned prompt workflows."""
    workflows = [
        "requirement_interpretation",
        "evidence_interpretation",
        "explanation",
        "recommendations",
        "resume_improvement",
    ]
    for wf in workflows:
        sys_tmpl, user_tmpl = get_prompt_template(wf, PROMPT_VERSION)
        assert len(sys_tmpl) > 20
        assert len(user_tmpl) > 10

    # Invalid workflow raises error
    with pytest.raises(AIProviderError, match="not registered"):
        get_prompt_template("unknown_workflow", PROMPT_VERSION)

    # Invalid version raises error
    with pytest.raises(AIProviderError, match="not registered"):
        get_prompt_template("explanation", "v99.0.0")


# ---------------------------------------------------------------------------
# 2. Workflow 1: Requirement Interpretation Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orchestrated_requirement_interpretation():
    """Verify requirement breakdown workflow returns validated schema and metadata."""
    orchestrator = AnalysisOrchestrator(llm_provider=MockLLMProvider())
    req = ExtractedRequirement(
        id="req-fastapi",
        text="Architecting high-throughput REST APIs using FastAPI and Python",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["fastapi", "python"],
    )

    result = await orchestrator.interpret_requirement(req)
    assert isinstance(result.data, RequirementInterpretationOutput)
    assert result.data.requirement_id == "req-fastapi"
    assert result.data.is_strictly_mandatory is True
    assert "fastapi" in [t.lower() for t in result.data.key_technologies]

    # Verify metadata tracking
    meta = result.metadata
    assert meta.workflow_name == "requirement_interpretation"
    assert meta.prompt_version == PROMPT_VERSION
    assert meta.llm_provider == "mock"
    assert meta.latency_ms >= 0


# ---------------------------------------------------------------------------
# 3. Workflow 2: Evidence Interpretation Tests (Evidence First Principle)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orchestrated_evidence_interpretation_matched():
    """Verify evidence interpretation captures verified quotes for MATCHED requirement."""
    orchestrator = AnalysisOrchestrator(llm_provider=MockLLMProvider())
    req = ExtractedRequirement(
        id="req-docker",
        text="Containerization with Docker",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["docker"],
    )
    evidence = RequirementEvidence(
        requirement_id="req-docker",
        requirement_text=req.text,
        classification=MatchLevel.MATCHED,
        snippets=[
            EvidenceSnippet(
                quote="Containerized legacy backend microservices with Docker.",
                section_source="work_experience",
                context="Lead Engineer at CloudScale",
                relevance_score=1.0,
            )
        ],
        explanation="Direct supporting evidence found in work_experience.",
        has_evidence=True,
    )

    result = await orchestrator.interpret_evidence(req, evidence)
    assert isinstance(result.data, EvidenceInterpretationOutput)
    assert result.data.classification == MatchLevel.MATCHED
    assert result.data.evidence_strength >= 0.5
    assert len(result.data.verified_quotes) == 1
    assert "Docker" in result.data.verified_quotes[0]
    assert result.data.is_ambiguous is False


@pytest.mark.asyncio
async def test_orchestrated_evidence_interpretation_missing_strict_guard():
    """Verify missing requirement strictly enforces zero evidence and non-fabrication rationale."""
    orchestrator = AnalysisOrchestrator(llm_provider=MockLLMProvider())
    req = ExtractedRequirement(
        id="req-rust",
        text="Systems programming in Rust",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["rust"],
    )
    evidence = RequirementEvidence(
        requirement_id="req-rust",
        requirement_text=req.text,
        classification=MatchLevel.MISSING,
        snippets=[],
        explanation="No supporting evidence was found in the submitted resume.",
        has_evidence=False,
    )

    result = await orchestrator.interpret_evidence(req, evidence)
    assert result.data.classification == MatchLevel.MISSING
    assert result.data.evidence_strength == 0.0
    assert result.data.verified_quotes == []
    # Strict compliance: never invent claims
    assert result.data.interpretation_rationale == "No supporting evidence was found in the submitted resume."


# ---------------------------------------------------------------------------
# 4. Workflow 3: Grounded Explanation Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orchestrated_grounded_explanation():
    """Verify factual explanation citations and absence rationale."""
    orchestrator = AnalysisOrchestrator(llm_provider=MockLLMProvider())
    req = ExtractedRequirement(
        id="req-pg",
        text="PostgreSQL database query tuning",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["postgresql"],
    )
    evidence = RequirementEvidence(
        requirement_id="req-pg",
        requirement_text=req.text,
        classification=MatchLevel.MATCHED,
        snippets=[
            EvidenceSnippet(
                quote="Tuned PostgreSQL indexes and queries reducing p99 latency.",
                section_source="work_experience",
                context="Senior Backend Developer",
                relevance_score=1.0,
            )
        ],
        explanation="Direct evidence found in candidate's work_experience.",
        has_evidence=True,
    )

    result = await orchestrator.generate_grounded_explanation(req, evidence)
    assert isinstance(result.data, GroundedExplanationOutput)
    assert result.data.confidence_score >= 0.8
    assert len(result.data.cited_sources) == 1
    assert "PostgreSQL" in result.data.cited_sources[0]


# ---------------------------------------------------------------------------
# 5. Workflow 4: Recommendations Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orchestrated_recommendations_no_fabrication():
    """Verify recommendations advise on genuine gaps and highlight verified strengths."""
    orchestrator = AnalysisOrchestrator(llm_provider=MockLLMProvider())
    req_matched = ExtractedRequirement(
        id="req-1",
        text="Python backend APIs",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["python"],
    )
    ev_matched = RequirementEvidence(
        requirement_id="req-1",
        requirement_text=req_matched.text,
        classification=MatchLevel.MATCHED,
        snippets=[EvidenceSnippet(quote="Built Python APIs", section_source="skills")],
        explanation="Evidence found.",
        has_evidence=True,
    )

    req_missing = ExtractedRequirement(
        id="req-2",
        text="Kubernetes cluster admin",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["kubernetes"],
    )
    ev_missing = RequirementEvidence(
        requirement_id="req-2",
        requirement_text=req_missing.text,
        classification=MatchLevel.MISSING,
        snippets=[],
        explanation="No supporting evidence was found in the submitted resume.",
        has_evidence=False,
    )

    result = await orchestrator.generate_recommendations([req_matched, req_missing], [ev_matched, ev_missing])
    assert isinstance(result.data, RecommendationOutput)
    assert len(result.data.recommendations) >= 2
    # Check that all recommendations are marked as grounded
    assert all(r.is_grounded_in_evidence is True for r in result.data.recommendations)


# ---------------------------------------------------------------------------
# 6. Workflow 5: Controlled Resume Improvement Tests (Integrity Guaranteed)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orchestrated_resume_improvement_preserves_facts():
    """Verify resume improvements guarantee factual integrity with zero invented metrics."""
    orchestrator = AnalysisOrchestrator(llm_provider=MockLLMProvider())
    bullets = [
        "Responsible for writing python scripts to process data files.",
        "Helped deploy containers using docker on local machines.",
    ]
    candidate_skills = ["Python", "Docker"]

    result = await orchestrator.generate_resume_improvement(bullets, candidate_skills)
    assert isinstance(result.data, ResumeImprovementOutput)
    assert len(result.data.improvements) == 2

    for imp in result.data.improvements:
        assert imp.factual_integrity_verified is True
        assert imp.original_text in bullets
        assert len(imp.improved_text) > 0


# ---------------------------------------------------------------------------
# 7. Service Facade & Custom LLM Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orchestration_service_facade():
    """Verify OrchestrationService exposes methods and maintains prompt version."""
    service = OrchestrationService()
    assert service.prompt_version == PROMPT_VERSION

    req = ExtractedRequirement(
        id="req-aws",
        text="AWS cloud architecture",
        category=RequirementCategory.TECHNICAL_SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["aws"],
    )
    res = await service.interpret_requirement(req)
    assert res.data.requirement_id == "req-aws"
    assert res.metadata.prompt_version == PROMPT_VERSION


@pytest.mark.asyncio
async def test_orchestration_with_custom_llm_structured_data():
    """Verify orchestrator parses and validates structured data from custom provider."""
    class CustomStructuredLLM(BaseLLMProvider):
        async def generate_text(self, prompt, **kwargs):
            return LLMResponse(content="", provider="custom", model="c-model")

        async def generate_structured(self, prompt, schema, **kwargs):
            if schema == RequirementInterpretationOutput:
                payload = {
                    "requirement_id": "req-custom",
                    "core_competency": "Distributed Systems",
                    "technical_domain": "Cloud Architecture",
                    "depth_level": "expert",
                    "is_strictly_mandatory": True,
                    "key_technologies": ["Kafka", "GRPC"],
                }
            else:
                payload = {}
            return LLMResponse(
                content="",
                structured_data=payload,
                provider="custom",
                model="c-model",
                input_tokens=50,
                output_tokens=30,
                latency_ms=15.0,
            )

    orchestrator = AnalysisOrchestrator(llm_provider=CustomStructuredLLM())
    req = ExtractedRequirement(
        id="req-custom",
        text="Distributed systems using Kafka and gRPC",
        category=RequirementCategory.RESPONSIBILITY,
        priority=RequirementPriority.REQUIRED,
        normalized_terms=["kafka", "grpc"],
    )

    res = await orchestrator.interpret_requirement(req)
    assert res.data.core_competency == "Distributed Systems"
    assert res.data.depth_level == "expert"
    assert res.data.key_technologies == ["Kafka", "GRPC"]
    assert res.metadata.llm_provider == "custom"
    assert res.metadata.input_tokens == 50
    assert res.metadata.output_tokens == 30

"""Structured output schemas for LLM orchestration workflows."""

from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field
from backend.app.modules.matching.schemas import MatchLevel

T = TypeVar("T")


class RequirementInterpretationOutput(BaseModel):
    """Structured interpretation of a job requirement."""
    requirement_id: str = Field(default="", description="Identifier of the requirement")
    core_competency: str = Field(..., description="Primary skill or competency evaluated")
    technical_domain: str = Field(..., description="Engineering domain, e.g. Backend, Frontend, Cloud, Data")
    depth_level: str = Field(..., description="Expected proficiency: introductory, intermediate, advanced, expert")
    is_strictly_mandatory: bool = Field(..., description="True if requirement is hard mandatory based on JD phrasing")
    key_technologies: List[str] = Field(default_factory=list, description="Explicit technologies referenced")


class EvidenceInterpretationOutput(BaseModel):
    """Structured evidence evaluation against requirement."""
    requirement_id: str = Field(default="", description="Requirement evaluated")
    classification: MatchLevel = Field(..., description="MATCHED, PARTIAL, MISSING, or AMBIGUOUS")
    evidence_strength: float = Field(..., ge=0.0, le=1.0, description="Confidence in evidence support")
    verified_quotes: List[str] = Field(default_factory=list, description="Direct verbatim excerpts from resume")
    interpretation_rationale: str = Field(..., description="Evidence-grounded rationale for classification")
    is_ambiguous: bool = Field(default=False, description="True if candidate text is vague or qualified")


class GroundedExplanationOutput(BaseModel):
    """Structured explainable rationale for a match classification."""
    requirement_id: str = Field(default="", description="Requirement identifier")
    summary_explanation: str = Field(..., description="Factual explainable explanation")
    cited_sources: List[str] = Field(default_factory=list, description="Sections or quotes cited")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Mathematical confidence")


class ActionableRecommendationItem(BaseModel):
    """Individual evidence-grounded recommendation for candidate."""
    requirement_id: str = Field(..., description="Associated requirement")
    recommendation_type: str = Field(
        ...,
        description="Category: clarify_ambiguity, highlight_experience, or skill_upskilling",
    )
    action_text: str = Field(..., description="Concrete actionable advice for candidate")
    is_grounded_in_evidence: bool = Field(
        default=True,
        description="Guaranteed that advice does not encourage falsification",
    )


class RecommendationOutput(BaseModel):
    """Collection of evidence-grounded recommendations."""
    recommendations: List[ActionableRecommendationItem] = Field(default_factory=list)
    advisory_notes: Optional[str] = Field(None, description="General strategic advice")


class ResumeImprovementItem(BaseModel):
    """Factual wording enhancement for a single bullet point."""
    original_text: str = Field(..., description="Candidate's original bullet point")
    improved_text: str = Field(..., description="Enhanced phrasing preserving exact facts")
    improvement_rationale: str = Field(..., description="Why new wording is more impactful")
    factual_integrity_verified: bool = Field(
        default=True,
        description="Confirmed zero invented metrics or unverified tools",
    )


class ResumeImprovementOutput(BaseModel):
    """Collection of non-fabricating resume bullet improvements."""
    improvements: List[ResumeImprovementItem] = Field(default_factory=list)
    disclaimer: str = Field(
        default="Wording improvements strictly preserve candidate's original facts with zero invented achievements.",
        description="Integrity disclaimer",
    )


class OrchestrationMetadata(BaseModel):
    """Metadata tracking stage execution and reproducibility."""
    workflow_name: str
    prompt_version: str
    llm_provider: str
    llm_model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0


class OrchestratedStageResult(BaseModel, Generic[T]):
    """Normalized envelope containing typed structured output and execution metadata."""
    data: T
    metadata: OrchestrationMetadata

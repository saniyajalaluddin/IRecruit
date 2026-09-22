"""Explainable component scoring schemas and mathematical breakdown."""

from typing import Dict
from pydantic import BaseModel, Field


class ComponentScores(BaseModel):
    """Deterministic component scores scaled 0.0 to 100.0."""
    technical_skill_alignment: float = Field(..., ge=0.0, le=100.0, description="Match on required/preferred tech skills")
    semantic_relevance: float = Field(..., ge=0.0, le=100.0, description="Semantic concept similarity score")
    evidence_strength: float = Field(..., ge=0.0, le=100.0, description="Depth of verified candidate evidence")
    experience_alignment: float = Field(..., ge=0.0, le=100.0, description="Alignment with required experience level")
    ats_compatibility: float = Field(..., ge=0.0, le=100.0, description="ATS parsing structural cleanliness score")


class AlignmentScoreResult(BaseModel):
    """Complete alignment score calculation with transparent mathematical weights."""
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Deterministic overall weighted score (0-100)")
    components: ComponentScores
    weights: Dict[str, float] = Field(..., description="Weights utilized in composite calculation")
    scoring_version: str = Field(default="v1.0.0", description="Scoring methodology version")
    summary_rationale: str = Field(..., description="Explainable mathematical summary of why the score was achieved")

"""Multi-signal matching schemas and classification levels."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class MatchLevel(str, Enum):
    """Evidence-based match classification."""
    MATCHED = "MATCHED"        # Direct, unambiguous evidence found
    PARTIAL = "PARTIAL"        # Related skills or incomplete evidence found
    MISSING = "MISSING"        # No supporting evidence found in candidate submission
    AMBIGUOUS = "AMBIGUOUS"    # Context is vague, unclear, or contradictory


class MatchSignalBreakdown(BaseModel):
    """Breakdown of individual matching signals."""
    exact_match: bool = Field(default=False, description="Exact literal string/term match")
    normalized_match: bool = Field(default=False, description="Synonym / alias normalized match")
    semantic_similarity: float = Field(default=0.0, ge=0.0, le=1.0, description="Embedding vector cosine similarity")
    contextual_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Contextual alignment score")
    combined_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Deterministic blended score")


class RequirementMatchResult(BaseModel):
    """Matching determination for an individual requirement."""
    requirement_id: str
    requirement_text: str
    match_level: MatchLevel
    signals: MatchSignalBreakdown
    matched_resume_terms: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

"""Evidence-grounded recommendation schemas."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class RecommendationType(str, Enum):
    """Categorization of evidence-grounded recommendations."""
    CLARIFY_EXPERIENCE = "clarify_experience"
    IMPROVE_WORDING = "improve_wording"
    RESOLVE_AMBIGUITY = "resolve_ambiguity"
    RESTRUCTURE_SECTION = "restructure_section"
    KEYWORD_ALIGNMENT = "keyword_alignment"
    ATS_COMPATIBILITY = "ats_compatibility"


class RecommendationItem(BaseModel):
    """Individual actionable recommendation grounded in real evidence."""
    id: str = Field(..., description="Unique recommendation identifier")
    type: RecommendationType
    requirement_id: Optional[str] = Field(None, description="Associated JD requirement if applicable")
    title: str = Field(..., description="Concise recommendation title")
    rationale: str = Field(..., description="Why this recommendation is made based on the JD gap")
    current_evidence_quote: Optional[str] = Field(
        None, description="Source quote from resume being refined"
    )
    suggested_revision: Optional[str] = Field(
        None, description="Refined text proposal strictly based on candidate evidence (no fabrication)"
    )
    is_evidence_grounded: bool = Field(
        default=True, description="Strict guarantee that suggestion does not fabricate experience"
    )

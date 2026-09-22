"""Schemas for categorized skill and requirement gap analysis."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.modules.job_descriptions.schemas import RequirementCategory, RequirementPriority
from backend.app.modules.matching.schemas import MatchLevel


class GapSeverity(str, Enum):
    """Gap severity strictly derived from JD-defined requirement priority."""
    CRITICAL = "CRITICAL"    # Missing REQUIRED requirement
    MODERATE = "MODERATE"    # Partial or ambiguous REQUIRED requirement
    LOW = "LOW"              # Missing or partial PREFERRED requirement
    INFO = "INFO"            # Fully MATCHED requirement (no gap)


class RequirementGapItem(BaseModel):
    """Categorized gap detail for a single JD requirement."""
    requirement_id: str
    requirement_text: str
    category: RequirementCategory
    priority: RequirementPriority
    match_level: MatchLevel
    severity: GapSeverity
    gap_explanation: str
    suggested_remediation_type: str = Field(
        ...,
        description="Remediation category: acquire_skill, clarify_experience, or highlight_existing",
    )


class CategorizedGapAnalysisResult(BaseModel):
    """Complete categorized breakdown of matched, partial, missing, and ambiguous requirements."""
    matched: List[RequirementGapItem] = Field(default_factory=list, description="Directly supported requirements")
    partial: List[RequirementGapItem] = Field(default_factory=list, description="Partially supported requirements")
    missing: List[RequirementGapItem] = Field(default_factory=list, description="Requirements with no supporting evidence")
    ambiguous: List[RequirementGapItem] = Field(default_factory=list, description="Vague or qualified candidate evidence")
    critical_gaps_count: int = Field(default=0, description="Count of missing REQUIRED skills")
    moderate_gaps_count: int = Field(default=0, description="Count of partial/ambiguous REQUIRED skills")
    low_gaps_count: int = Field(default=0, description="Count of missing/partial PREFERRED skills")
    summary: str = Field(..., description="Deterministic gap analysis summary")

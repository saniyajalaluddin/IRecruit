"""Schemas for controlled, evidence-grounded resume optimization."""

from typing import List, Optional
from pydantic import BaseModel, Field


class OptimizedBulletProposal(BaseModel):
    """Proposal for an enhanced resume bullet strictly constrained to verified candidate evidence."""
    original_bullet: str = Field(..., description="Candidate's original bullet point")
    optimized_bullet: str = Field(..., description="Enhanced bullet point with active phrasing and verified context")
    target_requirement_id: Optional[str] = Field(None, description="JD requirement addressed by this optimization")
    verified_technologies_added: List[str] = Field(
        default_factory=list,
        description="Technologies incorporated that are strictly proven in candidate source evidence",
    )
    rationale: str = Field(..., description="Why the revision is more effective and how it remains strictly factual")
    factual_integrity_verified: bool = Field(
        default=True,
        description="Confirmed zero fabricated tools, metrics, or responsibilities",
    )
    anti_hallucination_check_passed: bool = Field(
        default=True,
        description="Passed anti-hallucination verification against source evidence pool",
    )


class ControlledOptimizationResult(BaseModel):
    """Result of controlled resume optimization enforcing zero fabrication."""
    optimized_bullets: List[OptimizedBulletProposal] = Field(default_factory=list)
    supported_skills_referenced: List[str] = Field(
        default_factory=list,
        description="Candidate's verified skills utilized across optimizations",
    )
    rejected_proposals_count: int = Field(
        default=0,
        description="Number of candidate proposals rejected for attempting to introduce unverified claims",
    )
    disclaimer: str = Field(
        default=(
            "Wording enhancements incorporate only verified candidate evidence. "
            "No ungrounded metrics, percentages, tools, or responsibilities were invented."
        ),
        description="Strict non-fabrication guarantee disclaimer",
    )


"""Schemas for Analysis and Anonymous Analysis workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class AnonymousAnalysisRequest(BaseModel):
    """Payload for submitting an anonymous resume alignment analysis."""
    resume_text: str = Field(..., min_length=20, description="Raw or parsed resume text")
    job_description_text: Optional[str] = Field(default=None, description="Target job description text")
    job_description: Optional[str] = Field(default=None, description="Alternative field name for job description")
    job_title: Optional[str] = Field(default="Target Role", description="Optional job title")
    company_name: Optional[str] = Field(default=None, description="Optional target company name")
    session_id: Optional[str] = Field(default=None, description="Client session identifier")

    @model_validator(mode="before")
    @classmethod
    def validate_job_description_present(cls, data: Any) -> Any:
        if isinstance(data, dict):
            jd = data.get("job_description_text") or data.get("job_description")
            if not jd or len(str(jd).strip()) < 20:
                raise ValueError("Job description text must be at least 20 characters long.")
            data["job_description_text"] = jd
        return data


class AnonymousAnalysisResponse(BaseModel):
    """Result envelope returned for anonymous quick analysis."""
    analysis_id: str
    session_id: str
    overall_score: float
    grade: str
    component_scores: Dict[str, float]
    requirements_matched: int
    requirements_partial: int
    requirements_missing: int
    top_gaps: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    ats_compatibility: Dict[str, Any]
    scoring_version: str
    created_at: datetime
    expires_at: datetime
    is_claimed: bool = False
    evidence: List[Dict[str, Any]] = Field(default_factory=list)


class ClaimAnalysisRequest(BaseModel):
    """Payload to claim and migrate an anonymous analysis to an authenticated account."""
    session_id: str = Field(..., description="Session identifier used during anonymous submission")


class ClaimAnalysisResponse(BaseModel):
    """Response confirming successful ownership transfer of an analysis."""
    analysis_id: str
    claimed: bool
    user_id: str
    claimed_at: datetime


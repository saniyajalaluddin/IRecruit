"""Schemas for resume versioning, iteration tracking, and delta comparison."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ResumeVersionCreate(BaseModel):
    """Payload to create a new revision of a resume."""
    raw_text: str = Field(..., min_length=20, description="Revised resume plaintext")
    revision_notes: Optional[str] = Field(None, description="Optional notes explaining changes")


class ResumeVersionItem(BaseModel):
    """Summarized metadata for a resume version."""
    id: str
    version_number: int
    character_count: int
    word_count: int
    created_at: datetime


class ResumeVersionListResponse(BaseModel):
    """Listing of all revisions for a candidate resume."""
    resume_id: str
    total_versions: int
    versions: List[ResumeVersionItem]


class VersionDiffItem(BaseModel):
    """Delta line or section between two versions."""
    change_type: str  # "added", "removed", "unchanged"
    text: str


class ScoreProgression(BaseModel):
    """Comparative score delta if analyses exist for both versions."""
    base_score: float
    target_score: float
    delta: float
    base_grade: str
    target_grade: str


class VersionComparisonResponse(BaseModel):
    """Comprehensive comparison between two resume versions."""
    resume_id: str
    base_version_number: int
    target_version_number: int
    text_diffs: List[VersionDiffItem]
    skills_added: List[str]
    skills_removed: List[str]
    score_progression: Optional[ScoreProgression] = None

"""Schemas for user dashboard, analytics metrics, and analysis history."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AnalysisHistoryItem(BaseModel):
    """Summarized historical analysis item for listing and dashboard views."""
    id: str
    job_title: Optional[str] = "Target Role"
    company_name: Optional[str] = None
    overall_score: float
    grade: str
    component_scores: Dict[str, float]
    scoring_version: str
    created_at: datetime


class AnalysisHistoryResponse(BaseModel):
    """Enforce latest 5 saved analyses for free tier with pagination metadata."""
    items: List[AnalysisHistoryItem] = Field(default_factory=list)
    total_saved: int = Field(..., description="Total analyses currently stored for user")
    max_allowed: int = Field(default=5, description="Maximum visible saved analyses allowed by tier")
    tier: str = Field(default="free")


class DashboardMetrics(BaseModel):
    """Aggregated statistics for authenticated candidate dashboard."""
    total_analyses_run: int = Field(default=0)
    average_score: float = Field(default=0.0)
    top_missing_skills: List[str] = Field(default_factory=list)
    tier: str = Field(default="free")
    saved_analyses_count: int = Field(default=0)
    max_saved_analyses: int = Field(default=5)
    latest_analysis: Optional[AnalysisHistoryItem] = None

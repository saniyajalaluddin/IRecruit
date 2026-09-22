"""Schemas for AI Cost and Usage Controls."""

from __future__ import annotations

from typing import Dict, Optional
from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token consumption and monetary cost for an individual AI call."""
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)
    latency_ms: float = Field(default=0.0, ge=0.0)


class UsageQuota(BaseModel):
    """User or tier token and monetary spending budget."""
    daily_token_limit: int = Field(default=50_000, description="Max tokens per day")
    monthly_cost_limit_usd: float = Field(default=5.00, description="Max spend in USD per month")
    tokens_used_today: int = Field(default=0, ge=0)
    cost_used_this_month: float = Field(default=0.0, ge=0.0)


class UsageRecordCreate(BaseModel):
    """Payload to persist an AI usage transaction."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    analysis_id: Optional[str] = None
    provider_name: str
    model_name: str
    input_tokens: int = Field(..., ge=0)
    output_tokens: int = Field(default=0, ge=0)
    latency_ms: float = Field(default=0.0, ge=0.0)


class UsageSummary(BaseModel):
    """Aggregated usage statistics across multiple operations."""
    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    model_breakdown: Dict[str, Dict[str, float]] = Field(default_factory=dict)


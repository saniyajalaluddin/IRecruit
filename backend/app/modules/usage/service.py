"""AI Usage and Cost Tracking Service."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.core.errors import AppException
from backend.app.models.usage import UsageRecord
from backend.app.modules.usage.pricing import calculate_cost
from backend.app.modules.usage.schemas import (
    TokenUsage,
    UsageQuota,
    UsageRecordCreate,
    UsageSummary,
)


class QuotaExceededError(AppException):
    """Raised when an AI token or monetary spend budget is exceeded."""

    def __init__(self, message: str = "AI consumption quota exceeded.", details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=429,
            code="AI_QUOTA_EXCEEDED",
            details=details,
        )


class UsageTrackingService:
    """Manages AI token accounting, cost calculations, and budget enforcement."""

    def __init__(self):
        # In-memory quota ledger for fast low-latency checks
        # identifier -> UsageQuota
        self._quotas: Dict[str, UsageQuota] = defaultdict(UsageQuota)
        # identifier -> list of TokenUsage records
        self._history: Dict[str, List[TokenUsage]] = defaultdict(list)

    def set_quota(self, identifier: str, quota: UsageQuota) -> None:
        """Assign custom quota ceiling for a user or tenant tier."""
        self._quotas[identifier] = quota

    def get_quota(self, identifier: str) -> UsageQuota:
        """Retrieve quota status for a user or tenant."""
        return self._quotas[identifier]

    def check_quota(self, identifier: str, projected_tokens: int = 0) -> None:
        """Validate whether the pending AI call would violate spending/token limits."""
        quota = self._quotas.get(identifier)
        if not quota:
            quota = UsageQuota()
            self._quotas[identifier] = quota

        # Check daily token limit
        if (quota.tokens_used_today + projected_tokens) > quota.daily_token_limit:
            raise QuotaExceededError(
                message=f"Daily AI token limit of {quota.daily_token_limit:,} tokens exceeded.",
                details={
                    "current_usage": quota.tokens_used_today,
                    "projected": projected_tokens,
                    "limit": quota.daily_token_limit,
                },
            )

        # Check monthly cost limit
        if quota.cost_used_this_month >= quota.monthly_cost_limit_usd:
            raise QuotaExceededError(
                message=f"Monthly AI spend budget of ${quota.monthly_cost_limit_usd:.2f} exceeded.",
                details={
                    "current_cost_usd": quota.cost_used_this_month,
                    "limit_usd": quota.monthly_cost_limit_usd,
                },
            )

    def record_usage(
        self,
        record_in: UsageRecordCreate,
        db: Optional[Session] = None,
    ) -> TokenUsage:
        """Record token consumption, compute cost, update budgets, and persist."""
        cost_usd = calculate_cost(
            model_name=record_in.model_name,
            input_tokens=record_in.input_tokens,
            output_tokens=record_in.output_tokens,
        )
        total_tokens = record_in.input_tokens + record_in.output_tokens

        usage = TokenUsage(
            input_tokens=record_in.input_tokens,
            output_tokens=record_in.output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost_usd,
            latency_ms=record_in.latency_ms,
        )

        identifier = record_in.user_id or record_in.session_id or "anonymous"
        quota = self._quotas[identifier]
        quota.tokens_used_today += total_tokens
        quota.cost_used_this_month = round(quota.cost_used_this_month + cost_usd, 6)

        self._history[identifier].append(usage)

        # Persist to database if session provided
        if db:
            db_record = UsageRecord(
                user_id=record_in.user_id,
                session_id=record_in.session_id,
                analysis_id=record_in.analysis_id,
                provider_name=record_in.provider_name,
                model_name=record_in.model_name,
                input_tokens=record_in.input_tokens,
                output_tokens=record_in.output_tokens,
                total_tokens=total_tokens,
                latency_ms=record_in.latency_ms,
            )
            db.add(db_record)
            db.commit()
            db.refresh(db_record)

        return usage

    def get_summary(self, identifier: str) -> UsageSummary:
        """Generate usage aggregate summary for an identifier."""
        history = self._history.get(identifier, [])
        total_calls = len(history)
        total_in = sum(u.input_tokens for u in history)
        total_out = sum(u.output_tokens for u in history)
        total_cost = sum(u.estimated_cost_usd for u in history)

        return UsageSummary(
            total_calls=total_calls,
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            total_tokens=total_in + total_out,
            total_cost_usd=round(total_cost, 6),
        )


# Global singleton instance
usage_service = UsageTrackingService()


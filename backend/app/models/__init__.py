"""Database domain models package."""

from backend.app.models.user import User
from backend.app.models.resume import Resume, ResumeVersion
from backend.app.models.job_description import JobDescription
from backend.app.models.analysis import Analysis
from backend.app.models.requirement import Requirement
from backend.app.models.evidence import Evidence
from backend.app.models.recommendation import Recommendation
from backend.app.models.audit import AuditEvent
from backend.app.models.usage import UsageRecord
from backend.app.models.entitlement import Entitlement

__all__ = [
    "User",
    "Resume",
    "ResumeVersion",
    "JobDescription",
    "Analysis",
    "Requirement",
    "Evidence",
    "Recommendation",
    "AuditEvent",
    "UsageRecord",
    "Entitlement",
]

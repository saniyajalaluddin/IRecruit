"""Resume versioning module initialization."""

from backend.app.modules.versioning.schemas import (
    ResumeVersionCreate,
    ResumeVersionItem,
    ResumeVersionListResponse,
    ScoreProgression,
    VersionComparisonResponse,
    VersionDiffItem,
)
from backend.app.modules.versioning.service import (
    ResumeVersioningService,
    resume_versioning_service,
)

__all__ = [
    "ResumeVersionCreate",
    "ResumeVersionItem",
    "ResumeVersionListResponse",
    "ScoreProgression",
    "VersionComparisonResponse",
    "VersionDiffItem",
    "ResumeVersioningService",
    "resume_versioning_service",
]


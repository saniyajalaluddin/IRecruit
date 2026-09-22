"""Gap analysis module initialization."""

from backend.app.modules.gaps.engine import GapAnalysisEngine
from backend.app.modules.gaps.schemas import (
    CategorizedGapAnalysisResult,
    GapSeverity,
    RequirementGapItem,
)
from backend.app.modules.gaps.service import (
    GapAnalysisService,
    GapAnalysisServiceInterface,
)

__all__ = [
    "GapAnalysisEngine",
    "GapAnalysisService",
    "GapAnalysisServiceInterface",
    "CategorizedGapAnalysisResult",
    "RequirementGapItem",
    "GapSeverity",
]

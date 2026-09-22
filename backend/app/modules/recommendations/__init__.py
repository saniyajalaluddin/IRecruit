"""Recommendations module initialization."""

from backend.app.modules.recommendations.engine import RecommendationEngine
from backend.app.modules.recommendations.schemas import (
    RecommendationItem,
    RecommendationType,
)
from backend.app.modules.recommendations.service import (
    RecommendationEngineInterface,
    RecommendationService,
)

__all__ = [
    "RecommendationType",
    "RecommendationItem",
    "RecommendationEngineInterface",
    "RecommendationEngine",
    "RecommendationService",
]

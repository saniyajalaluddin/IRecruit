"""Recommendations module initialization."""

from backend.app.modules.recommendations.schemas import RecommendationItem, RecommendationType
from backend.app.modules.recommendations.service import RecommendationEngineInterface

__all__ = ["RecommendationItem", "RecommendationType", "RecommendationEngineInterface"]

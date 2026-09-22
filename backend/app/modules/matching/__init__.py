"""Matching module initialization."""

from backend.app.modules.matching.schemas import MatchLevel, MatchSignalBreakdown, RequirementMatchResult
from backend.app.modules.matching.service import MatchingEngineInterface

__all__ = ["MatchLevel", "MatchSignalBreakdown", "RequirementMatchResult", "MatchingEngineInterface"]

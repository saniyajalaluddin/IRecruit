"""Matching and normalization module initialization."""

from backend.app.modules.matching.normalizer import SkillNormalizer
from backend.app.modules.matching.schemas import MatchLevel, MatchSignalBreakdown, RequirementMatchResult
from backend.app.modules.matching.service import MatchingEngineInterface
from backend.app.modules.matching.taxonomy import CANONICAL_SKILL_MAP, UNRELATED_PAIRS_CHECK

__all__ = [
    "MatchLevel",
    "MatchSignalBreakdown",
    "RequirementMatchResult",
    "MatchingEngineInterface",
    "SkillNormalizer",
    "CANONICAL_SKILL_MAP",
    "UNRELATED_PAIRS_CHECK",
]

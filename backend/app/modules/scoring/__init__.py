"""Scoring module initialization."""

from backend.app.modules.scoring.engine import (
    DEFAULT_COMPONENT_WEIGHTS,
    SCORING_VERSION,
    ScoringEngine,
)
from backend.app.modules.scoring.schemas import AlignmentScoreResult, ComponentScores
from backend.app.modules.scoring.service import ScoringEngineInterface, ScoringService

__all__ = [
    "ComponentScores",
    "AlignmentScoreResult",
    "ScoringEngineInterface",
    "ScoringEngine",
    "ScoringService",
    "SCORING_VERSION",
    "DEFAULT_COMPONENT_WEIGHTS",
]

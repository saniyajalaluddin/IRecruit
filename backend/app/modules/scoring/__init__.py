"""Scoring module initialization."""

from backend.app.modules.scoring.schemas import AlignmentScoreResult, ComponentScores
from backend.app.modules.scoring.service import ScoringEngineInterface

__all__ = ["AlignmentScoreResult", "ComponentScores", "ScoringEngineInterface"]

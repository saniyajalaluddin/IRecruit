"""Deterministic scoring engine protocol and service implementation."""

from typing import Dict, List, Optional, Protocol
from backend.app.modules.evidence.schemas import RequirementEvidence
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement
from backend.app.modules.resumes.schemas import StructuredResume
from backend.app.modules.scoring.engine import DEFAULT_COMPONENT_WEIGHTS, SCORING_VERSION, ScoringEngine
from backend.app.modules.scoring.schemas import AlignmentScoreResult


class ScoringEngineInterface(Protocol):
    """Protocol for calculating deterministic, explainable alignment scores."""

    def calculate_score(
        self,
        requirements: List[ExtractedRequirement],
        evidence: List[RequirementEvidence],
        resume: StructuredResume,
        ats_score: float,
    ) -> AlignmentScoreResult:
        """Calculates component and overall alignment scores deterministically."""
        ...


class ScoringService:
    """Service providing deterministic, explainable component alignment scoring."""

    def __init__(
        self,
        engine: Optional[ScoringEngine] = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.engine = engine or ScoringEngine(weights=weights)

    @property
    def version(self) -> str:
        return self.engine.version

    def calculate_score(
        self,
        requirements: List[ExtractedRequirement],
        evidence: List[RequirementEvidence],
        resume: StructuredResume,
        ats_score: float = 85.0,
    ) -> AlignmentScoreResult:
        """Computes deterministic overall and component alignment scores."""
        return self.engine.calculate_score(
            requirements=requirements,
            evidence=evidence,
            resume=resume,
            ats_score=ats_score,
        )

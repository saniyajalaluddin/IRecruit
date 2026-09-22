"""Deterministic scoring engine protocol and default implementation."""

from typing import List, Protocol
from backend.app.modules.evidence.schemas import RequirementEvidence
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement
from backend.app.modules.resumes.schemas import StructuredResume
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

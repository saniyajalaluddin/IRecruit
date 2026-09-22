"""Gap analysis service implementation."""

from typing import List, Optional, Protocol
from backend.app.modules.evidence.schemas import RequirementEvidence
from backend.app.modules.gaps.engine import GapAnalysisEngine
from backend.app.modules.gaps.schemas import CategorizedGapAnalysisResult
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement


class GapAnalysisServiceInterface(Protocol):
    """Protocol for executing categorized gap analysis."""

    def analyze_gaps(
        self,
        requirements: List[ExtractedRequirement],
        evidence_list: List[RequirementEvidence],
    ) -> CategorizedGapAnalysisResult:
        ...


class GapAnalysisService:
    """Service providing categorized requirement and skill gap analysis."""

    def __init__(self, engine: Optional[GapAnalysisEngine] = None):
        self.engine = engine or GapAnalysisEngine()

    def analyze_gaps(
        self,
        requirements: List[ExtractedRequirement],
        evidence_list: List[RequirementEvidence],
    ) -> CategorizedGapAnalysisResult:
        """Categorizes gaps based strictly on JD-defined requirements."""
        return self.engine.analyze_gaps(requirements, evidence_list)

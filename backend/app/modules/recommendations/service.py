"""Recommendation engine service implementation."""

from typing import List, Optional, Protocol
from backend.app.modules.evidence.schemas import RequirementEvidence
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement
from backend.app.modules.recommendations.engine import RecommendationEngine
from backend.app.modules.recommendations.schemas import RecommendationItem
from backend.app.modules.resumes.schemas import StructuredResume


class RecommendationEngineInterface(Protocol):
    """Protocol for generating grounded resume recommendations."""

    async def generate_recommendations(
        self,
        requirements: List[ExtractedRequirement],
        evidence: List[RequirementEvidence],
        resume: StructuredResume,
    ) -> List[RecommendationItem]:
        """Generates evidence-grounded recommendations without fabricating unstated claims."""
        ...


class RecommendationService:
    """Service providing targeted, evidence-grounded resume optimization recommendations."""

    def __init__(self, engine: Optional[RecommendationEngine] = None):
        self.engine = engine or RecommendationEngine()

    async def generate_recommendations(
        self,
        requirements: List[ExtractedRequirement],
        evidence: List[RequirementEvidence],
        resume: StructuredResume,
    ) -> List[RecommendationItem]:
        """Generates recommendations strictly grounded in JD requirements, candidate evidence, and gaps."""
        return await self.engine.generate_recommendations(
            requirements=requirements,
            evidence=evidence,
            resume=resume,
        )

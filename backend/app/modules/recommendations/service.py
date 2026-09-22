"""Recommendation engine service protocol."""

from typing import List, Protocol
from backend.app.modules.evidence.schemas import RequirementEvidence
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement
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

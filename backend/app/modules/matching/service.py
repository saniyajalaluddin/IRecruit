"""Matching engine service protocol."""

from typing import List, Protocol
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement
from backend.app.modules.matching.schemas import RequirementMatchResult
from backend.app.modules.resumes.schemas import StructuredResume


class MatchingEngineInterface(Protocol):
    """Protocol for executing multi-signal requirement matching."""

    async def match_requirements(
        self,
        requirements: List[ExtractedRequirement],
        resume: StructuredResume,
    ) -> List[RequirementMatchResult]:
        """Matches a collection of JD requirements against parsed resume content."""
        ...

"""Matching engine service implementation."""

from typing import List, Optional, Protocol
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement
from backend.app.modules.matching.engine import SemanticMatchingEngine
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


class MatchingService:
    """Service providing multi-signal semantic and deterministic requirement matching."""

    def __init__(self, engine: Optional[SemanticMatchingEngine] = None):
        self.engine = engine or SemanticMatchingEngine()

    @property
    def metadata(self) -> dict:
        """Returns embedding metadata and matching engine version."""
        return self.engine.embedding_metadata

    async def match_requirements(
        self,
        requirements: List[ExtractedRequirement],
        resume: StructuredResume,
    ) -> List[RequirementMatchResult]:
        """Evaluates JD requirements against structured candidate resume data."""
        return await self.engine.match_requirements(requirements=requirements, resume=resume)

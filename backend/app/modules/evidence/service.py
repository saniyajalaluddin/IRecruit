"""Evidence engine service implementation."""

from typing import List, Optional, Protocol
from backend.app.modules.evidence.engine import EvidenceEngine
from backend.app.modules.evidence.schemas import RequirementEvidence
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement
from backend.app.modules.matching.schemas import RequirementMatchResult
from backend.app.modules.resumes.schemas import StructuredResume


class EvidenceEngineInterface(Protocol):
    """Protocol for extracting and linking evidence to requirements."""

    async def evaluate_evidence(
        self,
        requirements: List[ExtractedRequirement],
        matches: List[RequirementMatchResult],
        resume: StructuredResume,
    ) -> List[RequirementEvidence]:
        """Maps each requirement to grounded candidate evidence or explicit absence of evidence."""
        ...


class EvidenceService:
    """Service providing grounded evidence extraction and verification."""

    def __init__(self, engine: Optional[EvidenceEngine] = None):
        self.engine = engine or EvidenceEngine()

    async def evaluate_evidence(
        self,
        requirements: List[ExtractedRequirement],
        matches: List[RequirementMatchResult],
        resume: StructuredResume,
    ) -> List[RequirementEvidence]:
        """Maps requirements and match determinations to verified candidate evidence trails."""
        return await self.engine.evaluate_evidence(
            requirements=requirements,
            matches=matches,
            resume=resume,
        )

"""Evidence engine service protocol."""

from typing import List, Protocol
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

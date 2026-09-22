"""Evidence module initialization."""

from backend.app.modules.evidence.engine import NO_EVIDENCE_EXPLANATION, EvidenceEngine
from backend.app.modules.evidence.schemas import EvidenceSnippet, RequirementEvidence
from backend.app.modules.evidence.service import EvidenceEngineInterface, EvidenceService

__all__ = [
    "EvidenceSnippet",
    "RequirementEvidence",
    "EvidenceEngineInterface",
    "EvidenceEngine",
    "EvidenceService",
    "NO_EVIDENCE_EXPLANATION",
]

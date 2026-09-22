"""Evidence module initialization."""

from backend.app.modules.evidence.schemas import EvidenceSnippet, RequirementEvidence
from backend.app.modules.evidence.service import EvidenceEngineInterface

__all__ = ["EvidenceSnippet", "RequirementEvidence", "EvidenceEngineInterface"]

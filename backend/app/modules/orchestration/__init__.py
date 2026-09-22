"""Orchestration module initialization."""

from backend.app.modules.orchestration.engine import AnalysisOrchestrator
from backend.app.modules.orchestration.prompts import (
    PROMPT_REGISTRY,
    PROMPT_VERSION,
    get_prompt_template,
)
from backend.app.modules.orchestration.schemas import (
    ActionableRecommendationItem,
    EvidenceInterpretationOutput,
    GroundedExplanationOutput,
    OrchestratedStageResult,
    OrchestrationMetadata,
    RecommendationOutput,
    RequirementInterpretationOutput,
    ResumeImprovementItem,
    ResumeImprovementOutput,
)
from backend.app.modules.orchestration.service import (
    OrchestrationService,
    OrchestrationServiceInterface,
)

__all__ = [
    "AnalysisOrchestrator",
    "OrchestrationService",
    "OrchestrationServiceInterface",
    "PROMPT_VERSION",
    "PROMPT_REGISTRY",
    "get_prompt_template",
    "RequirementInterpretationOutput",
    "EvidenceInterpretationOutput",
    "GroundedExplanationOutput",
    "ActionableRecommendationItem",
    "RecommendationOutput",
    "ResumeImprovementItem",
    "ResumeImprovementOutput",
    "OrchestrationMetadata",
    "OrchestratedStageResult",
]

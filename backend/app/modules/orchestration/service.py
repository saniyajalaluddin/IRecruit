"""Orchestration service implementation."""

from typing import List, Optional, Protocol
from backend.app.modules.evidence.schemas import RequirementEvidence
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement
from backend.app.modules.orchestration.engine import AnalysisOrchestrator
from backend.app.modules.orchestration.schemas import (
    EvidenceInterpretationOutput,
    GroundedExplanationOutput,
    OrchestratedStageResult,
    RecommendationOutput,
    RequirementInterpretationOutput,
    ResumeImprovementOutput,
)


class OrchestrationServiceInterface(Protocol):
    """Protocol for LLM analysis orchestration workflows."""

    async def interpret_requirement(
        self, requirement: ExtractedRequirement, context: Optional[str] = None
    ) -> OrchestratedStageResult[RequirementInterpretationOutput]:
        ...

    async def interpret_evidence(
        self, requirement: ExtractedRequirement, evidence: RequirementEvidence
    ) -> OrchestratedStageResult[EvidenceInterpretationOutput]:
        ...

    async def generate_grounded_explanation(
        self, requirement: ExtractedRequirement, evidence: RequirementEvidence
    ) -> OrchestratedStageResult[GroundedExplanationOutput]:
        ...

    async def generate_recommendations(
        self, requirements: List[ExtractedRequirement], evidence_list: List[RequirementEvidence]
    ) -> OrchestratedStageResult[RecommendationOutput]:
        ...

    async def generate_resume_improvement(
        self, original_bullets: List[str], candidate_skills: List[str]
    ) -> OrchestratedStageResult[ResumeImprovementOutput]:
        ...


class OrchestrationService:
    """Service facade providing structured LLM orchestration for all analysis workflows."""

    def __init__(self, orchestrator: Optional[AnalysisOrchestrator] = None):
        self.orchestrator = orchestrator or AnalysisOrchestrator()

    @property
    def prompt_version(self) -> str:
        return self.orchestrator.prompt_version

    async def interpret_requirement(
        self, requirement: ExtractedRequirement, context: Optional[str] = None
    ) -> OrchestratedStageResult[RequirementInterpretationOutput]:
        return await self.orchestrator.interpret_requirement(requirement, context)

    async def interpret_evidence(
        self, requirement: ExtractedRequirement, evidence: RequirementEvidence
    ) -> OrchestratedStageResult[EvidenceInterpretationOutput]:
        return await self.orchestrator.interpret_evidence(requirement, evidence)

    async def generate_grounded_explanation(
        self, requirement: ExtractedRequirement, evidence: RequirementEvidence
    ) -> OrchestratedStageResult[GroundedExplanationOutput]:
        return await self.orchestrator.generate_grounded_explanation(requirement, evidence)

    async def generate_recommendations(
        self, requirements: List[ExtractedRequirement], evidence_list: List[RequirementEvidence]
    ) -> OrchestratedStageResult[RecommendationOutput]:
        return await self.orchestrator.generate_recommendations(requirements, evidence_list)

    async def generate_resume_improvement(
        self, original_bullets: List[str], candidate_skills: List[str]
    ) -> OrchestratedStageResult[ResumeImprovementOutput]:
        return await self.orchestrator.generate_resume_improvement(original_bullets, candidate_skills)

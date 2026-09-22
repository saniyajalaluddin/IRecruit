"""Controlled optimization service implementation."""

from typing import List, Optional, Protocol
from backend.app.modules.evidence.schemas import RequirementEvidence
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement
from backend.app.modules.optimization.engine import ControlledResumeOptimizer
from backend.app.modules.optimization.schemas import ControlledOptimizationResult
from backend.app.modules.resumes.schemas import StructuredResume


class OptimizationServiceInterface(Protocol):
    """Protocol for controlled, evidence-grounded resume optimization."""

    def optimize_resume(
        self,
        resume: StructuredResume,
        evidence_list: List[RequirementEvidence],
        target_requirements: List[ExtractedRequirement],
    ) -> ControlledOptimizationResult:
        ...


class OptimizationService:
    """Service providing controlled, non-fabricating resume optimization."""

    def __init__(self, optimizer: Optional[ControlledResumeOptimizer] = None):
        self.optimizer = optimizer or ControlledResumeOptimizer()

    def optimize_resume(
        self,
        resume: StructuredResume,
        evidence_list: List[RequirementEvidence],
        target_requirements: List[ExtractedRequirement],
    ) -> ControlledOptimizationResult:
        """Optimizes resume wording strictly within candidate-provided source evidence."""
        return self.optimizer.optimize_resume(resume, evidence_list, target_requirements)


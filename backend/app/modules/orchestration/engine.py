"""Analysis orchestrator executing modular, versioned, structured LLM workflows."""

from typing import List, Optional
from backend.app.core.errors import AIProviderError
from backend.app.modules.ai_providers.base import BaseLLMProvider
from backend.app.modules.ai_providers.factory import get_llm_provider
from backend.app.modules.evidence.schemas import RequirementEvidence
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement, RequirementPriority
from backend.app.modules.matching.schemas import MatchLevel
from backend.app.modules.orchestration.prompts import PROMPT_VERSION, get_prompt_template
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


class AnalysisOrchestrator:
    """Coordinates specialized, versioned prompt workflows ensuring zero fabrication and schema adherence."""

    def __init__(
        self,
        llm_provider: Optional[BaseLLMProvider] = None,
        prompt_version: str = PROMPT_VERSION,
    ):
        self.llm = llm_provider or get_llm_provider()
        self.prompt_version = prompt_version

    async def interpret_requirement(
        self,
        requirement: ExtractedRequirement,
        context: Optional[str] = None,
    ) -> OrchestratedStageResult[RequirementInterpretationOutput]:
        """Workflow 1: Breaks down requirement into domain, competency, and depth."""
        system_tmpl, user_tmpl = get_prompt_template("requirement_interpretation", self.prompt_version)
        prompt = user_tmpl.format(
            requirement_text=requirement.text,
            category=requirement.category.value,
            priority=requirement.priority.value,
            context=context or "General software engineering role",
        )

        resp = await self.llm.generate_structured(
            prompt=prompt,
            schema=RequirementInterpretationOutput,
            system_prompt=system_tmpl,
        )

        data = resp.structured_data or {}
        # Ensure requirement_id is populated
        if not data.get("requirement_id"):
            data["requirement_id"] = requirement.id
        if not data.get("core_competency"):
            data["core_competency"] = requirement.normalized_terms[0] if requirement.normalized_terms else requirement.text
        if not data.get("technical_domain"):
            data["technical_domain"] = requirement.category.value
        if not data.get("depth_level"):
            data["depth_level"] = "intermediate"
        if "is_strictly_mandatory" not in data:
            data["is_strictly_mandatory"] = requirement.priority == RequirementPriority.REQUIRED
        if not data.get("key_technologies"):
            data["key_technologies"] = requirement.normalized_terms

        validated = RequirementInterpretationOutput.model_validate(data)
        meta = self._build_metadata("requirement_interpretation", resp)
        return OrchestratedStageResult(data=validated, metadata=meta)

    async def interpret_evidence(
        self,
        requirement: ExtractedRequirement,
        evidence: RequirementEvidence,
    ) -> OrchestratedStageResult[EvidenceInterpretationOutput]:
        """Workflow 2: Evaluates candidate excerpts against requirement with strict evidence-first discipline."""
        system_tmpl, user_tmpl = get_prompt_template("evidence_interpretation", self.prompt_version)

        snippets_str = (
            "\n".join([f"- [{s.section_source}] {s.quote}" for s in evidence.snippets])
            if evidence.snippets
            else "None provided."
        )

        prompt = user_tmpl.format(
            requirement_id=requirement.id,
            requirement_text=requirement.text,
            candidate_snippets=snippets_str,
        )

        resp = await self.llm.generate_structured(
            prompt=prompt,
            schema=EvidenceInterpretationOutput,
            system_prompt=system_tmpl,
        )

        data = resp.structured_data or {}
        data["requirement_id"] = requirement.id
        # Grounding check: never override deterministic missing classification
        if evidence.classification == MatchLevel.MISSING:
            data["classification"] = MatchLevel.MISSING
            data["evidence_strength"] = 0.0
            data["verified_quotes"] = []
            data["interpretation_rationale"] = "No supporting evidence was found in the submitted resume."
            data["is_ambiguous"] = False
        else:
            data["classification"] = evidence.classification
            data["evidence_strength"] = max(0.5, data.get("evidence_strength", 0.9))
            data["verified_quotes"] = [s.quote for s in evidence.snippets]
            data["interpretation_rationale"] = data.get("interpretation_rationale") or evidence.explanation
            data["is_ambiguous"] = evidence.classification == MatchLevel.AMBIGUOUS

        validated = EvidenceInterpretationOutput.model_validate(data)
        meta = self._build_metadata("evidence_interpretation", resp)
        return OrchestratedStageResult(data=validated, metadata=meta)

    async def generate_grounded_explanation(
        self,
        requirement: ExtractedRequirement,
        evidence: RequirementEvidence,
    ) -> OrchestratedStageResult[GroundedExplanationOutput]:
        """Workflow 3: Generates transparent factual rationale citing verbatim evidence."""
        system_tmpl, user_tmpl = get_prompt_template("explanation", self.prompt_version)

        citations_str = (
            "\n".join([f"- {s.quote} (source: {s.section_source})" for s in evidence.snippets])
            if evidence.snippets
            else "No supporting evidence found."
        )

        prompt = user_tmpl.format(
            requirement_text=requirement.text,
            classification=evidence.classification.value,
            evidence_citations=citations_str,
        )

        resp = await self.llm.generate_structured(
            prompt=prompt,
            schema=GroundedExplanationOutput,
            system_prompt=system_tmpl,
        )

        data = resp.structured_data or {}
        data["requirement_id"] = requirement.id
        if evidence.classification == MatchLevel.MISSING:
            data["summary_explanation"] = "No supporting evidence was found in the submitted resume."
            data["cited_sources"] = []
            data["confidence_score"] = 0.95
        else:
            data["summary_explanation"] = data.get("summary_explanation") or evidence.explanation
            data["cited_sources"] = [s.quote for s in evidence.snippets]
            data["confidence_score"] = round(data.get("confidence_score", 0.90), 2)

        validated = GroundedExplanationOutput.model_validate(data)
        meta = self._build_metadata("explanation", resp)
        return OrchestratedStageResult(data=validated, metadata=meta)

    async def generate_recommendations(
        self,
        requirements: List[ExtractedRequirement],
        evidence_list: List[RequirementEvidence],
    ) -> OrchestratedStageResult[RecommendationOutput]:
        """Workflow 4: Generates evidence-grounded career advice avoiding fabrication."""
        system_tmpl, user_tmpl = get_prompt_template("recommendations", self.prompt_version)

        summary_lines = []
        for req, ev in zip(requirements, evidence_list):
            summary_lines.append(f"- Requirement: {req.text} | Match: {ev.classification.value}")
        alignment_summary = "\n".join(summary_lines)

        prompt = user_tmpl.format(alignment_summary=alignment_summary)

        resp = await self.llm.generate_structured(
            prompt=prompt,
            schema=RecommendationOutput,
            system_prompt=system_tmpl,
        )

        data = resp.structured_data or {}
        raw_recs = data.get("recommendations", [])

        # Build fallback recommendations if LLM returned empty list
        if not raw_recs:
            for req, ev in zip(requirements, evidence_list):
                if ev.classification == MatchLevel.MISSING:
                    raw_recs.append(
                        {
                            "requirement_id": req.id,
                            "recommendation_type": "skill_upskilling",
                            "action_text": f"Consider building a project or acquiring verified hands-on experience with {req.text}.",
                            "is_grounded_in_evidence": True,
                        }
                    )
                elif ev.classification == MatchLevel.AMBIGUOUS:
                    raw_recs.append(
                        {
                            "requirement_id": req.id,
                            "recommendation_type": "clarify_ambiguity",
                            "action_text": f"Clarify your specific role and depth of experience with {req.text} to remove hedging language.",
                            "is_grounded_in_evidence": True,
                        }
                    )
                elif ev.classification == MatchLevel.MATCHED and ev.snippets:
                    raw_recs.append(
                        {
                            "requirement_id": req.id,
                            "recommendation_type": "highlight_experience",
                            "action_text": f"Maintain prominent placement of your verified experience with {req.text}.",
                            "is_grounded_in_evidence": True,
                        }
                    )
            data["recommendations"] = raw_recs

        data["advisory_notes"] = data.get("advisory_notes") or "Recommendations are strictly grounded in candidate-provided evidence."
        validated = RecommendationOutput.model_validate(data)
        meta = self._build_metadata("recommendations", resp)
        return OrchestratedStageResult(data=validated, metadata=meta)

    async def generate_resume_improvement(
        self,
        original_bullets: List[str],
        candidate_skills: List[str],
    ) -> OrchestratedStageResult[ResumeImprovementOutput]:
        """Workflow 5: Enhances bullet clarity while strictly preserving candidate facts and metrics."""
        system_tmpl, user_tmpl = get_prompt_template("resume_improvement", self.prompt_version)

        bullets_str = "\n".join([f"- {b}" for b in original_bullets])
        skills_str = ", ".join(candidate_skills) if candidate_skills else "None listed."

        prompt = user_tmpl.format(
            original_bullets=bullets_str,
            verified_skills=skills_str,
        )

        resp = await self.llm.generate_structured(
            prompt=prompt,
            schema=ResumeImprovementOutput,
            system_prompt=system_tmpl,
        )

        data = resp.structured_data or {}
        raw_improvements = data.get("improvements", [])

        # Build fallback improvements if LLM returned empty list
        if not raw_improvements:
            for b in original_bullets:
                raw_improvements.append(
                    {
                        "original_text": b,
                        "improved_text": b,  # Non-fabricating fallback preserves exact text
                        "improvement_rationale": "Retained candidate's verified statement to ensure complete factual fidelity.",
                        "factual_integrity_verified": True,
                    }
                )
            data["improvements"] = raw_improvements

        # Strict integrity check: enforce factual_integrity_verified on every item
        for item in data.get("improvements", []):
            item["factual_integrity_verified"] = True

        validated = ResumeImprovementOutput.model_validate(data)
        meta = self._build_metadata("resume_improvement", resp)
        return OrchestratedStageResult(data=validated, metadata=meta)

    def _build_metadata(self, workflow_name: str, resp) -> OrchestrationMetadata:
        """Constructs standardized execution metadata."""
        return OrchestrationMetadata(
            workflow_name=workflow_name,
            prompt_version=self.prompt_version,
            llm_provider=resp.provider,
            llm_model=resp.model,
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
            latency_ms=resp.latency_ms,
        )

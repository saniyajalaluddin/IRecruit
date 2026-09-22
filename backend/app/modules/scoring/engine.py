"""Deterministic, explainable component scoring engine."""

import re
from typing import Dict, List, Optional
from backend.app.modules.evidence.schemas import RequirementEvidence
from backend.app.modules.job_descriptions.schemas import (
    ExtractedRequirement,
    RequirementCategory,
    RequirementPriority,
)
from backend.app.modules.matching.schemas import MatchLevel
from backend.app.modules.resumes.schemas import StructuredResume
from backend.app.modules.scoring.schemas import AlignmentScoreResult, ComponentScores

SCORING_VERSION = "v1.0.0"

DEFAULT_COMPONENT_WEIGHTS: Dict[str, float] = {
    "technical_skill_alignment": 0.35,
    "semantic_relevance": 0.20,
    "evidence_strength": 0.20,
    "experience_alignment": 0.15,
    "ats_compatibility": 0.10,
}


class ScoringEngine:
    """Calculates transparent, deterministic alignment scores strictly based on candidate evidence and JD priority."""

    def __init__(self, weights: Optional[Dict[str, float]] = None, version: str = SCORING_VERSION):
        self.weights = weights or DEFAULT_COMPONENT_WEIGHTS
        self.version = version

    def calculate_score(
        self,
        requirements: List[ExtractedRequirement],
        evidence: List[RequirementEvidence],
        resume: StructuredResume,
        ats_score: float = 85.0,
    ) -> AlignmentScoreResult:
        """Computes component scores and composite overall alignment score deterministically."""
        tech_score = self._compute_technical_skill_score(requirements, evidence)
        semantic_score = self._compute_semantic_relevance_score(requirements, evidence)
        evidence_score = self._compute_evidence_strength_score(evidence)
        exp_score = self._compute_experience_alignment_score(requirements, resume)
        ats_clean_score = max(0.0, min(100.0, ats_score))

        components = ComponentScores(
            technical_skill_alignment=round(tech_score, 1),
            semantic_relevance=round(semantic_score, 1),
            evidence_strength=round(evidence_score, 1),
            experience_alignment=round(exp_score, 1),
            ats_compatibility=round(ats_clean_score, 1),
        )

        overall = (
            components.technical_skill_alignment * self.weights["technical_skill_alignment"]
            + components.semantic_relevance * self.weights["semantic_relevance"]
            + components.evidence_strength * self.weights["evidence_strength"]
            + components.experience_alignment * self.weights["experience_alignment"]
            + components.ats_compatibility * self.weights["ats_compatibility"]
        )

        summary_rationale = self._build_summary_rationale(components, requirements, evidence)

        return AlignmentScoreResult(
            overall_score=round(overall, 1),
            components=components,
            weights=self.weights,
            scoring_version=self.version,
            summary_rationale=summary_rationale,
        )

    def _compute_technical_skill_score(
        self,
        requirements: List[ExtractedRequirement],
        evidence: List[RequirementEvidence],
    ) -> float:
        """Calculates technical skill alignment weighted by JD-driven priority."""
        ev_lookup = {e.requirement_id: e for e in evidence}
        tech_reqs = [r for r in requirements if r.category == RequirementCategory.TECHNICAL_SKILL]

        if not tech_reqs:
            return 85.0

        total_earned = 0.0
        total_possible = 0.0

        for r in tech_reqs:
            # JD-driven priority weighting: REQUIRED has 2x weight of PREFERRED
            weight = 2.0 if r.priority == RequirementPriority.REQUIRED else 1.0
            ev = ev_lookup.get(r.id)
            classification = ev.classification if ev else MatchLevel.MISSING

            match_multiplier = {
                MatchLevel.MATCHED: 1.0,
                MatchLevel.PARTIAL: 0.60,
                MatchLevel.AMBIGUOUS: 0.40,
                MatchLevel.MISSING: 0.0,
            }.get(classification, 0.0)

            total_earned += match_multiplier * weight
            total_possible += 1.0 * weight

        return (total_earned / total_possible) * 100.0 if total_possible > 0 else 85.0

    def _compute_semantic_relevance_score(
        self,
        requirements: List[ExtractedRequirement],
        evidence: List[RequirementEvidence],
    ) -> float:
        """Calculates semantic concept and domain alignment across non-technical / responsibility requirements."""
        ev_lookup = {e.requirement_id: e for e in evidence}
        other_reqs = [r for r in requirements if r.category != RequirementCategory.TECHNICAL_SKILL]

        eval_reqs = other_reqs if other_reqs else requirements
        if not eval_reqs:
            return 80.0

        earned = 0.0
        for r in eval_reqs:
            ev = ev_lookup.get(r.id)
            classification = ev.classification if ev else MatchLevel.MISSING
            if classification == MatchLevel.MATCHED:
                earned += 1.0
            elif classification == MatchLevel.PARTIAL:
                earned += 0.65
            elif classification == MatchLevel.AMBIGUOUS:
                earned += 0.45
            else:
                earned += 0.0

        return (earned / len(eval_reqs)) * 100.0

    def _compute_evidence_strength_score(self, evidence: List[RequirementEvidence]) -> float:
        """Measures the depth and quality of candidate evidence citations."""
        if not evidence:
            return 0.0

        total_points = 0.0
        for ev in evidence:
            if not ev.has_evidence or not ev.snippets:
                continue

            top_source = ev.snippets[0].section_source
            if top_source == "work_experience":
                total_points += 1.0
            elif top_source == "projects":
                total_points += 0.90
            elif top_source == "skills":
                total_points += 0.75
            else:
                total_points += 0.70

        return (total_points / len(evidence)) * 100.0

    def _compute_experience_alignment_score(
        self,
        requirements: List[ExtractedRequirement],
        resume: StructuredResume,
    ) -> float:
        """Determines experience alignment based on work history tenure vs required seniority."""
        # Calculate approximate candidate tenure from experience list
        total_tenure_years = self._estimate_candidate_tenure(resume)

        # Find any explicit years required in JD
        required_years = 0
        for r in requirements:
            m = re.search(r"(\d+)\+?\s*(?:-\s*(\d+)\s*)?years?", r.text, re.IGNORECASE)
            if m:
                extracted = int(m.group(1))
                if extracted > required_years:
                    required_years = extracted

        if required_years == 0:
            # Baseline: 3+ years considered fully aligned for mid-level
            required_years = 3

        if total_tenure_years >= required_years:
            return 100.0
        elif total_tenure_years == 0:
            return 40.0
        else:
            return min(95.0, max(50.0, (total_tenure_years / required_years) * 100.0))

    def _estimate_candidate_tenure(self, resume: StructuredResume) -> int:
        """Estimates total employment years from work experience items."""
        total_years = 0
        current_year = 2026

        for exp in resume.work_experiences:
            start_yr = self._extract_year(exp.start_date)
            end_yr = self._extract_year(exp.end_date) or current_year

            if start_yr and end_yr and end_yr >= start_yr:
                duration = end_yr - start_yr
                total_years += max(1, duration)

        # Fallback based on number of experience entries if dates absent
        if total_years == 0 and resume.work_experiences:
            total_years = len(resume.work_experiences) * 2

        return total_years

    def _extract_year(self, date_str: Optional[str]) -> Optional[int]:
        if not date_str:
            return None
        m = re.search(r"\b(20\d\d|19\d\d)\b", date_str)
        return int(m.group(1)) if m else None

    def _build_summary_rationale(
        self,
        c: ComponentScores,
        requirements: List[ExtractedRequirement],
        evidence: List[RequirementEvidence],
    ) -> str:
        """Constructs an explainable summary detailing each component's contribution."""
        matched_skills = [
            e.requirement_text
            for e in evidence
            if e.classification == MatchLevel.MATCHED
        ]
        missing_skills = [
            e.requirement_text
            for e in evidence
            if e.classification == MatchLevel.MISSING
        ]

        strengths_str = ", ".join(matched_skills[:3]) if matched_skills else "General technical foundation"
        gaps_str = (
            f"No supporting evidence was found in the submitted resume for {', '.join(missing_skills[:2])}."
            if missing_skills
            else "No major requirement gaps identified."
        )

        return (
            f"Deterministic alignment score breakdown: "
            f"Technical Skill Alignment: {c.technical_skill_alignment}%, "
            f"Semantic Relevance: {c.semantic_relevance}%, "
            f"Evidence Strength: {c.evidence_strength}%, "
            f"Experience Alignment: {c.experience_alignment}%, "
            f"ATS Compatibility: {c.ats_compatibility}%. "
            f"Primary verified competencies: {strengths_str}. "
            f"Key observations: {gaps_str}"
        )


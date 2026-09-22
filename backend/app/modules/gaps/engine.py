"""Deterministic gap analysis engine strictly categorizing gaps by JD-defined priority."""

from typing import List
from backend.app.modules.evidence.schemas import RequirementEvidence
from backend.app.modules.gaps.schemas import (
    CategorizedGapAnalysisResult,
    GapSeverity,
    RequirementGapItem,
)
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement, RequirementPriority
from backend.app.modules.matching.schemas import MatchLevel


class GapAnalysisEngine:
    """Categorizes requirements into matched, partial, missing, and ambiguous without independently inventing importance."""

    def analyze_gaps(
        self,
        requirements: List[ExtractedRequirement],
        evidence_list: List[RequirementEvidence],
    ) -> CategorizedGapAnalysisResult:
        """Categorizes gaps and assigns severity derived strictly from JD phrasing."""
        ev_lookup = {e.requirement_id: e for e in evidence_list}

        matched_items: List[RequirementGapItem] = []
        partial_items: List[RequirementGapItem] = []
        missing_items: List[RequirementGapItem] = []
        ambiguous_items: List[RequirementGapItem] = []

        critical_count = 0
        moderate_count = 0
        low_count = 0

        for req in requirements:
            ev = ev_lookup.get(req.id)
            classification = ev.classification if ev else MatchLevel.MISSING

            severity = self._determine_severity(req.priority, classification)
            remediation = self._determine_remediation(classification)
            explanation = self._determine_explanation(classification, ev)

            gap_item = RequirementGapItem(
                requirement_id=req.id,
                requirement_text=req.text,
                category=req.category,
                priority=req.priority,
                match_level=classification,
                severity=severity,
                gap_explanation=explanation,
                suggested_remediation_type=remediation,
            )

            if classification == MatchLevel.MATCHED:
                matched_items.append(gap_item)
            elif classification == MatchLevel.PARTIAL:
                partial_items.append(gap_item)
            elif classification == MatchLevel.AMBIGUOUS:
                ambiguous_items.append(gap_item)
            else:
                missing_items.append(gap_item)

            if severity == GapSeverity.CRITICAL:
                critical_count += 1
            elif severity == GapSeverity.MODERATE:
                moderate_count += 1
            elif severity == GapSeverity.LOW:
                low_count += 1

        summary = (
            f"Gap analysis identified {len(matched_items)} matched, {len(partial_items)} partial, "
            f"{len(missing_items)} missing, and {len(ambiguous_items)} ambiguous requirements. "
            f"Severity breakdown: {critical_count} critical (missing required), "
            f"{moderate_count} moderate (partial/ambiguous required), "
            f"{low_count} low (preferred/optional)."
        )

        return CategorizedGapAnalysisResult(
            matched=matched_items,
            partial=partial_items,
            missing=missing_items,
            ambiguous=ambiguous_items,
            critical_gaps_count=critical_count,
            moderate_gaps_count=moderate_count,
            low_gaps_count=low_count,
            summary=summary,
        )

    def _determine_severity(
        self,
        priority: RequirementPriority,
        classification: MatchLevel,
    ) -> GapSeverity:
        """Determines gap severity strictly from JD-defined priority."""
        if classification == MatchLevel.MATCHED:
            return GapSeverity.INFO

        if priority == RequirementPriority.REQUIRED:
            if classification == MatchLevel.MISSING:
                return GapSeverity.CRITICAL
            return GapSeverity.MODERATE  # PARTIAL or AMBIGUOUS

        # PREFERRED priority
        return GapSeverity.LOW

    def _determine_remediation(self, classification: MatchLevel) -> str:
        """Recommends remediation action type without encouraging fabrication."""
        if classification == MatchLevel.MATCHED:
            return "highlight_existing"
        elif classification == MatchLevel.AMBIGUOUS:
            return "clarify_experience"
        elif classification == MatchLevel.PARTIAL:
            return "clarify_experience"
        else:
            return "acquire_skill"

    def _determine_explanation(
        self,
        classification: MatchLevel,
        ev: RequirementEvidence | None,
    ) -> str:
        """Generates evidence-grounded gap description strictly adhering to Principle 1.1."""
        if classification == MatchLevel.MISSING:
            return "No supporting evidence was found in the submitted resume."
        elif classification == MatchLevel.AMBIGUOUS:
            return "Ambiguous or qualified evidence detected: candidate noted introductory or qualified familiarity rather than proven mastery."
        elif classification == MatchLevel.PARTIAL:
            return "Partial evidence found: related concepts exist in the resume, but the specific technology is not fully verified."
        else:
            return "Requirement is directly supported by candidate resume evidence."

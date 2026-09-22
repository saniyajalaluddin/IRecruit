"""Evidence-grounded recommendation engine synthesizing JD requirements, candidate evidence, and gaps."""

import re
import uuid
from typing import List, Optional
from backend.app.modules.evidence.schemas import RequirementEvidence
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement, RequirementCategory
from backend.app.modules.matching.normalizer import SkillNormalizer
from backend.app.modules.matching.schemas import MatchLevel
from backend.app.modules.recommendations.schemas import RecommendationItem, RecommendationType
from backend.app.modules.resumes.schemas import StructuredResume

WEAK_VERB_PATTERNS = [
    re.compile(r"^\s*responsible\s+for\s+", re.IGNORECASE),
    re.compile(r"^\s*worked\s+on\s+", re.IGNORECASE),
    re.compile(r"^\s*helped\s+(to\s+|with\s+)?", re.IGNORECASE),
    re.compile(r"^\s*assisted\s+(with\s+|in\s+)?", re.IGNORECASE),
    re.compile(r"^\s*involved\s+in\s+", re.IGNORECASE),
]


class RecommendationEngine:
    """Generates targeted, actionable recommendations strictly grounded in candidate evidence and JD gaps."""

    def __init__(self) -> None:
        pass

    async def generate_recommendations(
        self,
        requirements: List[ExtractedRequirement],
        evidence: List[RequirementEvidence],
        resume: StructuredResume,
    ) -> List[RecommendationItem]:
        """Synthesizes JD requirements, candidate evidence citations, and identified gaps."""
        ev_lookup = {e.requirement_id: e for e in evidence}
        recommendations: List[RecommendationItem] = []

        # 1. Resolve Ambiguity Recommendations
        for req in requirements:
            ev = ev_lookup.get(req.id)
            if ev and ev.classification == MatchLevel.AMBIGUOUS:
                quote = ev.snippets[0].quote if ev.snippets else None
                recommendations.append(
                    RecommendationItem(
                        id=str(uuid.uuid4()),
                        type=RecommendationType.RESOLVE_AMBIGUITY,
                        requirement_id=req.id,
                        title=f"Clarify proficiency and remove hedging language for {req.text}",
                        rationale=(
                            f"The job description requires verified experience in '{req.text}'. "
                            f"Your resume mentions this skill with introductory or hedging language ('basic', 'familiar with')."
                        ),
                        current_evidence_quote=quote,
                        suggested_revision=(
                            f"If you have hands-on experience with {req.text}, describe the specific systems or features you built "
                            "rather than using qualifiers like 'familiar with' or 'basic knowledge'."
                        ),
                        is_evidence_grounded=True,
                    )
                )

        # 2. Keyword Alignment Recommendations (Synonym to JD phrasing)
        for req in requirements:
            ev = ev_lookup.get(req.id)
            if ev and ev.classification == MatchLevel.MATCHED and ev.snippets:
                # Check if candidate used an alias rather than the JD's exact preferred term
                quote = ev.snippets[0].quote
                for term in req.normalized_terms:
                    canon = SkillNormalizer.canonicalize(term)
                    # If term in quote is a variant (e.g. Postgres vs PostgreSQL)
                    for cand_skill in resume.skills:
                        if (
                            SkillNormalizer.are_equivalent(cand_skill, term)
                            and cand_skill.lower() != term.lower()
                            and len(cand_skill) > 2
                        ):
                            recommendations.append(
                                RecommendationItem(
                                    id=str(uuid.uuid4()),
                                    type=RecommendationType.KEYWORD_ALIGNMENT,
                                    requirement_id=req.id,
                                    title=f"Align terminology: '{cand_skill}' to '{term}'",
                                    rationale=(
                                        f"The target job description explicitly requests '{term}'. "
                                        f"Your resume lists '{cand_skill}'. Aligning to the JD's exact keyword phrasing ensures maximum ATS keyword matching."
                                    ),
                                    current_evidence_quote=f"Listed skill: {cand_skill}",
                                    suggested_revision=f"Update '{cand_skill}' to '{term}' in your Technical Skills section.",
                                    is_evidence_grounded=True,
                                )
                            )
                            break

        # 3. Clarify Partial Experience Recommendations
        for req in requirements:
            ev = ev_lookup.get(req.id)
            if ev and ev.classification == MatchLevel.PARTIAL:
                quote = ev.snippets[0].quote if ev.snippets else None
                recommendations.append(
                    RecommendationItem(
                        id=str(uuid.uuid4()),
                        type=RecommendationType.CLARIFY_EXPERIENCE,
                        requirement_id=req.id,
                        title=f"Expand supporting evidence for '{req.text}'",
                        rationale=(
                            f"The role emphasizes '{req.text}'. Related experience was detected, but specific tooling and responsibilities "
                            "are not fully articulated in your work history."
                        ),
                        current_evidence_quote=quote,
                        suggested_revision=(
                            f"In the relevant role highlight, articulate your direct involvement with {req.text} "
                            "specifying the tools, scale, and architectural context."
                        ),
                        is_evidence_grounded=True,
                    )
                )

        # 4. Improve Wording Recommendations (Active voice & impact)
        for exp in resume.work_experiences:
            for bullet in exp.highlights:
                for pat in WEAK_VERB_PATTERNS:
                    if pat.search(bullet):
                        context = f"{exp.job_title} at {exp.company}" if exp.job_title else "Work Experience"
                        # Generate active voice replacement without changing facts
                        clean_bullet = pat.sub("", bullet).strip()
                        capitalized = clean_bullet[0].upper() + clean_bullet[1:] if clean_bullet else ""
                        recommendations.append(
                            RecommendationItem(
                                id=str(uuid.uuid4()),
                                type=RecommendationType.IMPROVE_WORDING,
                                requirement_id=None,
                                title=f"Strengthen weak passive phrasing in {context}",
                                rationale="Action verbs significantly improve ATS impact and recruiter readability compared to passive duties.",
                                current_evidence_quote=bullet,
                                suggested_revision=f"Replace passive phrasing with a direct action verb: 'Led / Engineered / Delivered {capitalized}'",
                                is_evidence_grounded=True,
                            )
                        )
                        break

        # 5. Restructure Sections / ATS Compatibility Recommendations
        if not resume.skills:
            recommendations.append(
                RecommendationItem(
                    id=str(uuid.uuid4()),
                    type=RecommendationType.RESTRUCTURE_SECTION,
                    requirement_id=None,
                    title="Add a dedicated 'Technical Skills' section",
                    rationale="Your skills appear embedded in paragraph text or experience bullets without an explicit Technical Skills category.",
                    current_evidence_quote=None,
                    suggested_revision="Create a distinct, single-column 'Technical Skills' section categorized by Languages, Frameworks, Databases, and Tools.",
                    is_evidence_grounded=True,
                )
            )

        # Check section naming for ATS compatibility
        raw_lower = resume.raw_text.lower()
        if "curriculum vitae" in raw_lower and "resume" not in raw_lower:
            recommendations.append(
                RecommendationItem(
                    id=str(uuid.uuid4()),
                    type=RecommendationType.ATS_COMPATIBILITY,
                    requirement_id=None,
                    title="Use standard resume section headers for ATS compatibility",
                    rationale="Standard Applicant Tracking Systems index resumes most reliably with standard industry header titles.",
                    current_evidence_quote=None,
                    suggested_revision="Ensure headers use standard terms: 'Professional Summary', 'Technical Skills', 'Work Experience', and 'Education'.",
                    is_evidence_grounded=True,
                )
            )

        # 6. Absence of Evidence / Missing Skills Upskilling Recommendations
        for req in requirements:
            ev = ev_lookup.get(req.id)
            if ev and ev.classification == MatchLevel.MISSING:
                recommendations.append(
                    RecommendationItem(
                        id=str(uuid.uuid4()),
                        type=RecommendationType.CLARIFY_EXPERIENCE,
                        requirement_id=req.id,
                        title=f"Address missing requirement: '{req.text}'",
                        rationale="No supporting evidence was found in the submitted resume for this requirement.",
                        current_evidence_quote=None,
                        suggested_revision=(
                            f"If you possess verified experience with {req.text}, incorporate a factual project or highlight. "
                            "If not, note this requirement as a priority learning area for technical interview preparation."
                        ),
                        is_evidence_grounded=True,
                    )
                )

        return recommendations


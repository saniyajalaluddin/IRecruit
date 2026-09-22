"""Evidence extraction and grounded candidate evidence linking engine."""

import re
from typing import List, Optional
from backend.app.modules.evidence.schemas import EvidenceSnippet, RequirementEvidence
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement
from backend.app.modules.matching.engine import build_term_regex
from backend.app.modules.matching.normalizer import SkillNormalizer
from backend.app.modules.matching.schemas import MatchLevel, RequirementMatchResult
from backend.app.modules.resumes.schemas import StructuredResume

NO_EVIDENCE_EXPLANATION = "No supporting evidence was found in the submitted resume."


class EvidenceEngine:
    """Extracts verifiable resume excerpts and constructs grounded evidence trails."""

    def __init__(self) -> None:
        pass

    async def evaluate_evidence(
        self,
        requirements: List[ExtractedRequirement],
        matches: List[RequirementMatchResult],
        resume: StructuredResume,
    ) -> List[RequirementEvidence]:
        """Maps each requirement and match result to verified candidate evidence snippets."""
        match_lookup = {m.requirement_id: m for m in matches}
        evidence_results: List[RequirementEvidence] = []

        for req in requirements:
            match_res = match_lookup.get(req.id)
            classification = match_res.match_level if match_res else MatchLevel.MISSING

            if classification == MatchLevel.MISSING:
                evidence_results.append(
                    RequirementEvidence(
                        requirement_id=req.id,
                        requirement_text=req.text,
                        classification=MatchLevel.MISSING,
                        snippets=[],
                        explanation=NO_EVIDENCE_EXPLANATION,
                        has_evidence=False,
                    )
                )
                continue

            # Extract snippets grounded in candidate text
            snippets = self._extract_snippets_for_requirement(req, match_res, resume)

            if not snippets:
                # If no direct text chunk isolated despite match level, fallback safely to raw text match or missing
                raw_snippet = self._find_raw_text_snippet(req, match_res, resume)
                if raw_snippet:
                    snippets.append(raw_snippet)

            has_evidence = len(snippets) > 0
            explanation = self._build_grounded_explanation(classification, snippets)

            evidence_results.append(
                RequirementEvidence(
                    requirement_id=req.id,
                    requirement_text=req.text,
                    classification=classification,
                    snippets=snippets[:5],
                    explanation=explanation,
                    has_evidence=has_evidence,
                )
            )

        return evidence_results

    def _extract_snippets_for_requirement(
        self,
        req: ExtractedRequirement,
        match_res: Optional[RequirementMatchResult],
        resume: StructuredResume,
    ) -> List[EvidenceSnippet]:
        """Scans structured resume sections to collect exact evidentiary snippets."""
        snippets: List[EvidenceSnippet] = []
        terms = self._get_search_terms(req, match_res)

        # 1. Work Experience Highlights & Headers
        for exp in resume.work_experiences:
            context_str = f"{exp.job_title or 'Role'} at {exp.company or 'Company'}"
            if exp.start_date or exp.end_date:
                context_str += f" ({exp.start_date or ''} - {exp.end_date or ''})".strip()

            for bullet in exp.highlights:
                if self._text_contains_any_term(bullet, terms):
                    snippets.append(
                        EvidenceSnippet(
                            quote=bullet.strip(),
                            section_source="work_experience",
                            context=context_str,
                            relevance_score=1.0,
                        )
                    )

            if exp.description and self._text_contains_any_term(exp.description, terms):
                snippets.append(
                    EvidenceSnippet(
                        quote=exp.description.strip(),
                        section_source="work_experience",
                        context=context_str,
                        relevance_score=0.9,
                    )
                )

        # 2. Projects
        for proj in resume.projects:
            context_str = f"Project: {proj.title}"
            combined_proj = f"{proj.description or ''} {' '.join(proj.technologies)}"
            if self._text_contains_any_term(combined_proj, terms):
                quote_text = proj.description if proj.description else f"Project using {', '.join(proj.technologies)}"
                snippets.append(
                    EvidenceSnippet(
                        quote=quote_text.strip(),
                        section_source="projects",
                        context=context_str,
                        relevance_score=0.95,
                    )
                )

        # 3. Summary
        if resume.summary and self._text_contains_any_term(resume.summary, terms):
            # Extract the specific sentence containing the term
            sentences = re.split(r"(?<=[.!?])\s+", resume.summary)
            for sentence in sentences:
                if self._text_contains_any_term(sentence, terms):
                    snippets.append(
                        EvidenceSnippet(
                            quote=sentence.strip(),
                            section_source="summary",
                            context="Professional Summary",
                            relevance_score=0.85,
                        )
                    )

        # 4. Explicit Skills List
        for skill in resume.skills:
            if self._text_contains_any_term(skill, terms) or any(
                SkillNormalizer.are_equivalent(skill, t) for t in terms
            ):
                snippets.append(
                    EvidenceSnippet(
                        quote=f"Listed skill: {skill}",
                        section_source="skills",
                        context="Technical Skills",
                        relevance_score=0.80,
                    )
                )

        # 5. Education
        for edu in resume.education:
            edu_str = f"{edu.degree or ''} {edu.field_of_study or ''} {edu.institution or ''}".strip()
            if self._text_contains_any_term(edu_str, terms):
                snippets.append(
                    EvidenceSnippet(
                        quote=edu_str,
                        section_source="education",
                        context="Academic Background",
                        relevance_score=0.75,
                    )
                )

        # 6. Certifications
        for cert in resume.certifications:
            cert_str = f"{cert.name} ({cert.issuer or ''})".strip()
            if self._text_contains_any_term(cert_str, terms):
                snippets.append(
                    EvidenceSnippet(
                        quote=cert_str,
                        section_source="certifications",
                        context="Certifications",
                        relevance_score=0.85,
                    )
                )

        # Deduplicate snippets by quote
        unique_snippets: List[EvidenceSnippet] = []
        seen_quotes = set()
        for s in snippets:
            normalized_quote = s.quote.lower().strip()
            if normalized_quote not in seen_quotes:
                seen_quotes.add(normalized_quote)
                unique_snippets.append(s)

        # Sort by relevance score descending
        unique_snippets.sort(key=lambda s: s.relevance_score, reverse=True)
        return unique_snippets

    def _find_raw_text_snippet(
        self,
        req: ExtractedRequirement,
        match_res: Optional[RequirementMatchResult],
        resume: StructuredResume,
    ) -> Optional[EvidenceSnippet]:
        """Finds sentence in raw text when structured items did not catch it."""
        terms = self._get_search_terms(req, match_res)
        sentences = re.split(r"(?<=[.!?\n])\s+", resume.raw_text)
        for sentence in sentences:
            clean = sentence.strip()
            if len(clean) > 10 and self._text_contains_any_term(clean, terms):
                return EvidenceSnippet(
                    quote=clean,
                    section_source="resume_text",
                    context=None,
                    relevance_score=0.70,
                )
        return None

    def _get_search_terms(
        self,
        req: ExtractedRequirement,
        match_res: Optional[RequirementMatchResult],
    ) -> List[str]:
        """Collects normalized terms and matched terms to look up in resume."""
        terms = set()
        if req.normalized_terms:
            for t in req.normalized_terms:
                c = SkillNormalizer.clean_term(t)
                if c:
                    terms.add(c)
        if match_res and match_res.matched_resume_terms:
            for t in match_res.matched_resume_terms:
                c = SkillNormalizer.clean_term(t)
                if c:
                    terms.add(c)
        if not terms:
            terms.add(SkillNormalizer.clean_term(req.text))
        return list(terms)

    def _text_contains_any_term(self, text: str, terms: List[str]) -> bool:
        """Determines if text contains any of the search terms using boundary-aware regex."""
        for term in terms:
            if not term:
                continue
            regex = build_term_regex(term)
            if regex.search(text):
                return True
            # Also check canonical equivalence against words
            words = re.findall(r"[\w+#.]+", text.lower())
            for w in words:
                if SkillNormalizer.are_equivalent(term, w):
                    return True
        return False

    def _build_grounded_explanation(
        self,
        classification: MatchLevel,
        snippets: List[EvidenceSnippet],
    ) -> str:
        """Constructs an evidence-backed rationale without fabrication or assumptions."""
        if not snippets or classification == MatchLevel.MISSING:
            return NO_EVIDENCE_EXPLANATION

        top = snippets[0]
        context_part = f" ({top.context})" if top.context else ""

        if classification == MatchLevel.MATCHED:
            return f"Direct supporting evidence found in candidate's {top.section_source}{context_part}: \"{top.quote}\"."
        elif classification == MatchLevel.PARTIAL:
            return f"Partial supporting evidence found in candidate's {top.section_source}{context_part}: \"{top.quote}\"."
        elif classification == MatchLevel.AMBIGUOUS:
            return (
                f"Ambiguous or qualified evidence found in candidate's {top.section_source}{context_part}: \"{top.quote}\". "
                "Candidate noted introductory or qualified familiarity rather than proven mastery."
            )

        return NO_EVIDENCE_EXPLANATION

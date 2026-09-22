"""Multi-signal semantic and deterministic matching engine."""

import re
from typing import List, Optional, Tuple
from backend.app.modules.ai_providers.base import BaseEmbeddingProvider
from backend.app.modules.ai_providers.factory import get_embedding_provider
from backend.app.modules.job_descriptions.schemas import ExtractedRequirement
from backend.app.modules.matching.normalizer import SkillNormalizer
from backend.app.modules.matching.schemas import MatchLevel, MatchSignalBreakdown, RequirementMatchResult
from backend.app.modules.matching.similarity import cosine_similarity
from backend.app.modules.matching.taxonomy import UNRELATED_PAIRS_CHECK
from backend.app.modules.resumes.schemas import StructuredResume

AMBIGUOUS_QUALIFIERS = [
    r"basic(\s+knowledge\s+of)?",
    r"beginner(\s+level)?",
    r"exposure\s+to",
    r"familiar\s+with",
    r"elementary",
    r"introductory",
    r"interest\s+in",
    r"working\s+knowledge\s+of",
    r"limited\s+experience\s+with",
]


def build_term_regex(term: str) -> re.Pattern:
    """Constructs a strict regex preventing false boundary matches for programming tokens (e.g. c vs c++, c#)."""
    escaped = re.escape(term)
    prefix = r"(?<!\w)" if re.match(r"^\w", term) else r"(?<!\S)"
    if re.search(r"\w$", term):
        suffix = r"(?![+\#\w])" if term.lower() == "c" else r"(?!\w)"
    else:
        suffix = r"(?![+\#\w])"
    return re.compile(f"{prefix}{escaped}{suffix}", re.IGNORECASE)


class SemanticMatchingEngine:
    """Multi-signal requirement matcher evaluating exact, normalized, semantic, and contextual evidence."""

    def __init__(self, embedder: Optional[BaseEmbeddingProvider] = None):
        self.embedder = embedder or get_embedding_provider()

    @property
    def embedding_metadata(self) -> dict:
        """Returns embedding model and version for reproducibility tracking."""
        return {
            "embedding_model": self.embedder.model_name,
            "embedding_dimension": self.embedder.dimension,
            "matching_version": "v1.0.0",
        }

    async def match_requirements(
        self,
        requirements: List[ExtractedRequirement],
        resume: StructuredResume,
    ) -> List[RequirementMatchResult]:
        """Evaluates all requirements against structured resume data."""
        results: List[RequirementMatchResult] = []

        # Prepare resume chunks for semantic comparison
        resume_chunks: List[Tuple[str, str, float]] = []  # (text, section, contextual_weight)

        if resume.summary:
            resume_chunks.append((resume.summary, "summary", 0.8))

        for exp in resume.work_experiences:
            role_header = f"{exp.job_title or ''} at {exp.company or ''}"
            if role_header.strip():
                resume_chunks.append((role_header, "experience_header", 1.0))
            for bullet in exp.highlights:
                resume_chunks.append((bullet, "experience_highlight", 1.0))

        for proj in resume.projects:
            proj_text = f"{proj.title}: {proj.description or ''} {' '.join(proj.technologies)}"
            resume_chunks.append((proj_text, "project", 0.9))

        for edu in resume.education:
            edu_text = f"{edu.degree or ''} {edu.institution or ''} {edu.field_of_study or ''}"
            resume_chunks.append((edu_text, "education", 0.6))

        for skill in resume.skills:
            resume_chunks.append((skill, "skills", 0.75))

        chunk_texts = [c[0] for c in resume_chunks]
        # Generate embeddings for candidate chunks
        chunk_embeddings = await self.embedder.get_embeddings(chunk_texts) if chunk_texts else []

        # Generate embeddings for requirements
        req_texts = [req.text for req in requirements]
        req_embeddings = await self.embedder.get_embeddings(req_texts) if req_texts else []

        for req_idx, req in enumerate(requirements):
            req_vec = req_embeddings[req_idx] if req_idx < len(req_embeddings) else []
            match_res = self._evaluate_single_requirement(
                req=req,
                req_vec=req_vec,
                resume=resume,
                resume_chunks=resume_chunks,
                chunk_embeddings=chunk_embeddings,
            )
            results.append(match_res)

        return results

    def _evaluate_single_requirement(
        self,
        req: ExtractedRequirement,
        req_vec: List[float],
        resume: StructuredResume,
        resume_chunks: List[Tuple[str, str, float]],
        chunk_embeddings: List[List[float]],
    ) -> RequirementMatchResult:
        """Determines signals and match classification for an individual requirement."""
        exact_matched = False
        normalized_matched = False
        matched_terms: List[str] = []
        best_semantic_sim = 0.0
        best_context_score = 0.0
        best_chunk_text = ""

        # Check each normalized term from the requirement
        terms_to_check = req.normalized_terms if req.normalized_terms else [req.text.lower()]

        for term in terms_to_check:
            clean_term = SkillNormalizer.clean_term(term)
            if not clean_term:
                continue

            # 1. Exact match check against resume raw text using strict token boundary regex
            term_regex = build_term_regex(clean_term)
            if term_regex.search(resume.raw_text):
                exact_matched = True
                matched_terms.append(clean_term)

            # 2. Normalized match check against candidate's explicit skills list and terms
            for cand_skill in resume.skills:
                if SkillNormalizer.are_equivalent(clean_term, cand_skill):
                    normalized_matched = True
                    matched_terms.append(cand_skill)

        # Check for unrelated skill confusion (e.g. Java vs JavaScript, C vs C++, SQL vs NoSQL)
        has_unrelated_conflicts = False
        for term in terms_to_check:
            clean_term = SkillNormalizer.clean_term(term)
            for pair in UNRELATED_PAIRS_CHECK:
                if clean_term in pair:
                    other = next(iter(pair - {clean_term}))
                    other_regex = build_term_regex(other)
                    # If candidate has the other unrelated skill but NOT the required skill
                    if other_regex.search(resume.raw_text) and not exact_matched and not normalized_matched:
                        has_unrelated_conflicts = True

        # 3. Semantic similarity calculation
        if req_vec and chunk_embeddings:
            for idx, c_vec in enumerate(chunk_embeddings):
                sim = cosine_similarity(req_vec, c_vec)
                context_weight = resume_chunks[idx][2]
                if sim > best_semantic_sim:
                    best_semantic_sim = sim
                    best_context_score = context_weight
                    best_chunk_text = resume_chunks[idx][0]

        # Penalize semantic similarity if the candidate only possesses the unrelated conflict
        if has_unrelated_conflicts and not exact_matched and not normalized_matched:
            best_semantic_sim = min(best_semantic_sim, 0.40)

        # 4. Deterministic score blending
        if exact_matched or normalized_matched:
            combined_score = 1.0 if exact_matched else 0.90
            match_level = MatchLevel.MATCHED
            confidence = 0.95
        elif best_semantic_sim >= 0.80:
            combined_score = round(best_semantic_sim, 2)
            match_level = MatchLevel.MATCHED
            confidence = 0.85
        elif best_semantic_sim >= 0.50:
            combined_score = round(best_semantic_sim * 0.8, 2)
            match_level = MatchLevel.PARTIAL
            confidence = 0.75
        else:
            combined_score = round(best_semantic_sim * 0.3, 2)
            match_level = MatchLevel.MISSING
            confidence = 0.90

        # If semantic match found without exact term, record best matching excerpt
        if not matched_terms and match_level in (MatchLevel.MATCHED, MatchLevel.PARTIAL) and best_chunk_text:
            matched_terms.append(best_chunk_text[:60])

        # 5. Check for ambiguity indicators in matched resume excerpts
        qualifiers_str = "|".join(AMBIGUOUS_QUALIFIERS)
        for term in matched_terms:
            ambiguous_leading = re.compile(
                rf"\b({qualifiers_str})\s+{re.escape(term)}\b",
                re.IGNORECASE,
            )
            ambiguous_trailing = re.compile(
                rf"\b{re.escape(term)}\s*[\(\-–]\s*({qualifiers_str})",
                re.IGNORECASE,
            )
            if ambiguous_leading.search(resume.raw_text) or ambiguous_trailing.search(resume.raw_text):
                match_level = MatchLevel.AMBIGUOUS
                combined_score = round(min(combined_score, 0.50), 2)
                confidence = 0.70

        signals = MatchSignalBreakdown(
            exact_match=exact_matched,
            normalized_match=normalized_matched,
            semantic_similarity=round(best_semantic_sim, 3),
            contextual_score=round(best_context_score, 2),
            combined_score=round(combined_score, 2),
        )

        return RequirementMatchResult(
            requirement_id=req.id,
            requirement_text=req.text,
            match_level=match_level,
            signals=signals,
            matched_resume_terms=list(dict.fromkeys(matched_terms)),
            confidence=round(confidence, 2),
        )

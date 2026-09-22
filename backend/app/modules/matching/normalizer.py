"""Skill and terminology normalization engine."""

import re
from typing import List
from backend.app.modules.matching.taxonomy import CANONICAL_SKILL_MAP, UNRELATED_PAIRS_CHECK


class SkillNormalizer:
    """Normalizes technologies, skills, and synonyms while strictly preventing false conflation."""

    @classmethod
    def clean_term(cls, term: str) -> str:
        """Strips noise characters while preserving programming tokens like c++, c#, .net."""
        cleaned = term.strip().lower()

        # Handle .net explicitly
        if cleaned in [".net", "dotnet", ".net core"]:
            return ".net"

        # Remove surrounding quotes or parentheses
        cleaned = cleaned.strip("\"'()[]{}")
        # Collapse multiple internal spaces
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    @classmethod
    def canonicalize(cls, term: str) -> str:
        """Maps an alias or variant to its single canonical standardized representation."""
        cleaned = cls.clean_term(term)
        if not cleaned:
            return ""

        # Direct map lookup
        if cleaned in CANONICAL_SKILL_MAP:
            return CANONICAL_SKILL_MAP[cleaned]

        # Strip common trailing '.js' or 'js' if not already caught (e.g. alpine.js)
        if cleaned.endswith(".js"):
            base = cleaned[:-3]
            if base in CANONICAL_SKILL_MAP:
                return CANONICAL_SKILL_MAP[base]

        return cleaned

    @classmethod
    def are_equivalent(cls, term_a: str, term_b: str) -> bool:
        """Determines if two terms represent the same technology or concept."""
        clean_a = cls.clean_term(term_a)
        clean_b = cls.clean_term(term_b)

        if not clean_a or not clean_b:
            return False

        # Guard against known false mergers (e.g. Java vs JavaScript)
        pair = frozenset([clean_a, clean_b])
        if pair in UNRELATED_PAIRS_CHECK:
            return False

        canon_a = cls.canonicalize(clean_a)
        canon_b = cls.canonicalize(clean_b)

        # Check canonical pair against unrelated check
        canon_pair = frozenset([canon_a, canon_b])
        if canon_pair in UNRELATED_PAIRS_CHECK:
            return False

        # Exact canonical match
        if canon_a == canon_b:
            return True

        return False

    @classmethod
    def normalize_list(cls, terms: List[str]) -> List[str]:
        """Normalizes and deduplicates a list of skills."""
        canonical_terms = []
        for term in terms:
            c = cls.canonicalize(term)
            if c and c not in canonical_terms:
                canonical_terms.append(c)
        return canonical_terms

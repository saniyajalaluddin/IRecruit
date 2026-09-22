"""Job description intelligence pipeline for extracting prioritized requirements strictly from JD text."""

import re
import uuid
from typing import Dict, List, Tuple
from backend.app.modules.job_descriptions.schemas import (
    ExtractedRequirement,
    ParsedJobDescription,
    RequirementCategory,
    RequirementPriority,
)

# JD Section Headers
JD_SECTION_PATTERNS = {
    "required_qualifications": re.compile(
        r"^(minimum\s+qualifications|basic\s+qualifications|required\s+qualifications|requirements|what\s+you\s+need|what\s+we're\s+looking\s+for|must\s+haves?)$",
        re.IGNORECASE,
    ),
    "preferred_qualifications": re.compile(
        r"^(preferred\s+qualifications|nice\s+to\s+haves?|bonus\s+points?|preferred\s+skills|what\s+would\s+be\s+great|preferred)$",
        re.IGNORECASE,
    ),
    "responsibilities": re.compile(
        r"^(responsibilities|what\s+you'll\s+do|key\s+responsibilities|role\s+overview|duties|what\s+you\s+will\s+do)$",
        re.IGNORECASE,
    ),
    "about_role": re.compile(
        r"^(about\s+the\s+role|about\s+the\s+job|summary|overview)$",
        re.IGNORECASE,
    ),
}

# Explicit priority indicators in sentence text
EXPLICIT_REQUIRED_REGEX = re.compile(
    r"\b(must\s+have|required|minimum|essential|mandatory|need|needs|necessary)\b",
    re.IGNORECASE,
)
EXPLICIT_PREFERRED_REGEX = re.compile(
    r"\b(preferred|nice\s+to\s+have|bonus|plus|pluses|ideally|ideal|optional|advantageous)\b",
    re.IGNORECASE,
)

# Category classifier regexes
EXPERIENCE_YEARS_REGEX = re.compile(r"\b(\d+\+?\s*(?:years?|yrs?))\b", re.IGNORECASE)
EDUCATION_REGEX = re.compile(
    r"\b(bachelor(?:'s)?|master(?:'s)?|ph\.?d\.?|degree|bs|ms|ba|computer\s+science|engineering)\b",
    re.IGNORECASE,
)
RESPONSIBILITY_VERB_REGEX = re.compile(
    r"^(design|develop|build|architect|maintain|lead|collaborate|participate|manage|deliver|write|own|create)\b",
    re.IGNORECASE,
)


class JobDescriptionIntelligenceParser:
    """Parses pasted job description and extracts prioritized requirements strictly from text."""

    @classmethod
    def segment_jd_sections(cls, text: str) -> Dict[str, List[str]]:
        """Segments JD into categorized section blocks."""
        lines = [line.strip() for line in text.split("\n")]
        sections: Dict[str, List[str]] = {}
        current_section = "general"

        for line in lines:
            if not line:
                continue

            clean_header = line.strip(":*# \t-")
            matched_sec = None
            if len(clean_header.split()) <= 4:
                for sec_name, pattern in JD_SECTION_PATTERNS.items():
                    if pattern.match(clean_header):
                        matched_sec = sec_name
                        break

            if matched_sec:
                current_section = matched_sec
                if current_section not in sections:
                    sections[current_section] = []
            else:
                if current_section not in sections:
                    sections[current_section] = []
                sections[current_section].append(line)

        return sections

    @classmethod
    def determine_priority_and_category(
        cls,
        line: str,
        section_context: str,
    ) -> Tuple[RequirementPriority, RequirementCategory]:
        """Infers priority strictly from explicit words or parent section context."""
        # 1. Check explicit inline priority keywords
        if EXPLICIT_PREFERRED_REGEX.search(line):
            priority = RequirementPriority.PREFERRED
        elif EXPLICIT_REQUIRED_REGEX.search(line):
            priority = RequirementPriority.REQUIRED
        elif section_context == "preferred_qualifications":
            priority = RequirementPriority.PREFERRED
        else:
            priority = RequirementPriority.REQUIRED

        # 2. Check Category
        clean_text = line.lstrip("-•* ").strip()
        if EDUCATION_REGEX.search(clean_text):
            category = RequirementCategory.EDUCATION
        elif EXPERIENCE_YEARS_REGEX.search(clean_text):
            category = RequirementCategory.EXPERIENCE
        elif section_context == "responsibilities" or RESPONSIBILITY_VERB_REGEX.match(clean_text):
            category = RequirementCategory.RESPONSIBILITY
        else:
            category = RequirementCategory.TECHNICAL_SKILL

        return priority, category

    @classmethod
    def extract_normalized_terms(cls, line: str) -> List[str]:
        """Extracts candidate keywords and technologies mentioned in the requirement."""
        from backend.app.modules.matching.engine import build_term_regex
        from backend.app.modules.matching.taxonomy import CANONICAL_SKILL_MAP

        clean = line.lstrip("-*• ").strip()
        # Remove parenthetical notes
        clean = re.sub(r"\(.*?\)", "", clean)
        # Split on commas, 'and', 'or', slashes
        parts = re.split(r"[,/]|(?:\s+(?:and|or|such\s+as|including|e\.g\.)\s+)", clean)
        terms = []
        for part in parts:
            tok = part.strip().strip(". ")
            tok = re.sub(
                r"^(?:\d+\+?\s+years(?:\s+of)?\s+)?(?:hands-on\s+)?(?:experience\s+(?:with|in)?|proficiency\s+in|knowledge\s+of|background\s+in|familiarity\s+with|understanding\s+of)\s+",
                "",
                tok,
                flags=re.IGNORECASE,
            ).strip()
            if 1 <= len(tok.split()) <= 5 and len(tok) >= 2:
                terms.append(tok.lower())

        # Also detect any canonical skill aliases mentioned directly in the line
        for alias, canonical in CANONICAL_SKILL_MAP.items():
            if len(alias) >= 2:
                reg = build_term_regex(alias)
                if reg.search(line):
                    terms.append(canonical)

        return list(dict.fromkeys(terms))

    @classmethod
    def parse(cls, text: str) -> ParsedJobDescription:
        """Parses full Job Description into structured prioritized requirements."""
        sections = cls.segment_jd_sections(text)
        requirements: List[ExtractedRequirement] = []

        req_counter = 1
        for sec_name, lines in sections.items():
            if sec_name == "about_role":
                continue

            for raw_line in lines:
                clean_line = raw_line.lstrip("-*•# \t").strip()
                # Filter out short noise or obvious section dividers
                if len(clean_line) < 10 or len(clean_line.split()) < 3:
                    continue

                priority, category = cls.determine_priority_and_category(clean_line, sec_name)
                terms = cls.extract_normalized_terms(clean_line)

                req = ExtractedRequirement(
                    id=f"req_{req_counter}",
                    text=clean_line,
                    category=category,
                    priority=priority,
                    normalized_terms=terms,
                )
                requirements.append(req)
                req_counter += 1

        required_count = sum(1 for r in requirements if r.priority == RequirementPriority.REQUIRED)
        preferred_count = sum(1 for r in requirements if r.priority == RequirementPriority.PREFERRED)

        # Inferred Title from first line if general
        first_line = text.strip().split("\n")[0].strip() if text.strip() else None
        title = first_line if first_line and len(first_line.split()) <= 6 else None

        return ParsedJobDescription(
            raw_text=text,
            job_title=title,
            requirements=requirements,
            required_count=required_count,
            preferred_count=preferred_count,
        )

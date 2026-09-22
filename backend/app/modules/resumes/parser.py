"""Resume intelligence pipeline for extracting structured resume sections without hallucination."""

import re
from typing import Dict, List, Optional
from backend.app.modules.resumes.schemas import (
    CertificationItem,
    EducationItem,
    ProjectItem,
    StructuredResume,
    WorkExperienceItem,
)

# Standard resume section header regex patterns
SECTION_HEADER_PATTERNS = {
    "summary": re.compile(
        r"^(professional\s+summary|executive\s+summary|summary|profile|about\s+me|objective)$",
        re.IGNORECASE,
    ),
    "skills": re.compile(
        r"^(technical\s+skills|skills\s*(&|and)?\s*competencies|skills|technologies|core\s+competencies|tools\s*(&|and)?\s*technologies)$",
        re.IGNORECASE,
    ),
    "experience": re.compile(
        r"^(work\s+experience|professional\s+experience|experience|employment\s+history|career\s+history|work\s+history)$",
        re.IGNORECASE,
    ),
    "education": re.compile(
        r"^(education|academic\s+background|educational\s+background|academic\s+history|academics)$",
        re.IGNORECASE,
    ),
    "projects": re.compile(
        r"^(projects|personal\s+projects|key\s+projects|academic\s+projects|technical\s+projects)$",
        re.IGNORECASE,
    ),
    "certifications": re.compile(
        r"^(certifications|licenses\s*(&|and)?\s*certifications|certificates|credentials)$",
        re.IGNORECASE,
    ),
    "achievements": re.compile(
        r"^(achievements|honors\s*(&|and)?\s*awards|awards|accomplishments)$",
        re.IGNORECASE,
    ),
    "leadership": re.compile(
        r"^(leadership|extracurricular\s+activities|volunteer\s+experience|volunteering)$",
        re.IGNORECASE,
    ),
}

DATE_RANGE_PATTERN = re.compile(
    r"((?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)?\s*'?\d{2,4})\s*(?:-|–|to|until)\s*((?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)?\s*'?\d{2,4}|present|current)",
    re.IGNORECASE,
)

DEGREE_PATTERN = re.compile(
    r"\b(bachelor(?:'s)?|b\.?s\.?|b\.?a\.?|b\.?tech|b\.?e\.?|master(?:'s)?|m\.?s\.?|m\.?a\.?|m\.?tech|ph\.?d\.?|associate(?:'s)?|diploma)\b",
    re.IGNORECASE,
)

YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")


class ResumeIntelligenceParser:
    """Parses normalized resume text into structured sections with zero fabrication."""

    @classmethod
    def segment_sections(cls, text: str) -> Dict[str, str]:
        """Segments text lines into section blocks based on detected section headers."""
        lines = [line.strip() for line in text.split("\n")]
        sections: Dict[str, List[str]] = {}
        current_section = "header"

        for line in lines:
            if not line:
                continue

            clean_header = line.strip(":").strip()
            # Check if line matches a known section header
            matched_sec = None
            if len(clean_header.split()) <= 4:
                for sec_name, pattern in SECTION_HEADER_PATTERNS.items():
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

        return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}

    @classmethod
    def extract_skills(cls, skills_text: Optional[str]) -> List[str]:
        """Extracts skills from skills section using comma, bullet, pipe, or newline delimiters."""
        if not skills_text:
            return []

        skills = []
        # Split on line breaks first
        for line in skills_text.split("\n"):
            # Strip subcategories like "Languages: Python, Go" or "Frameworks: React"
            if ":" in line and len(line.split(":")[0].split()) <= 3:
                line = line.split(":", 1)[1]

            # Split on commas, bullets, or pipes
            tokens = re.split(r"[,|•·\*\t]|\s-\s", line)
            for tok in tokens:
                clean_tok = tok.strip()
                if clean_tok and len(clean_tok) <= 40 and not clean_tok.startswith("-"):
                    skills.append(clean_tok)

        # Deduplicate while preserving order
        return list(dict.fromkeys(skills))

    @classmethod
    def extract_experience(cls, exp_text: Optional[str]) -> List[WorkExperienceItem]:
        """Extracts work experience records based on dates, company, and bullet points."""
        if not exp_text:
            return []

        experiences: List[WorkExperienceItem] = []
        lines = [l.strip() for l in exp_text.split("\n") if l.strip()]
        current_exp: Optional[WorkExperienceItem] = None

        for line in lines:
            date_match = DATE_RANGE_PATTERN.search(line)
            if date_match and (current_exp is None or len(current_exp.highlights) > 0 or len(experiences) == 0):
                # New role boundary detected
                if current_exp:
                    experiences.append(current_exp)

                date_str = date_match.group(0)
                # Remainder of line may contain company/title
                line_without_date = line.replace(date_str, "").strip(" |-,")
                parts = [p.strip() for p in re.split(r"[,|–-]", line_without_date) if p.strip()]

                title = parts[0] if parts else None
                company = parts[1] if len(parts) > 1 else None

                current_exp = WorkExperienceItem(
                    job_title=title,
                    company=company,
                    start_date=date_match.group(1),
                    end_date=date_match.group(2),
                    highlights=[],
                )
            else:
                if current_exp is not None:
                    # Treat as highlight / bullet point
                    bullet = line.lstrip("-*• ").strip()
                    if bullet:
                        current_exp.highlights.append(bullet)
                else:
                    # Preliminary header info before date line
                    parts = [p.strip() for p in re.split(r"[,|–-]", line) if p.strip()]
                    current_exp = WorkExperienceItem(
                        job_title=parts[0] if parts else line,
                        company=parts[1] if len(parts) > 1 else None,
                        highlights=[],
                    )

        if current_exp:
            experiences.append(current_exp)

        return experiences

    @classmethod
    def extract_education(cls, edu_text: Optional[str]) -> List[EducationItem]:
        """Extracts education entries, degree level, institution, and graduation year."""
        if not edu_text:
            return []

        entries: List[EducationItem] = []
        lines = [l.strip() for l in edu_text.split("\n") if l.strip()]

        for line in lines:
            degree_match = DEGREE_PATTERN.search(line)
            year_match = YEAR_PATTERN.search(line)

            degree_val = degree_match.group(0) if degree_match else None
            year_val = year_match.group(0) if year_match else None

            # Look for institution name
            institution = line
            if degree_val:
                institution = institution.replace(degree_val, "")
            if year_val:
                institution = institution.replace(year_val, "")
            institution = re.sub(r"[,|–-]", " ", institution).strip()

            entries.append(
                EducationItem(
                    degree=degree_val,
                    institution=institution or line,
                    graduation_year=year_val,
                )
            )

        return entries

    @classmethod
    def extract_projects(cls, proj_text: Optional[str]) -> List[ProjectItem]:
        """Extracts project records and technologies."""
        if not proj_text:
            return []

        projects: List[ProjectItem] = []
        lines = [l.strip() for l in proj_text.split("\n") if l.strip()]
        current_proj: Optional[ProjectItem] = None

        for line in lines:
            if line.startswith("-") or line.startswith("•"):
                if current_proj:
                    desc_line = line.lstrip("-•* ").strip()
                    if current_proj.description:
                        current_proj.description += " " + desc_line
                    else:
                        current_proj.description = desc_line
            else:
                if current_proj:
                    projects.append(current_proj)
                # Split title from tech stack if formatted like 'Project Name | Python, React'
                parts = [p.strip() for p in line.split("|")]
                title = parts[0]
                techs = [t.strip() for t in parts[1].split(",")] if len(parts) > 1 else []
                current_proj = ProjectItem(
                    title=title,
                    description=None,
                    technologies=techs,
                )

        if current_proj:
            projects.append(current_proj)

        return projects

    @classmethod
    def extract_certifications(cls, cert_text: Optional[str]) -> List[CertificationItem]:
        """Extracts certification credentials and year."""
        if not cert_text:
            return []

        certs = []
        for line in cert_text.split("\n"):
            clean = line.lstrip("-•* ").strip()
            if not clean:
                continue

            year_match = YEAR_PATTERN.search(clean)
            year_val = year_match.group(0) if year_match else None
            name = clean.replace(year_val, "").strip(" -(),") if year_val else clean

            certs.append(CertificationItem(name=name, year=year_val))

        return certs

    @classmethod
    def parse(cls, text: str) -> StructuredResume:
        """Processes normalized resume text into structured domain representation."""
        sections = cls.segment_sections(text)

        summary = sections.get("summary")
        skills = cls.extract_skills(sections.get("skills"))
        experiences = cls.extract_experience(sections.get("experience"))
        education = cls.extract_education(sections.get("education"))
        projects = cls.extract_projects(sections.get("projects"))
        certifications = cls.extract_certifications(sections.get("certifications"))

        # Candidate name from header
        header_text = sections.get("header", "")
        name = None
        if header_text:
            first_line = header_text.split("\n")[0].strip()
            if len(first_line.split()) <= 4 and not re.search(r"[@\d]", first_line):
                name = first_line

        return StructuredResume(
            candidate_name=name,
            summary=summary,
            skills=skills,
            work_experiences=experiences,
            education=education,
            projects=projects,
            certifications=certifications,
            raw_text=text,
        )

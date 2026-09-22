"""ATS Parsing Compatibility Analysis Engine."""

from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

from backend.app.modules.ats.schemas import (
    ATSCategory,
    ATSCategoryScore,
    ATSCompatibilityReport,
    ATSIssue,
    ATSIssueSeverity,
)

# Standard section headings recognized by ATS systems
STANDARD_HEADINGS: Dict[str, List[str]] = {
    "EXPERIENCE": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "work history",
    ],
    "EDUCATION": [
        "education",
        "academic background",
        "academic history",
        "educational background",
    ],
    "SKILLS": [
        "skills",
        "technical skills",
        "core competencies",
        "technical proficiencies",
        "areas of expertise",
    ],
    "PROJECTS": [
        "projects",
        "key projects",
        "personal projects",
        "technical projects",
    ],
    "CERTIFICATIONS": [
        "certifications",
        "licenses",
        "credentials",
        "certificates",
    ],
    "SUMMARY": [
        "summary",
        "professional summary",
        "profile",
        "executive summary",
        "about me",
    ],
}

# Known creative or ambiguous headings that confuse ATS parsers
NON_STANDARD_HEADING_PATTERNS = [
    r"\bwhere i(?:'ve| have) been\b",
    r"\bmy journey\b",
    r"\bwhat i do\b",
    r"\bninja skills\b",
    r"\bguru\b",
    r"\bpassions\b",
    r"\bthings i make\b",
    r"\blife story\b",
]

# Standard bullet characters
STANDARD_BULLETS = {"•", "-", "*", "–", "—", "·"}

# Strong action verbs for resume bullets
STRONG_ACTION_VERBS = {
    "accelerated", "achieved", "administered", "advised", "analyzed", "architected",
    "automated", "built", "centralized", "championed", "collaborated", "configured",
    "constructed", "created", "decreased", "delivered", "deployed", "designed",
    "developed", "devised", "directed", "documented", "drove", "engineered",
    "established", "executed", "expanded", "expedited", "formulated", "founded",
    "generated", "guided", "headed", "implemented", "improved", "increased",
    "initiated", "instituted", "integrated", "introduced", "launched", "led",
    "managed", "maximized", "mentored", "migrated", "minimized", "modernized",
    "monitored", "negotiated", "optimized", "orchestrated", "organized", "overhauled",
    "oversaw", "pioneered", "planned", "produced", "programmed", "published",
    "re-engineered", "redesigned", "reduced", "refactored", "resolved", "restructured",
    "revamped", "scaled", "simplified", "spearheaded", "standardized", "streamlined",
    "strengthened", "structured", "supervised", "trained", "transformed", "upgraded",
}

# Weak or passive opening phrases that ATS systems and recruiters penalize
PASSIVE_OPENERS = [
    r"^responsible for\b",
    r"^duties included\b",
    r"^worked on\b",
    r"^helped with\b",
    r"^assisted in\b",
    r"^tasked with\b",
]


class ATSCompatibilityEngine:
    """Evaluates resume text against ATS parsing standards."""

    def analyze(self, resume_text: str) -> ATSCompatibilityReport:
        """Run comprehensive ATS compatibility scan on resume text."""
        if not resume_text or not resume_text.strip():
            return self._empty_report()

        lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
        total_lines = len(lines)

        # 1. Section Headings Analysis
        heading_score, heading_findings, heading_issues, detected_heads, missing_heads = (
            self._analyze_section_headings(lines)
        )

        # 2. Formatting & Layout Safety Analysis
        format_score, format_findings, format_issues = self._analyze_formatting_safety(
            resume_text, lines
        )

        # 3. Contact Info Accessibility Analysis
        contact_score, contact_findings, contact_issues = self._analyze_contact_info(
            resume_text, lines
        )

        # 4. Date Consistency Analysis
        date_score, date_findings, date_issues = self._analyze_dates(resume_text)

        # 5. Bullet & Content Clarity Analysis
        bullet_score, bullet_findings, bullet_issues = self._analyze_bullets_and_clarity(
            lines
        )

        # Assemble Category Scores
        category_scores: Dict[str, ATSCategoryScore] = {
            ATSCategory.SECTION_HEADINGS.value: ATSCategoryScore(
                category=ATSCategory.SECTION_HEADINGS,
                score=heading_score,
                status="PASS" if heading_score >= 80 else ("WARNING" if heading_score >= 60 else "FAIL"),
                findings=heading_findings,
            ),
            ATSCategory.FORMATTING_SAFETY.value: ATSCategoryScore(
                category=ATSCategory.FORMATTING_SAFETY,
                score=format_score,
                status="PASS" if format_score >= 80 else ("WARNING" if format_score >= 60 else "FAIL"),
                findings=format_findings,
            ),
            ATSCategory.CONTACT_ACCESSIBILITY.value: ATSCategoryScore(
                category=ATSCategory.CONTACT_ACCESSIBILITY,
                score=contact_score,
                status="PASS" if contact_score >= 80 else ("WARNING" if contact_score >= 60 else "FAIL"),
                findings=contact_findings,
            ),
            ATSCategory.DATE_CONSISTENCY.value: ATSCategoryScore(
                category=ATSCategory.DATE_CONSISTENCY,
                score=date_score,
                status="PASS" if date_score >= 80 else ("WARNING" if date_score >= 60 else "FAIL"),
                findings=date_findings,
            ),
            ATSCategory.BULLET_STANDARDIZATION.value: ATSCategoryScore(
                category=ATSCategory.BULLET_STANDARDIZATION,
                score=bullet_score,
                status="PASS" if bullet_score >= 80 else ("WARNING" if bullet_score >= 60 else "FAIL"),
                findings=bullet_findings,
            ),
        }

        # Weighted Overall Score
        # Headings: 25%, Formatting: 25%, Contact: 20%, Dates: 15%, Bullets: 15%
        overall_score = round(
            (heading_score * 0.25)
            + (format_score * 0.25)
            + (contact_score * 0.20)
            + (date_score * 0.15)
            + (bullet_score * 0.15),
            1,
        )

        # Severe structural penalty: If 2 or more core sections (Experience, Skills, Education) are missing
        if len(missing_heads) >= 2:
            overall_score = min(overall_score, 60.0)

        grade = self._calculate_grade(overall_score)

        # Separate critical vs warnings
        all_issues = heading_issues + format_issues + contact_issues + date_issues + bullet_issues
        critical_issues = [i for i in all_issues if i.severity == ATSIssueSeverity.HIGH]
        warnings = [i for i in all_issues if i.severity in (ATSIssueSeverity.MEDIUM, ATSIssueSeverity.LOW)]

        # Consolidate actionable recommendations
        recommendations = [issue.recommendation for issue in all_issues if issue.recommendation]
        # Deduplicate while preserving order
        seen_recs: Set[str] = set()
        deduped_recs: List[str] = []
        for rec in recommendations:
            if rec not in seen_recs:
                seen_recs.add(rec)
                deduped_recs.append(rec)

        summary = (
            f"ATS Compatibility Score: {overall_score}/100 (Grade {grade}). "
            f"Detected {len(detected_heads)} standard section headings, "
            f"{len(critical_issues)} critical parsing risks, and {len(warnings)} formatting warnings."
        )

        return ATSCompatibilityReport(
            overall_score=overall_score,
            grade=grade,
            category_scores=category_scores,
            critical_issues=critical_issues,
            warnings=warnings,
            recommendations=deduped_recs,
            standard_headings_detected=detected_heads,
            missing_standard_headings=missing_heads,
            summary=summary,
        )

    def _analyze_section_headings(
        self, lines: List[str]
    ) -> Tuple[float, List[str], List[ATSIssue], List[str], List[str]]:
        """Evaluate ATS section headings."""
        detected_categories: Set[str] = set()
        findings: List[str] = []
        issues: List[ATSIssue] = []

        lower_lines = [l.lower() for l in lines]

        for cat, variations in STANDARD_HEADINGS.items():
            for line in lower_lines:
                # Direct match or line starts with standard heading
                clean_line = line.strip(" :#*-")
                if clean_line in variations or any(clean_line.startswith(v) for v in variations if len(clean_line) < 30):
                    detected_categories.add(cat)
                    break

        detected_heads = sorted(list(detected_categories))
        missing_heads = [
            cat for cat in ["EXPERIENCE", "EDUCATION", "SKILLS"]
            if cat not in detected_categories
        ]

        score = 100.0

        # Mandatory sections check
        if "EXPERIENCE" not in detected_categories:
            score -= 30.0
            issues.append(
                ATSIssue(
                    category=ATSCategory.SECTION_HEADINGS,
                    severity=ATSIssueSeverity.HIGH,
                    issue="Missing recognized 'Work Experience' heading.",
                    recommendation="Add a clear standard heading: 'Work Experience' or 'Professional Experience'.",
                )
            )

        if "SKILLS" not in detected_categories:
            score -= 20.0
            issues.append(
                ATSIssue(
                    category=ATSCategory.SECTION_HEADINGS,
                    severity=ATSIssueSeverity.HIGH,
                    issue="Missing recognized 'Skills' heading.",
                    recommendation="Add a dedicated 'Technical Skills' or 'Skills' section heading.",
                )
            )

        if "EDUCATION" not in detected_categories:
            score -= 15.0
            issues.append(
                ATSIssue(
                    category=ATSCategory.SECTION_HEADINGS,
                    severity=ATSIssueSeverity.MEDIUM,
                    issue="Missing recognized 'Education' heading.",
                    recommendation="Add a standard 'Education' section heading.",
                )
            )

        # Check for non-standard creative headings
        for pattern in NON_STANDARD_HEADING_PATTERNS:
            for line in lines:
                if re.search(pattern, line, re.IGNORECASE):
                    score -= 10.0
                    issues.append(
                        ATSIssue(
                            category=ATSCategory.SECTION_HEADINGS,
                            severity=ATSIssueSeverity.MEDIUM,
                            issue=f"Non-standard section header detected: '{line}'.",
                            evidence=line,
                            recommendation="Replace creative or informal headings with standard ATS labels (e.g. 'Work Experience', 'Skills').",
                        )
                    )
                    break

        score = max(0.0, min(100.0, score))
        findings.append(f"Detected {len(detected_heads)} standard sections: {', '.join(detected_heads) if detected_heads else 'None'}.")
        if missing_heads:
            findings.append(f"Missing core sections: {', '.join(missing_heads)}.")

        return score, findings, issues, detected_heads, missing_heads

    def _analyze_formatting_safety(
        self, text: str, lines: List[str]
    ) -> Tuple[float, List[str], List[ATSIssue]]:
        """Check for tables, multi-column artifacts, emojis, and special symbols."""
        score = 100.0
        findings: List[str] = []
        issues: List[ATSIssue] = []

        # 1. Detect markdown / ASCII tables
        # A real table has markdown table syntax (e.g. |---| or +---+), or multiple rows starting and ending with '|'
        table_rows = [
            l for l in lines
            if (l.startswith("|") and l.endswith("|") and l.count("|") >= 3)
            or re.search(r"\|[\s:\-]+\|", l)
            or re.match(r"^\+[-+]+\+$", l)
        ]
        if len(table_rows) >= 2 or any(re.search(r"\|[\s:\-]+\|", l) for l in lines):
            score -= 30.0
            issues.append(
                ATSIssue(
                    category=ATSCategory.FORMATTING_SAFETY,
                    severity=ATSIssueSeverity.HIGH,
                    issue="Table layout artifacts detected in resume.",
                    evidence=table_rows[0] if table_rows else "Markdown/ASCII table structure",
                    recommendation="Avoid multi-column tables or table dividers. Use single-column linear text layout.",
                )
            )
            findings.append("Table structures detected; older ATS parsers frequently jumble columns into incoherent text.")

        # 2. Detect wide tabular spacing / multi-column tab stops
        wide_tab_lines = [l for l in lines if re.search(r"(\t{2,}|\s{8,})", l)]
        if len(wide_tab_lines) > 5:
            score -= 15.0
            issues.append(
                ATSIssue(
                    category=ATSCategory.FORMATTING_SAFETY,
                    severity=ATSIssueSeverity.MEDIUM,
                    issue="Frequent multi-column spacing or wide tab stops detected.",
                    evidence=wide_tab_lines[0][:50],
                    recommendation="Use single-column left-aligned formatting rather than multi-column tab alignments.",
                )
            )
            findings.append("Multi-column layout patterns found; may disrupt ATS vertical reading order.")

        # 3. Detect emojis and non-standard symbols
        emoji_pattern = re.compile(
            r"[\U00010000-\U0010ffff"  # Supplementary planes (emojis)
            r"\u2600-\u26ff"          # Misc symbols
            r"\u2700-\u27bf"          # Dingbats
            r"\u2190-\u21ff]"         # Arrows
        )
        emojis_found = emoji_pattern.findall(text)
        if emojis_found:
            score -= 15.0
            unique_emojis = list(set(emojis_found))[:5]
            issues.append(
                ATSIssue(
                    category=ATSCategory.FORMATTING_SAFETY,
                    severity=ATSIssueSeverity.MEDIUM,
                    issue=f"Graphic symbols or emojis detected: {' '.join(unique_emojis)}.",
                    evidence=" ".join(unique_emojis),
                    recommendation="Remove emojis, decorative glyphs, and non-standard symbols. Use standard text and bullets.",
                )
            )
            findings.append(f"Found {len(emojis_found)} non-standard symbols/emojis that may corrupt text parsing.")

        if score == 100.0:
            findings.append("No hazardous layout tables, columns, or graphic symbols detected.")

        score = max(0.0, min(100.0, score))
        return score, findings, issues

    def _analyze_contact_info(
        self, text: str, lines: List[str]
    ) -> Tuple[float, List[str], List[ATSIssue]]:
        """Verify presence and safe placement of contact information."""
        score = 100.0
        findings: List[str] = []
        issues: List[ATSIssue] = []

        # Check for email
        email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
        # Check for phone
        phone_match = re.search(
            r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b",
            text,
        )
        # Check for linkedin
        linkedin_match = re.search(r"linkedin\.com/(?:in|company)/[a-zA-Z0-9_-]+", text, re.IGNORECASE)

        if not email_match:
            score -= 40.0
            issues.append(
                ATSIssue(
                    category=ATSCategory.CONTACT_ACCESSIBILITY,
                    severity=ATSIssueSeverity.HIGH,
                    issue="No email address found in the document body.",
                    recommendation="Ensure a valid, professional email is placed in plain text at the top of the resume.",
                )
            )
        else:
            findings.append("Professional email address detected.")

        if not phone_match:
            score -= 20.0
            issues.append(
                ATSIssue(
                    category=ATSCategory.CONTACT_ACCESSIBILITY,
                    severity=ATSIssueSeverity.MEDIUM,
                    issue="No contact phone number detected.",
                    recommendation="Include a phone number formatted with standard separators in the contact section.",
                )
            )
        else:
            findings.append("Phone number detected.")

        if linkedin_match:
            findings.append("LinkedIn profile link detected.")

        # Check placement: Is contact info in the first 25% of lines?
        if email_match and len(lines) > 10:
            top_lines_count = max(5, int(len(lines) * 0.25))
            top_text = " ".join(lines[:top_lines_count])
            if email_match.group(0) not in top_text:
                score -= 20.0
                issues.append(
                    ATSIssue(
                        category=ATSCategory.CONTACT_ACCESSIBILITY,
                        severity=ATSIssueSeverity.MEDIUM,
                        issue="Email address is placed far down in the resume rather than at the top.",
                        recommendation="Place all contact info in the top header block of the document body.",
                    )
                )

        score = max(0.0, min(100.0, score))
        return score, findings, issues

    def _analyze_dates(self, text: str) -> Tuple[float, List[str], List[ATSIssue]]:
        """Verify date consistency across employment history."""
        score = 100.0
        findings: List[str] = []
        issues: List[ATSIssue] = []

        # Find various date patterns
        # 1. Month Year: Jan 2021, January 2021
        month_year_pattern = r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}\b"
        # 2. MM/YYYY or MM-YYYY
        num_month_year_pattern = r"\b(?:0[1-9]|1[0-2])[/-]\d{4}\b"
        # 3. Just YYYY (e.g. 2019 - 2023)
        year_only_pattern = r"\b(?:19|20)\d{2}\b"

        month_years = re.findall(month_year_pattern, text, re.IGNORECASE)
        num_dates = re.findall(num_month_year_pattern, text)
        years = re.findall(year_only_pattern, text)

        if not years:
            score -= 30.0
            issues.append(
                ATSIssue(
                    category=ATSCategory.DATE_CONSISTENCY,
                    severity=ATSIssueSeverity.HIGH,
                    issue="No employment dates or years detected.",
                    recommendation="Add start and end dates (e.g., 'MM/YYYY' or 'Month YYYY') to all job positions.",
                )
            )
            findings.append("No dates detected; ATS parsers cannot compute total years of experience.")
        else:
            findings.append(f"Found {len(years)} chronological date anchors.")
            # Check for mixed formatting if both textual month and numeric month formats are used heavily
            if len(month_years) >= 2 and len(num_dates) >= 2:
                score -= 15.0
                issues.append(
                    ATSIssue(
                        category=ATSCategory.DATE_CONSISTENCY,
                        severity=ATSIssueSeverity.LOW,
                        issue="Inconsistent date formatting (mixing 'Month YYYY' with 'MM/YYYY').",
                        evidence=f"Example formats found: {month_years[0]} vs {num_dates[0]}",
                        recommendation="Standardize on a single consistent date format throughout (recommended: 'Mon YYYY' or 'MM/YYYY').",
                    )
                )
                findings.append("Mixed date formats detected; standardizing improves chronological parsing accuracy.")

        score = max(0.0, min(100.0, score))
        return score, findings, issues

    def _analyze_bullets_and_clarity(
        self, lines: List[str]
    ) -> Tuple[float, List[str], List[ATSIssue]]:
        """Evaluate bullet glyphs, action verbs, and passive phrasing."""
        score = 100.0
        findings: List[str] = []
        issues: List[ATSIssue] = []

        bullet_lines: List[str] = []
        non_standard_bullets: Set[str] = set()

        for line in lines:
            if not line:
                continue
            first_char = line[0]
            if first_char in STANDARD_BULLETS:
                bullet_lines.append(line.lstrip("•-*–—· \t"))
            elif line.startswith(("- ", "* ", "+ ")):
                bullet_lines.append(line[2:].strip())
            elif ord(first_char) > 127 and first_char not in STANDARD_BULLETS:
                # Potential non-standard bullet (arrow, checkmark, dingbat)
                non_standard_bullets.add(first_char)
                bullet_lines.append(line[1:].strip())

        if not bullet_lines:
            score -= 25.0
            issues.append(
                ATSIssue(
                    category=ATSCategory.BULLET_STANDARDIZATION,
                    severity=ATSIssueSeverity.MEDIUM,
                    issue="No bullet points or structured list items detected in resume.",
                    recommendation="Structure your work experience achievements into concise bullet points.",
                )
            )
            findings.append("No bullet points detected; unstructured paragraphs hurt ATS content segmentation.")
        elif non_standard_bullets:
            score -= 15.0
            issues.append(
                ATSIssue(
                    category=ATSCategory.BULLET_STANDARDIZATION,
                    severity=ATSIssueSeverity.MEDIUM,
                    issue=f"Non-standard bullet characters used: {' '.join(non_standard_bullets)}.",
                    evidence=" ".join(non_standard_bullets),
                    recommendation="Use standard round bullet points (•) or hyphens (-) for list items.",
                )
            )
            findings.append("Custom bullet glyphs detected that may turn into garbled characters in legacy ATS parsers.")
        else:
            findings.append("Standard bullet point characters utilized.")

        # Check for passive openers vs strong action verbs
        passive_count = 0
        action_count = 0

        for b_text in bullet_lines:
            lower_b = b_text.lower().strip()
            # Check passive opener
            if any(re.search(p, lower_b) for p in PASSIVE_OPENERS):
                passive_count += 1
            # Check strong action verb at start
            first_word = lower_b.split()[0] if lower_b.split() else ""
            clean_word = re.sub(r"[^a-z-]", "", first_word)
            if clean_word in STRONG_ACTION_VERBS:
                action_count += 1

        if passive_count > 0:
            score -= min(20.0, passive_count * 5.0)
            issues.append(
                ATSIssue(
                    category=ATSCategory.BULLET_STANDARDIZATION,
                    severity=ATSIssueSeverity.LOW,
                    issue=f"Found {passive_count} bullet points starting with passive phrases (e.g. 'Responsible for').",
                    recommendation="Begin bullet points with strong active verbs (e.g., 'Engineered', 'Optimized', 'Spearheaded') rather than passive duties.",
                )
            )

        findings.append(f"Analyzed {len(bullet_lines)} bullet items: {action_count} lead with strong action verbs, {passive_count} use passive phrasing.")

        score = max(0.0, min(100.0, score))
        return score, findings, issues

    def _calculate_grade(self, score: float) -> str:
        if score >= 90.0:
            return "A"
        elif score >= 80.0:
            return "B"
        elif score >= 70.0:
            return "C"
        elif score >= 60.0:
            return "D"
        return "F"

    def _empty_report(self) -> ATSCompatibilityReport:
        return ATSCompatibilityReport(
            overall_score=0.0,
            grade="F",
            category_scores={},
            critical_issues=[
                ATSIssue(
                    category=ATSCategory.CONTENT_CLARITY,
                    severity=ATSIssueSeverity.HIGH,
                    issue="Empty or unreadable document content.",
                    recommendation="Submit valid resume text or document for analysis.",
                )
            ],
            warnings=[],
            recommendations=["Submit a resume containing readable text content."],
            standard_headings_detected=[],
            missing_standard_headings=["EXPERIENCE", "EDUCATION", "SKILLS"],
            summary="Resume text is empty or unparseable.",
        )

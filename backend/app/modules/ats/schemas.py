"""Schemas for ATS Parsing Compatibility Engine."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ATSIssueSeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class ATSCategory(str, Enum):
    SECTION_HEADINGS = "SECTION_HEADINGS"
    FORMATTING_SAFETY = "FORMATTING_SAFETY"
    CONTACT_ACCESSIBILITY = "CONTACT_ACCESSIBILITY"
    DATE_CONSISTENCY = "DATE_CONSISTENCY"
    BULLET_STANDARDIZATION = "BULLET_STANDARDIZATION"
    CONTENT_CLARITY = "CONTENT_CLARITY"


class ATSIssue(BaseModel):
    """An issue that negatively impacts ATS parseability."""
    category: ATSCategory
    severity: ATSIssueSeverity
    issue: str
    evidence: Optional[str] = None
    recommendation: str


class ATSCategoryScore(BaseModel):
    """Score and evaluation for an individual ATS category."""
    category: ATSCategory
    score: float = Field(..., ge=0.0, le=100.0)
    status: str  # "PASS", "WARNING", "FAIL"
    findings: List[str] = Field(default_factory=list)


class ATSCompatibilityReport(BaseModel):
    """Complete ATS parsing compatibility analysis report."""
    overall_score: float = Field(..., ge=0.0, le=100.0)
    grade: str  # "A", "B", "C", "D", "F"
    category_scores: Dict[str, ATSCategoryScore] = Field(default_factory=dict)
    critical_issues: List[ATSIssue] = Field(default_factory=list)
    warnings: List[ATSIssue] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    standard_headings_detected: List[str] = Field(default_factory=list)
    missing_standard_headings: List[str] = Field(default_factory=list)
    summary: str

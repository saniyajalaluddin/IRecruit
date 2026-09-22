"""Job description domain models and requirement schemas."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class RequirementPriority(str, Enum):
    """Priority assigned strictly by explicit JD language."""
    REQUIRED = "required"  # must-have, minimum qualifications, required
    PREFERRED = "preferred"  # nice-to-have, bonus, preferred, plus


class RequirementCategory(str, Enum):
    """Categorization of extracted requirements."""
    TECHNICAL_SKILL = "technical_skill"
    RESPONSIBILITY = "responsibility"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    DOMAIN_KNOWLEDGE = "domain_knowledge"
    CERTIFICATION = "certification"


class ExtractedRequirement(BaseModel):
    """Single requirement parsed from a Job Description."""
    id: str = Field(..., description="Unique requirement ID within analysis")
    text: str = Field(..., description="Raw requirement statement from JD")
    category: RequirementCategory = Field(default=RequirementCategory.TECHNICAL_SKILL)
    priority: RequirementPriority = Field(default=RequirementPriority.REQUIRED)
    normalized_terms: List[str] = Field(default_factory=list, description="Canonical normalized terms / skills")


class ParsedJobDescription(BaseModel):
    """Complete parsed representation of a Job Description."""
    raw_text: str = Field(..., description="Pasted raw JD text")
    job_title: Optional[str] = Field(None, description="Inferred or stated job title")
    company_name: Optional[str] = Field(None, description="Company name if present")
    requirements: List[ExtractedRequirement] = Field(default_factory=list)
    required_count: int = Field(default=0)
    preferred_count: int = Field(default=0)

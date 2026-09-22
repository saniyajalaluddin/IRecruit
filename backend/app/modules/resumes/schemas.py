"""Structured resume domain schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field


class WorkExperienceItem(BaseModel):
    """Extracted work experience record."""
    job_title: Optional[str] = Field(None, description="Job title / role")
    company: Optional[str] = Field(None, description="Company or organization name")
    start_date: Optional[str] = Field(None, description="Start date / year")
    end_date: Optional[str] = Field(None, description="End date or Present")
    description: Optional[str] = Field(None, description="Role summary")
    highlights: List[str] = Field(default_factory=list, description="Bullet points and achievements")
    technologies: List[str] = Field(default_factory=list, description="Explicit technologies referenced")


class EducationItem(BaseModel):
    """Extracted education entry."""
    degree: Optional[str] = Field(None, description="Degree or program title")
    institution: Optional[str] = Field(None, description="University, college, or school")
    field_of_study: Optional[str] = Field(None, description="Major / discipline")
    graduation_year: Optional[str] = Field(None, description="Graduation year")


class ProjectItem(BaseModel):
    """Extracted personal or professional project."""
    title: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project summary")
    technologies: List[str] = Field(default_factory=list, description="Technologies or tools used")
    url: Optional[str] = Field(None, description="Project or code link")


class CertificationItem(BaseModel):
    """Extracted certification or credential."""
    name: str = Field(..., description="Certification name")
    issuer: Optional[str] = Field(None, description="Issuing organization")
    year: Optional[str] = Field(None, description="Issuance year")


class StructuredResume(BaseModel):
    """Complete parsed structured representation of candidate resume."""
    candidate_name: Optional[str] = Field(None, description="Extracted candidate name (if available)")
    contact_email: Optional[str] = Field(None, description="Extracted email (PII masked when exported)")
    contact_phone: Optional[str] = Field(None, description="Extracted phone (PII masked when exported)")
    summary: Optional[str] = Field(None, description="Professional summary or objective")
    skills: List[str] = Field(default_factory=list, description="Directly listed skills and technologies")
    work_experiences: List[WorkExperienceItem] = Field(default_factory=list, description="Employment history")
    education: List[EducationItem] = Field(default_factory=list, description="Educational background")
    projects: List[ProjectItem] = Field(default_factory=list, description="Portfolio projects")
    certifications: List[CertificationItem] = Field(default_factory=list, description="Certifications and licenses")
    raw_text: str = Field(..., description="Underlying normalized text")

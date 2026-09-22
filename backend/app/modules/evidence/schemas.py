"""Evidence extraction and grounded evidence trail schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.modules.matching.schemas import MatchLevel


class EvidenceSnippet(BaseModel):
    """Specific verbatim or paraphrased excerpt from the candidate's resume."""
    quote: str = Field(..., description="Excerpt from resume supporting or relating to the requirement")
    section_source: str = Field(..., description="Section of origin, e.g. experience, projects, skills")
    context: Optional[str] = Field(None, description="Surrounding context (e.g. company, role, dates)")
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0)


class RequirementEvidence(BaseModel):
    """Full grounded evidence representation for a single requirement."""
    requirement_id: str
    requirement_text: str
    classification: MatchLevel
    snippets: List[EvidenceSnippet] = Field(default_factory=list)
    explanation: str = Field(
        ...,
        description="Grounded explanation explaining why classification was made. "
                    "If missing: 'No supporting evidence was found in the submitted resume.'",
    )
    has_evidence: bool = Field(default=False)

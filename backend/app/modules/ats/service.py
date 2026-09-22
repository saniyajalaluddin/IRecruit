"""ATS Compatibility Service."""

from __future__ import annotations

from typing import Optional

from backend.app.modules.ats.engine import ATSCompatibilityEngine
from backend.app.modules.ats.schemas import ATSCompatibilityReport


class ATSCompatibilityService:
    """Service facade for ATS compatibility evaluations."""

    def __init__(self, engine: Optional[ATSCompatibilityEngine] = None):
        self._engine = engine or ATSCompatibilityEngine()

    def analyze_resume_text(self, resume_text: str) -> ATSCompatibilityReport:
        """Run ATS compatibility analysis on raw or parsed resume text."""
        return self._engine.analyze(resume_text)

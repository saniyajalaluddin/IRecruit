"""Resume intelligence service implementation."""

from typing import Protocol
from backend.app.modules.resumes.parser import ResumeIntelligenceParser
from backend.app.modules.resumes.schemas import StructuredResume


class ResumeParserInterface(Protocol):
    """Protocol for parsing normalized text into structured resume sections."""

    async def parse(self, text: str) -> StructuredResume:
        """Parses extracted document text into structured resume components."""
        ...


class ResumeService:
    """Provides resume parsing and section intelligence services."""

    def __init__(self, parser: ResumeIntelligenceParser | None = None):
        self.parser = parser or ResumeIntelligenceParser()

    async def parse(self, text: str) -> StructuredResume:
        """Parses normalized text into structured domain models without hallucination."""
        return self.parser.parse(text)

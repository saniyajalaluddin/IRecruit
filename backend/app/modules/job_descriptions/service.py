"""Job description parsing and requirement extraction service implementation."""

from typing import Protocol
from backend.app.modules.job_descriptions.parser import JobDescriptionIntelligenceParser
from backend.app.modules.job_descriptions.schemas import ParsedJobDescription


class JobDescriptionParserInterface(Protocol):
    """Protocol for parsing job descriptions and extracting prioritized requirements."""

    async def parse(self, text: str) -> ParsedJobDescription:
        """Parses JD text and extracts categorized requirements strictly based on JD phrasing."""
        ...


class JobDescriptionService:
    """Service providing job description intelligence and requirement extraction."""

    def __init__(self, parser: JobDescriptionIntelligenceParser | None = None):
        self.parser = parser or JobDescriptionIntelligenceParser()

    async def parse(self, text: str) -> ParsedJobDescription:
        """Parses JD text and extracts prioritized requirements deterministically."""
        return self.parser.parse(text)

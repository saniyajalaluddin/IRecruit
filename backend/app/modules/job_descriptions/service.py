"""Job description parsing and requirement extraction service protocol."""

from typing import Protocol
from backend.app.modules.job_descriptions.schemas import ParsedJobDescription


class JobDescriptionParserInterface(Protocol):
    """Protocol for parsing job descriptions and extracting prioritized requirements."""

    async def parse(self, text: str) -> ParsedJobDescription:
        """Parses JD text and extracts categorized requirements strictly based on JD phrasing."""
        ...

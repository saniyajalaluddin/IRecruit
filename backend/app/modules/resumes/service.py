"""Resume intelligence service protocol and interfaces."""

from typing import Protocol
from backend.app.modules.resumes.schemas import StructuredResume


class ResumeParserInterface(Protocol):
    """Protocol for parsing normalized text into structured resume sections."""

    async def parse(self, text: str) -> StructuredResume:
        """Parses extracted document text into structured resume components."""
        ...

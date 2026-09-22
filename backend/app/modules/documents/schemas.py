"""Document upload and storage schemas."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class DocumentFormat(str, Enum):
    """Supported document upload formats."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class DocumentMetadata(BaseModel):
    """Metadata regarding an uploaded resume file."""
    original_filename: str = Field(..., description="Original user file name")
    sanitized_filename: str = Field(..., description="Sanitized safe file name")
    format: DocumentFormat = Field(..., description="Detected format")
    content_type: str = Field(..., description="MIME content type")
    file_size_bytes: int = Field(..., description="File size in bytes")
    storage_path: Optional[str] = Field(None, description="Temporary or persistent storage path")
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ParsedDocument(BaseModel):
    """Raw parsed text output from document extraction."""
    raw_text: str = Field(..., description="Extracted plaintext")
    normalized_text: str = Field(..., description="Cleaned and normalized text")
    page_count: int = Field(default=1, description="Number of detected pages")
    word_count: int = Field(..., description="Total word count")
    metadata: DocumentMetadata
    is_empty: bool = Field(default=False)
    extraction_warning: Optional[str] = Field(None)

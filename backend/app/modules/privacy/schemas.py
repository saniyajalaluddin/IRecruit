"""Privacy and PII management schemas."""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class PIIType(str, Enum):
    """Categorization of sensitive personal identifiers."""
    EMAIL = "email"
    PHONE = "phone"
    PHYSICAL_ADDRESS = "physical_address"
    SSN = "ssn"
    LINKEDIN = "linkedin_url"
    PERSON_NAME = "person_name"


class PIISpan(BaseModel):
    """Detected location and type of sensitive PII in raw text."""
    pii_type: PIIType
    start_char: int
    end_char: int
    masked_value: str


class RedactionResult(BaseModel):
    """Output of PII minimization process."""
    sanitized_text: str
    detected_count: int
    redacted_types: List[PIIType]
    spans: List[PIISpan]


class PrivacyAuditEventType(str, Enum):
    """Audit log classification for privacy events."""
    RESUME_INGESTED = "resume_ingested"
    PII_REDACTED = "pii_redacted"
    ANONYMOUS_ANALYSIS_CREATED = "anonymous_analysis_created"
    ANALYSIS_ACCESSED = "analysis_accessed"
    DATA_DELETED = "data_deleted"
    RETENTION_PURGED = "retention_purged"


class PrivacyAuditEntry(BaseModel):
    """Audit record for user privacy compliance."""
    event_type: PrivacyAuditEventType
    user_id: Optional[str] = None
    resource_id: str
    details: Dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

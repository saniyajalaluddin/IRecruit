"""Privacy and PII management schemas."""

from __future__ import annotations

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
    ZIP_CODE = "zip_code"
    IP_ADDRESS = "ip_address"
    PERSON_NAME = "person_name"


class RedactionMode(str, Enum):
    """Action to take on detected sensitive identifiers."""
    MASK = "MASK"          # Replace with [REDACTED_{TYPE}]
    TOKENIZE = "TOKENIZE"  # Replace with reversible/reference token {{ANON_{TYPE}_{N}}}
    REMOVE = "REMOVE"      # Strip completely


class RedactionOptions(BaseModel):
    """Configuration options for PII minimization."""
    mode: RedactionMode = RedactionMode.MASK
    redact_email: bool = True
    redact_phone: bool = True
    redact_ssn: bool = True
    redact_linkedin: bool = True
    redact_address: bool = True
    redact_ip: bool = True


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
    spans: List[PIISpan] = Field(default_factory=list)
    token_map: Dict[str, str] = Field(default_factory=dict)


class PrivacyAuditEventType(str, Enum):
    """Audit log classification for privacy events."""
    RESUME_INGESTED = "resume_ingested"
    PII_REDACTED = "pii_redacted"
    ANONYMOUS_ANALYSIS_CREATED = "anonymous_analysis_created"
    ANALYSIS_ACCESSED = "analysis_accessed"
    DATA_DELETED = "data_deleted"
    RETENTION_PURGED = "retention_purged"


class PrivacyAuditEntry(BaseModel):
    """Audit record for user privacy compliance without retaining raw PII."""
    event_type: PrivacyAuditEventType
    user_id: Optional[str] = None
    resource_id: str
    details: Dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

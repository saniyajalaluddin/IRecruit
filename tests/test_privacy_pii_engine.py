"""Unit tests for Phase 21: Privacy & PII Engine."""

import pytest
from backend.app.modules.privacy.schemas import (
    PIIType,
    PrivacyAuditEventType,
    RedactionMode,
    RedactionOptions,
)
from backend.app.modules.privacy.service import PIIService, PrivacyAuditService


@pytest.fixture
def sample_pii_text():
    return (
        "Candidate: Jane Doe\n"
        "Email: jane.doe@techcorp.com\n"
        "Phone: +1 (555) 867-5309\n"
        "SSN: 000-12-3456\n"
        "Address: 742 Evergreen Terrace\n"
        "LinkedIn: https://www.linkedin.com/in/janedoe/\n"
        "Network IP: 10.0.4.15\n"
        "Skills: Python, FastAPI, Docker, Kubernetes\n"
        "Experience: Senior Backend Engineer at CloudScale Inc."
    )


def test_standard_mask_redaction(sample_pii_text):
    result = PIIService.redact_pii(sample_pii_text)

    # Asserts that PII is masked
    assert "[REDACTED_EMAIL]" in result.sanitized_text
    assert "[REDACTED_PHONE]" in result.sanitized_text
    assert "[REDACTED_SSN]" in result.sanitized_text
    assert "[REDACTED_LINKEDIN_URL]" in result.sanitized_text
    assert "[REDACTED_PHYSICAL_ADDRESS]" in result.sanitized_text
    assert "[REDACTED_IP_ADDRESS]" in result.sanitized_text

    # Zero-leakage verification: Raw identifiers must not exist in sanitized text
    assert "jane.doe@techcorp.com" not in result.sanitized_text
    assert "867-5309" not in result.sanitized_text
    assert "000-12-3456" not in result.sanitized_text
    assert "742 Evergreen Terrace" not in result.sanitized_text
    assert "https://www.linkedin.com/in/janedoe/" not in result.sanitized_text
    assert "10.0.4.15" not in result.sanitized_text

    # Candidate skills and experiences must be preserved!
    assert "Python, FastAPI, Docker, Kubernetes" in result.sanitized_text
    assert "Senior Backend Engineer at CloudScale Inc." in result.sanitized_text

    assert result.detected_count >= 5
    assert PIIType.EMAIL in result.redacted_types
    assert PIIType.SSN in result.redacted_types


def test_tokenize_mode(sample_pii_text):
    opts = RedactionOptions(mode=RedactionMode.TOKENIZE)
    result = PIIService.redact_pii(sample_pii_text, options=opts)

    assert "{{ANON_EMAIL_1}}" in result.sanitized_text
    assert "{{ANON_PHONE_1}}" in result.sanitized_text
    assert "{{ANON_SSN_1}}" in result.sanitized_text

    # Token map contains the mapping for authorized re-identification
    assert result.token_map["{{ANON_EMAIL_1}}"] == "jane.doe@techcorp.com"
    assert result.token_map["{{ANON_SSN_1}}"] == "000-12-3456"


def test_remove_mode(sample_pii_text):
    opts = RedactionOptions(mode=RedactionMode.REMOVE)
    result = PIIService.redact_pii(sample_pii_text, options=opts)

    assert "[REDACTED" not in result.sanitized_text
    assert "{{ANON" not in result.sanitized_text
    assert "jane.doe@techcorp.com" not in result.sanitized_text
    assert "000-12-3456" not in result.sanitized_text


def test_selective_redaction(sample_pii_text):
    # Only redact SSN and Email, keep phone and address
    opts = RedactionOptions(
        mode=RedactionMode.MASK,
        redact_ssn=True,
        redact_email=True,
        redact_phone=False,
        redact_address=False,
        redact_linkedin=False,
        redact_ip=False,
    )
    result = PIIService.redact_pii(sample_pii_text, options=opts)

    assert "[REDACTED_SSN]" in result.sanitized_text
    assert "[REDACTED_EMAIL]" in result.sanitized_text
    assert "867-5309" in result.sanitized_text
    assert "742 Evergreen Terrace" in result.sanitized_text


def test_privacy_audit_service():
    audit_service = PrivacyAuditService()
    entry = audit_service.record_event(
        event_type=PrivacyAuditEventType.PII_REDACTED,
        resource_id="resume-uuid-101",
        user_id="user-uuid-505",
        details={"types_redacted": "email, ssn", "count": "2"},
    )

    assert entry.event_type == PrivacyAuditEventType.PII_REDACTED
    assert entry.resource_id == "resume-uuid-101"
    assert entry.user_id == "user-uuid-505"

    events = audit_service.get_events("resume-uuid-101")
    assert len(events) == 1
    assert events[0].details["count"] == "2"

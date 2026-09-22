"""Privacy service for detecting and redacting PII from documents before external inference."""

import re
from typing import List
from backend.app.modules.privacy.schemas import PIISpan, PIIType, RedactionResult

# High-confidence Regex Patterns for PII Detection
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
PHONE_REGEX = re.compile(
    r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b"
)
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
LINKEDIN_REGEX = re.compile(r"https?://([a-z]{2,3}\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?", re.IGNORECASE)


class PIIService:
    """Detects and redacts candidate PII to prevent unnecessary external transmission."""

    @classmethod
    def redact_pii(cls, text: str) -> RedactionResult:
        """Minimizes sensitive personal data in text, replacing with anonymized tokens."""
        spans: List[PIISpan] = []
        redacted_types = set()
        sanitized = text

        # 1. Redact SSNs
        for match in SSN_REGEX.finditer(sanitized):
            redacted_types.add(PIIType.SSN)
            spans.append(
                PIISpan(
                    pii_type=PIIType.SSN,
                    start_char=match.start(),
                    end_char=match.end(),
                    masked_value="[REDACTED_SSN]",
                )
            )
        sanitized = SSN_REGEX.sub("[REDACTED_SSN]", sanitized)

        # 2. Redact Emails
        for match in EMAIL_REGEX.finditer(sanitized):
            redacted_types.add(PIIType.EMAIL)
            spans.append(
                PIISpan(
                    pii_type=PIIType.EMAIL,
                    start_char=match.start(),
                    end_char=match.end(),
                    masked_value="[REDACTED_EMAIL]",
                )
            )
        sanitized = EMAIL_REGEX.sub("[REDACTED_EMAIL]", sanitized)

        # 3. Redact Phone Numbers (min length check to avoid misidentifying year numbers or metrics)
        for match in PHONE_REGEX.finditer(sanitized):
            digits = re.sub(r"\D", "", match.group())
            if len(digits) >= 10:
                redacted_types.add(PIIType.PHONE)
                spans.append(
                    PIISpan(
                        pii_type=PIIType.PHONE,
                        start_char=match.start(),
                        end_char=match.end(),
                        masked_value="[REDACTED_PHONE]",
                    )
                )
        sanitized = PHONE_REGEX.sub(
            lambda m: "[REDACTED_PHONE]" if len(re.sub(r"\D", "", m.group())) >= 10 else m.group(),
            sanitized,
        )

        return RedactionResult(
            sanitized_text=sanitized,
            detected_count=len(spans),
            redacted_types=list(redacted_types),
            spans=spans,
        )

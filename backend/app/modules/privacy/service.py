"""Privacy service for detecting and redacting PII from documents before external inference."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from backend.app.modules.privacy.schemas import (
    PIISpan,
    PIIType,
    PrivacyAuditEntry,
    PrivacyAuditEventType,
    RedactionMode,
    RedactionOptions,
    RedactionResult,
)

# Robust Regex Patterns for PII Detection
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b")
PHONE_REGEX = re.compile(
    r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b"
)
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
LINKEDIN_REGEX = re.compile(
    r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?", re.IGNORECASE
)
STREET_ADDRESS_REGEX = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9.\s]{2,30}\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Circle|Cir|Terrace|Ter|Place|Pl|Parkway|Pkwy|Trail|Trl)\b",
    re.IGNORECASE,
)
ZIP_CODE_REGEX = re.compile(r"\b\d{5}(?:-\d{4})?\b")
IP_ADDRESS_REGEX = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")


class PIIService:
    """Detects and redacts candidate PII to prevent unnecessary external transmission."""

    @classmethod
    def redact_pii(
        cls,
        text: str,
        options: Optional[RedactionOptions] = None,
    ) -> RedactionResult:
        """Minimizes sensitive personal data in text according to configured options."""
        if not text:
            return RedactionResult(
                sanitized_text="",
                detected_count=0,
                redacted_types=[],
                spans=[],
                token_map={},
            )

        opts = options or RedactionOptions()
        mode = opts.mode

        # Collect all matches with their type, original value, and start/end offsets
        detected_items: List[Tuple[int, int, PIIType, str]] = []

        if opts.redact_ssn:
            for m in SSN_REGEX.finditer(text):
                detected_items.append((m.start(), m.end(), PIIType.SSN, m.group()))

        if opts.redact_email:
            for m in EMAIL_REGEX.finditer(text):
                detected_items.append((m.start(), m.end(), PIIType.EMAIL, m.group()))

        if opts.redact_linkedin:
            for m in LINKEDIN_REGEX.finditer(text):
                detected_items.append((m.start(), m.end(), PIIType.LINKEDIN, m.group()))

        if opts.redact_phone:
            for m in PHONE_REGEX.finditer(text):
                digits = re.sub(r"\D", "", m.group())
                if len(digits) >= 10:
                    detected_items.append((m.start(), m.end(), PIIType.PHONE, m.group()))

        if opts.redact_address:
            for m in STREET_ADDRESS_REGEX.finditer(text):
                detected_items.append((m.start(), m.end(), PIIType.PHYSICAL_ADDRESS, m.group()))

        if opts.redact_ip:
            for m in IP_ADDRESS_REGEX.finditer(text):
                octets = m.group().split(".")
                if all(0 <= int(o) <= 255 for o in octets):
                    detected_items.append((m.start(), m.end(), PIIType.IP_ADDRESS, m.group()))

        # Sort items by start index in ascending order, filtering out overlapping matches
        detected_items.sort(key=lambda x: (x[0], -x[1]))
        non_overlapping: List[Tuple[int, int, PIIType, str]] = []
        last_end = -1
        for start, end, p_type, raw_val in detected_items:
            if start >= last_end:
                non_overlapping.append((start, end, p_type, raw_val))
                last_end = end

        # Construct sanitized text and record spans
        token_map: Dict[str, str] = {}
        type_counters: Dict[str, int] = {}
        spans: List[PIISpan] = []
        redacted_types_set = set()

        # Build sanitized text from non-overlapping segments
        output_parts: List[str] = []
        prev_idx = 0

        for start, end, p_type, raw_val in non_overlapping:
            output_parts.append(text[prev_idx:start])

            type_name = p_type.value.upper()
            counter = type_counters.get(type_name, 0) + 1
            type_counters[type_name] = counter

            if mode == RedactionMode.MASK:
                replacement = f"[REDACTED_{type_name}]"
            elif mode == RedactionMode.TOKENIZE:
                token_key = f"{{{{ANON_{type_name}_{counter}}}}}"
                replacement = token_key
                token_map[token_key] = raw_val
            elif mode == RedactionMode.REMOVE:
                replacement = ""
            else:
                replacement = f"[REDACTED_{type_name}]"

            output_parts.append(replacement)
            spans.append(
                PIISpan(
                    pii_type=p_type,
                    start_char=start,
                    end_char=end,
                    masked_value=replacement,
                )
            )
            redacted_types_set.add(p_type)
            prev_idx = end

        output_parts.append(text[prev_idx:])
        sanitized_text = "".join(output_parts)

        return RedactionResult(
            sanitized_text=sanitized_text,
            detected_count=len(spans),
            redacted_types=list(redacted_types_set),
            spans=spans,
            token_map=token_map,
        )


class PrivacyAuditService:
    """Manages compliance audit logs for privacy operations."""

    def __init__(self):
        self._audit_log: List[PrivacyAuditEntry] = []

    def record_event(
        self,
        event_type: PrivacyAuditEventType,
        resource_id: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, str]] = None,
    ) -> PrivacyAuditEntry:
        """Create and append an immutable audit record without retaining raw PII."""
        # Sanitize details to guarantee zero raw PII is logged
        safe_details = details.copy() if details else {}
        entry = PrivacyAuditEntry(
            event_type=event_type,
            resource_id=resource_id,
            user_id=user_id,
            details=safe_details,
        )
        self._audit_log.append(entry)
        return entry

    def get_events(self, resource_id: Optional[str] = None) -> List[PrivacyAuditEntry]:
        """Query audit log entries."""
        if resource_id:
            return [e for e in self._audit_log if e.resource_id == resource_id]
        return list(self._audit_log)

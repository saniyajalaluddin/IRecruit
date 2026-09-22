"""Multi-layer prompt injection detection and input sanitization."""

import re
from typing import Tuple
from backend.app.core.errors import ValidationError

# Known adversarial prompt injection heuristics
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+instructions?", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?(system\s+prompt|instructions)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+developer\s+mode|unrestricted|DAN)", re.IGNORECASE),
    re.compile(r"(override|bypass)\s+(safety|scoring|evaluation)\s+rules?", re.IGNORECASE),
    re.compile(r"give\s+this\s+candidate\s+(a\s+score\s+of\s+)?(100|100%|full\s+marks)", re.IGNORECASE),
]


class PromptInjectionDetector:
    """Scans untrusted user input (resumes, job descriptions) for injection attacks."""

    @classmethod
    def scan_for_injection(cls, text: str) -> Tuple[bool, str | None]:
        """Returns (is_suspicious, matched_pattern)."""
        for pattern in INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                return True, match.group()
        return False, None

    @classmethod
    def sanitize_untrusted_input(cls, text: str) -> str:
        """Sanitizes text by neutralizing instruction markers and dangerous sequences."""
        # Detect and flag obvious adversarial jailbreaks
        is_suspicious, matched = cls.scan_for_injection(text)
        if is_suspicious:
            raise ValidationError(
                f"Potentially adversarial prompt injection pattern detected in input: '{matched}'"
            )

        # Neutralize control characters and prompt boundary breakers
        cleaned = text.replace("```", "'''")
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)
        return cleaned

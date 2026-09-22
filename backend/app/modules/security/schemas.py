"""Security schemas for prompt injection scanning, threat levels, and output guardrails."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class InjectionThreatLevel(str, Enum):
    """Severity classification of detected prompt injection patterns."""
    NONE = "NONE"
    LOW = "LOW"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class InjectionScanResult(BaseModel):
    """Result of scanning untrusted text for adversarial prompt injection."""
    is_suspicious: bool = Field(default=False, description="True if any adversarial heuristic was detected")
    threat_level: InjectionThreatLevel = Field(default=InjectionThreatLevel.NONE)
    matched_patterns: List[str] = Field(default_factory=list, description="Descriptions of matched adversarial heuristics")
    sanitized_text: str = Field(..., description="Cleaned, normalized, and instruction-separated text")
    has_zero_width_chars: bool = Field(default=False)
    has_delimiter_breakout: bool = Field(default=False)

    def __iter__(self):
        """Allows unpacking as (is_suspicious, first_pattern) for backwards compatibility."""
        first_pattern = self.matched_patterns[0] if self.matched_patterns else None
        return iter((self.is_suspicious, first_pattern))


class OutputValidationResult(BaseModel):
    """Validation report on LLM output to detect secret leakage and policy violations."""
    is_valid: bool = Field(default=True, description="True if LLM output passes all safety and privacy filters")
    sanitized_content: str = Field(..., description="Guarded and redacted LLM output")
    violations: List[str] = Field(default_factory=list, description="List of detected policy violations or secret leaks")
    leak_detected: bool = Field(default=False, description="True if secret or credential leakage was intercepted")

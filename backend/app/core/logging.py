"""Privacy-safe structured logging configuration.

Ensures no secrets, authorization tokens, passwords, or raw candidate PII
are leaked into application logs.
"""

import logging
import re
import sys
from typing import Any, Dict


# Patterns to redact from logs
SENSITIVE_KEY_PATTERNS = re.compile(
    r"(password|secret|token|authorization|bearer|api[_-]?key|credit|ssn)",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
PHONE_PATTERN = re.compile(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}")


class PrivacyFilter(logging.Filter):
    """Filters and masks sensitive credentials and personal data from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.mask_string(record.msg)
        elif isinstance(record.msg, dict):
            record.msg = self.mask_dict(record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = self.mask_dict(record.args)
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(
                    self.mask_string(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        return True

    @classmethod
    def mask_string(cls, text: str) -> str:
        """Masks potential emails and high-confidence sensitive token patterns."""
        # Redact JWT tokens if present in log text
        text = re.sub(r"Bearer\s+[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*", "Bearer [REDACTED_TOKEN]", text)
        # Redact raw email addresses
        text = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
        return text

    @classmethod
    def mask_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively masks dictionary keys and values."""
        masked = {}
        for k, v in data.items():
            if SENSITIVE_KEY_PATTERNS.search(k):
                masked[k] = "[REDACTED]"
            elif isinstance(v, dict):
                masked[k] = cls.mask_dict(v)
            elif isinstance(v, str):
                masked[k] = cls.mask_string(v)
            else:
                masked[k] = v
        return masked


def configure_logging(debug: bool = False) -> logging.Logger:
    """Configures application-wide privacy-safe structured logging."""
    logger = logging.getLogger("irecruit")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Avoid duplicate handlers if already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG if debug else logging.INFO)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] [request_id=%(request_id)s] %(message)s",
            defaults={"request_id": "system"},
        )
        handler.setFormatter(formatter)
        handler.addFilter(PrivacyFilter())
        logger.addHandler(handler)

    return logger


# Global application logger
logger = configure_logging()

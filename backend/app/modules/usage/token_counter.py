"""Token estimation and context window budgeting utilities."""

from __future__ import annotations

import math
import re


def estimate_tokens(text: str) -> int:
    """Estimate token count for raw text without network latency.

    Uses conservative multi-factor heuristic:
    - ~4 chars per token on average for English
    - accounts for whitespace, code symbols, and punctuation
    """
    if not text:
        return 0

    clean_text = text.strip()
    if not clean_text:
        return 0

    # Character based count
    char_count = len(clean_text)

    # Word based count
    words = re.findall(r"\w+|[^\w\s]", clean_text)
    word_count = len(words)

    # Blend word count (1.3 tokens/word) and char count (chars / 3.8)
    estimate = max(
        math.ceil(char_count / 3.8),
        math.ceil(word_count * 1.25),
    )
    return max(1, estimate)


def truncate_to_token_limit(text: str, max_tokens: int) -> str:
    """Safely truncate text so it does not exceed the designated token budget."""
    if not text or max_tokens <= 0:
        return ""

    current_estimate = estimate_tokens(text)
    if current_estimate <= max_tokens:
        return text

    # Approximate max characters allowed (~3.5 chars per token conservatively)
    max_chars = int(max_tokens * 3.5)
    truncated = text[:max_chars]

    # Don't break in the middle of a word or sentence if possible
    last_newline = truncated.rfind("\n")
    if last_newline > int(max_chars * 0.8):
        truncated = truncated[:last_newline]
    else:
        last_space = truncated.rfind(" ")
        if last_space > int(max_chars * 0.8):
            truncated = truncated[:last_space]

    return truncated + "\n...[Content truncated to respect token quota]"

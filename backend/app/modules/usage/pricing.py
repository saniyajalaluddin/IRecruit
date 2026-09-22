"""Pricing tables and cost estimation for LLM and embedding providers."""

from __future__ import annotations

from typing import Dict, Tuple

# Pricing in USD per 1,000,000 tokens: (input_price_per_1m, output_price_per_1m)
MODEL_PRICING: Dict[str, Tuple[float, float]] = {
    # OpenAI
    "gpt-4o": (5.00, 15.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "text-embedding-3-small": (0.02, 0.00),
    "text-embedding-3-large": (0.13, 0.00),
    # Google Gemini
    "gemini-1.5-pro": (3.50, 10.50),
    "gemini-1.5-flash": (0.075, 0.30),
    "text-embedding-004": (0.025, 0.00),
    # Anthropic
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-haiku": (0.25, 1.25),
    # Local & Mock (Free)
    "ollama": (0.00, 0.00),
    "llama3": (0.00, 0.00),
    "mistral": (0.00, 0.00),
    "mock": (0.00, 0.00),
    "mock-llm": (0.00, 0.00),
}


def calculate_cost(
    model_name: str,
    input_tokens: int,
    output_tokens: int = 0,
) -> float:
    """Calculate the estimated USD cost of an LLM or embedding invocation."""
    clean_model = model_name.lower().strip()
    
    # Direct match or prefix matching
    pricing = MODEL_PRICING.get(clean_model)
    if not pricing:
        for prefix, p in MODEL_PRICING.items():
            if clean_model.startswith(prefix):
                pricing = p
                break

    if not pricing:
        # Default fallback to mini rate to avoid underestimating
        pricing = (0.15, 0.60)

    input_price_per_token = pricing[0] / 1_000_000.0
    output_price_per_token = pricing[1] / 1_000_000.0

    total_cost = (input_tokens * input_price_per_token) + (output_tokens * output_price_per_token)
    return round(total_cost, 6)

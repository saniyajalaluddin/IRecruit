"""Deterministic Mock LLM and Embedding providers for offline execution, CI/CD, and testing."""

import hashlib
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from backend.app.modules.ai_providers.base import BaseEmbeddingProvider, BaseLLMProvider, LLMResponse


class MockLLMProvider(BaseLLMProvider):
    """Deterministic mock provider that requires zero external network calls or API keys."""

    def __init__(self, model_name: str = "mock-llm-v1"):
        self._model_name = model_name

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        start = time.perf_counter()
        simulated_text = f"Mock analysis completed for input text of length {len(prompt)}."
        latency_ms = (time.perf_counter() - start) * 1000

        return LLMResponse(
            content=simulated_text,
            structured_data=None,
            provider="mock",
            model=self._model_name,
            input_tokens=len(prompt.split()),
            output_tokens=len(simulated_text.split()),
            latency_ms=latency_ms,
        )

    async def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        start = time.perf_counter()
        # Instantiate empty default or model dump for the requested schema
        try:
            default_instance = schema()
            data = default_instance.model_dump()
        except Exception:
            data = {}

        latency_ms = (time.perf_counter() - start) * 1000
        return LLMResponse(
            content="{}",
            structured_data=data,
            provider="mock",
            model=self._model_name,
            input_tokens=len(prompt.split()),
            output_tokens=10,
            latency_ms=latency_ms,
        )


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic embedding provider generating reproducible pseudo-vectors via hashing."""

    def __init__(self, model_name: str = "mock-embedding-v1", dimension: int = 64):
        self._model_name = model_name
        self._dimension = dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            # Deterministic hash-based pseudo-vector normalized to unit sphere
            vec = []
            for i in range(self._dimension):
                h = hashlib.sha256(f"{text}_{i}".encode("utf-8")).hexdigest()
                val = (int(h[:8], 16) / 0xFFFFFFFF) * 2.0 - 1.0
                vec.append(val)
            norm = sum(x**2 for x in vec) ** 0.5 or 1.0
            unit_vec = [x / norm for x in vec]
            embeddings.append(unit_vec)
        return embeddings

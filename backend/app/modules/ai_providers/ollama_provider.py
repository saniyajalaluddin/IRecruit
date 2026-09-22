"""Ollama local AI provider for private, offline LLM inference and embeddings."""

import json
import time
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, ValidationError as PydanticValidationError
from backend.app.core.config import get_settings
from backend.app.core.errors import AIProviderError
from backend.app.modules.ai_providers.base import (
    BaseEmbeddingProvider,
    BaseLLMProvider,
    LLMResponse,
)


class OllamaProvider(BaseLLMProvider):
    """Provider for locally hosted Ollama instances."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        settings = get_settings()
        self._model_name = model_name or "llama3.2"
        self._base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self._client = client

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Generates text from Ollama chat API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        start = time.perf_counter()
        try:
            if self._client:
                resp = await self._client.post(
                    f"{self._base_url}/api/chat",
                    json=payload,
                    timeout=60.0,
                )
            else:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        f"{self._base_url}/api/chat",
                        json=payload,
                    )

            if resp.status_code >= 400:
                raise AIProviderError(f"Ollama API error ({resp.status_code}): {resp.text[:200]}")

            data = resp.json()
            latency_ms = (time.perf_counter() - start) * 1000
            content = data.get("message", {}).get("content", "")

            return LLMResponse(
                content=content,
                structured_data=None,
                provider="ollama",
                model=self._model_name,
                input_tokens=data.get("prompt_eval_count", len(prompt.split())),
                output_tokens=data.get("eval_count", len(content.split())),
                latency_ms=latency_ms,
            )
        except httpx.RequestError as exc:
            raise AIProviderError(
                f"Unable to connect to Ollama server at {self._base_url}. Ensure Ollama is running: {str(exc)}"
            ) from exc

    async def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Generates structured output conforming to a Pydantic schema using Ollama JSON format."""
        schema_json = json.dumps(schema.model_json_schema())
        instruction = (
            f"\nYou must respond ONLY with valid JSON matching this schema:\n{schema_json}"
        )
        effective_system = (system_prompt or "You are an expert AI parser.") + instruction

        messages = [
            {"role": "system", "content": effective_system},
            {"role": "user", "content": prompt},
        ]

        payload = {
            "model": self._model_name,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature},
        }

        start = time.perf_counter()
        try:
            if self._client:
                resp = await self._client.post(
                    f"{self._base_url}/api/chat",
                    json=payload,
                    timeout=60.0,
                )
            else:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        f"{self._base_url}/api/chat",
                        json=payload,
                    )

            if resp.status_code >= 400:
                raise AIProviderError(f"Ollama API error ({resp.status_code}): {resp.text[:200]}")

            data = resp.json()
            latency_ms = (time.perf_counter() - start) * 1000
            content = data.get("message", {}).get("content", "{}")

            try:
                parsed_json = json.loads(content)
                validated = schema.model_validate(parsed_json)
                structured_data = validated.model_dump()
            except (json.JSONDecodeError, PydanticValidationError) as val_err:
                raise AIProviderError(f"Failed to validate Ollama structured JSON: {str(val_err)}") from val_err

            return LLMResponse(
                content=content,
                structured_data=structured_data,
                provider="ollama",
                model=self._model_name,
                input_tokens=data.get("prompt_eval_count", len(prompt.split())),
                output_tokens=data.get("eval_count", len(content.split())),
                latency_ms=latency_ms,
            )
        except httpx.RequestError as exc:
            raise AIProviderError(
                f"Unable to connect to Ollama server at {self._base_url}. Ensure Ollama is running: {str(exc)}"
            ) from exc


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Provider for generating embeddings via local Ollama instance."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        dimension: int = 768,
        client: Optional[httpx.AsyncClient] = None,
    ):
        settings = get_settings()
        self._model_name = model_name or "nomic-embed-text"
        self._base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self._dimension = dimension
        self._client = client

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for texts using Ollama embed endpoint."""
        if not texts:
            return []

        try:
            # First attempt batch /api/embed endpoint
            payload = {"model": self._model_name, "input": texts}
            if self._client:
                resp = await self._client.post(f"{self._base_url}/api/embed", json=payload, timeout=60.0)
            else:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(f"{self._base_url}/api/embed", json=payload)

            if resp.status_code == 200:
                data = resp.json()
                return data.get("embeddings", [])

            # Fallback to single text /api/embeddings endpoint
            embeddings = []
            for t in texts:
                single_payload = {"model": self._model_name, "prompt": t}
                if self._client:
                    s_resp = await self._client.post(f"{self._base_url}/api/embeddings", json=single_payload, timeout=30.0)
                else:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        s_resp = await client.post(f"{self._base_url}/api/embeddings", json=single_payload)

                if s_resp.status_code >= 400:
                    raise AIProviderError(f"Ollama embedding error: {s_resp.text[:200]}")
                embeddings.append(s_resp.json().get("embedding", []))

            return embeddings
        except httpx.RequestError as exc:
            raise AIProviderError(f"Failed connecting to Ollama embeddings at {self._base_url}: {str(exc)}") from exc

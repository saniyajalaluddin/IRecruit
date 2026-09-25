"""OpenAI provider implementation for LLM completions and vector embeddings."""

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


class OpenAIProvider(BaseLLMProvider):
    """Provider for OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        settings = get_settings()
        self._model_name = model_name or "gpt-4o-mini"
        self._api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self._base_url = (base_url or settings.OPENAI_BASE_URL).rstrip("/")
        self._client = client

    def _get_headers(self) -> Dict[str, str]:
        if not self._api_key or not self._api_key.strip():
            raise AIProviderError("OpenAI API key is not configured. Set OPENAI_API_KEY in environment.")
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Generates text completion from prompt."""
        headers = self._get_headers()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        start = time.perf_counter()
        try:
            if self._client:
                resp = await self._client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0,
                )
            else:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{self._base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )

            if resp.status_code >= 400:
                raise AIProviderError(f"OpenAI API error ({resp.status_code}): {resp.text[:200]}")

            data = resp.json()
            latency_ms = (time.perf_counter() - start) * 1000
            content = data["choices"][0]["message"]["content"] or ""
            usage = data.get("usage", {})

            return LLMResponse(
                content=content,
                structured_data=None,
                provider="openai",
                model=self._model_name,
                input_tokens=usage.get("prompt_tokens", len(prompt.split())),
                output_tokens=usage.get("completion_tokens", len(content.split())),
                latency_ms=latency_ms,
            )
        except httpx.RequestError as exc:
            raise AIProviderError(f"Network error connecting to OpenAI: {str(exc)}") from exc

    async def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Generates structured output conforming to a Pydantic schema using JSON mode."""
        headers = self._get_headers()
        schema_instruction = (
            f"\nYou must output strictly valid JSON conforming to this schema:\n{json.dumps(schema.model_json_schema())}"
        )
        effective_system = (system_prompt or "You are an expert AI parser.") + schema_instruction

        messages = [
            {"role": "system", "content": effective_system},
            {"role": "user", "content": prompt},
        ]

        payload = {
            "model": self._model_name,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        start = time.perf_counter()
        try:
            if self._client:
                resp = await self._client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0,
                )
            else:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{self._base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )

            if resp.status_code >= 400:
                raise AIProviderError(f"OpenAI API error ({resp.status_code}): {resp.text[:200]}")

            data = resp.json()
            latency_ms = (time.perf_counter() - start) * 1000
            content = data["choices"][0]["message"]["content"] or "{}"
            usage = data.get("usage", {})

            try:
                parsed_json = json.loads(content)
                validated = schema.model_validate(parsed_json)
                structured_data = validated.model_dump()
            except (json.JSONDecodeError, PydanticValidationError) as val_err:
                raise AIProviderError(f"Failed to validate structured JSON against schema: {str(val_err)}") from val_err

            return LLMResponse(
                content=content,
                structured_data=structured_data,
                provider="openai",
                model=self._model_name,
                input_tokens=usage.get("prompt_tokens", len(prompt.split())),
                output_tokens=usage.get("completion_tokens", len(content.split())),
                latency_ms=latency_ms,
            )
        except httpx.RequestError as exc:
            raise AIProviderError(f"Network error connecting to OpenAI: {str(exc)}") from exc


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """Provider for OpenAI embedding vectors."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        dimension: int = 1536,
        client: Optional[httpx.AsyncClient] = None,
    ):
        settings = get_settings()
        self._model_name = model_name or "text-embedding-3-small"
        self._api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self._base_url = (base_url or settings.OPENAI_BASE_URL).rstrip("/")
        self._dimension = dimension
        self._client = client

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def _get_headers(self) -> Dict[str, str]:
        if not self._api_key or not self._api_key.strip():
            raise AIProviderError("OpenAI API key is not configured. Set OPENAI_API_KEY in environment.")
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for a list of strings."""
        if not texts:
            return []

        headers = self._get_headers()
        payload = {
            "model": self._model_name,
            "input": texts,
        }

        try:
            if self._client:
                resp = await self._client.post(
                    f"{self._base_url}/embeddings",
                    headers=headers,
                    json=payload,
                    timeout=30.0,
                )
            else:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{self._base_url}/embeddings",
                        headers=headers,
                        json=payload,
                    )

            if resp.status_code >= 400:
                raise AIProviderError(f"OpenAI embedding error ({resp.status_code}): {resp.text[:200]}")

            data = resp.json()
            raw_embeddings = [item["embedding"] for item in data.get("data", [])]
            return raw_embeddings
        except httpx.RequestError as exc:
            raise AIProviderError(f"Network error connecting to OpenAI embeddings: {str(exc)}") from exc

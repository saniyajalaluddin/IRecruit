"""Factory for dynamically instantiating LLM and Embedding providers."""

from typing import Dict, Optional, Type
from backend.app.core.config import get_settings
from backend.app.core.errors import AIProviderError
from backend.app.modules.ai_providers.base import BaseEmbeddingProvider, BaseLLMProvider
from backend.app.modules.ai_providers.mock_provider import MockEmbeddingProvider, MockLLMProvider
from backend.app.modules.ai_providers.ollama_provider import OllamaEmbeddingProvider, OllamaProvider
from backend.app.modules.ai_providers.openai_provider import OpenAIEmbeddingProvider, OpenAIProvider

# Provider registry for runtime extensibility
_LLM_PROVIDERS: Dict[str, Type[BaseLLMProvider]] = {
    "mock": MockLLMProvider,
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
}

_EMBEDDING_PROVIDERS: Dict[str, Type[BaseEmbeddingProvider]] = {
    "mock": MockEmbeddingProvider,
    "openai": OpenAIEmbeddingProvider,
    "ollama": OllamaEmbeddingProvider,
}


def register_llm_provider(name: str, provider_cls: Type[BaseLLMProvider]) -> None:
    """Registers a new LLM provider implementation."""
    _LLM_PROVIDERS[name.lower()] = provider_cls


def register_embedding_provider(name: str, provider_cls: Type[BaseEmbeddingProvider]) -> None:
    """Registers a new Embedding provider implementation."""
    _EMBEDDING_PROVIDERS[name.lower()] = provider_cls


def get_llm_provider(provider_name: Optional[str] = None, **kwargs) -> BaseLLMProvider:
    """Instantiates configured or requested LLM provider."""
    settings = get_settings()
    name = (provider_name or settings.DEFAULT_LLM_PROVIDER).lower()

    provider_cls = _LLM_PROVIDERS.get(name)
    if not provider_cls:
        raise AIProviderError(f"Requested LLM provider '{name}' is not registered.")

    return provider_cls(**kwargs)


def get_embedding_provider(provider_name: Optional[str] = None, **kwargs) -> BaseEmbeddingProvider:
    """Instantiates configured or requested Embedding provider."""
    settings = get_settings()
    name = (provider_name or settings.DEFAULT_EMBEDDING_PROVIDER).lower()

    provider_cls = _EMBEDDING_PROVIDERS.get(name)
    if not provider_cls:
        raise AIProviderError(f"Requested Embedding provider '{name}' is not registered.")

    return provider_cls(**kwargs)

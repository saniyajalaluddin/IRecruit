"""Tests for provider-agnostic AI architecture: Mock, OpenAI, Ollama, and Factory registry."""

import json
import httpx
import pytest
from pydantic import BaseModel, Field
from backend.app.core.errors import AIProviderError
from backend.app.modules.ai_providers.base import BaseLLMProvider, LLMResponse
from backend.app.modules.ai_providers.factory import (
    get_embedding_provider,
    get_llm_provider,
    register_embedding_provider,
    register_llm_provider,
)
from backend.app.modules.ai_providers.mock_provider import MockEmbeddingProvider, MockLLMProvider
from backend.app.modules.ai_providers.ollama_provider import (
    OllamaEmbeddingProvider,
    OllamaProvider,
)
from backend.app.modules.ai_providers.openai_provider import (
    OpenAIEmbeddingProvider,
    OpenAIProvider,
)


class SampleStructuredOutput(BaseModel):
    """Test schema for structured LLM generation."""
    skill_name: str = Field(default="Python")
    confidence: float = Field(default=0.95)
    tags: list[str] = Field(default_factory=lambda: ["backend", "api"])


# --------------------------------------------------------------------------
# 1. Factory & Provider Registry Tests
# --------------------------------------------------------------------------

def test_factory_defaults_and_switching():
    """Verify factory instantiates mock, openai, and ollama providers."""
    mock_llm = get_llm_provider("mock")
    assert isinstance(mock_llm, MockLLMProvider)

    openai_llm = get_llm_provider("openai", api_key="sk-test-fake-key")
    assert isinstance(openai_llm, OpenAIProvider)

    ollama_llm = get_llm_provider("ollama")
    assert isinstance(ollama_llm, OllamaProvider)

    mock_emb = get_embedding_provider("mock")
    assert isinstance(mock_emb, MockEmbeddingProvider)

    openai_emb = get_embedding_provider("openai", api_key="sk-test-fake-key")
    assert isinstance(openai_emb, OpenAIEmbeddingProvider)

    ollama_emb = get_embedding_provider("ollama")
    assert isinstance(ollama_emb, OllamaEmbeddingProvider)


def test_factory_invalid_provider_raises_error():
    """Verify unregistered provider name raises AIProviderError."""
    with pytest.raises(AIProviderError, match="not registered"):
        get_llm_provider("nonexistent-provider")

    with pytest.raises(AIProviderError, match="not registered"):
        get_embedding_provider("nonexistent-embedder")


def test_factory_custom_provider_registration():
    """Verify runtime registration of custom third-party providers."""
    class CustomLLM(BaseLLMProvider):
        async def generate_text(self, prompt, **kwargs):
            return LLMResponse(
                content="custom",
                provider="custom",
                model="custom-v1",
                input_tokens=1,
                output_tokens=1,
            )

        async def generate_structured(self, prompt, schema, **kwargs):
            return LLMResponse(
                content="{}",
                structured_data={},
                provider="custom",
                model="custom-v1",
            )

    register_llm_provider("custom", CustomLLM)
    custom_inst = get_llm_provider("custom")
    assert isinstance(custom_inst, CustomLLM)


# --------------------------------------------------------------------------
# 2. Mock Provider Tests
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_llm_generation():
    """Verify MockLLMProvider deterministic generation."""
    llm = MockLLMProvider(model_name="mock-test-model")
    resp = await llm.generate_text("Summarize candidate experience")
    assert resp.provider == "mock"
    assert resp.model == "mock-test-model"
    assert "Mock analysis completed" in resp.content
    assert resp.input_tokens > 0

    struct_resp = await llm.generate_structured("Extract skill", SampleStructuredOutput)
    assert struct_resp.structured_data is not None
    assert "skill_name" in struct_resp.structured_data


@pytest.mark.asyncio
async def test_mock_embedding_generation():
    """Verify MockEmbeddingProvider vector dimensional stability."""
    emb = MockEmbeddingProvider(dimension=32)
    vectors = await emb.get_embeddings(["python backend", "fastapi developer", ""])
    assert len(vectors) == 3
    assert len(vectors[0]) == 32
    assert len(vectors[1]) == 32
    assert len(vectors[2]) == 32


# --------------------------------------------------------------------------
# 3. OpenAI Provider Tests
# --------------------------------------------------------------------------

def test_openai_missing_api_key_raises_error():
    """Verify OpenAIProvider blocks calls if API key is not configured."""
    provider = OpenAIProvider(api_key="")
    with pytest.raises(AIProviderError, match="API key is not configured"):
        provider._get_headers()


@pytest.mark.asyncio
async def test_openai_generate_text_mocked_http():
    """Verify OpenAIProvider handles successful API response."""
    mock_json_response = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Analysis of candidate matches requirement."},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 15, "completion_tokens": 8, "total_tokens": 23},
    }

    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=mock_json_response)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenAIProvider(api_key="sk-test-key", client=client)
        resp = await provider.generate_text("Evaluate resume")

        assert resp.provider == "openai"
        assert resp.content == "Analysis of candidate matches requirement."
        assert resp.input_tokens == 15
        assert resp.output_tokens == 8
        assert resp.latency_ms >= 0


@pytest.mark.asyncio
async def test_openai_generate_structured_mocked_http():
    """Verify OpenAIProvider handles structured JSON response and schema validation."""
    valid_payload = {"skill_name": "FastAPI", "confidence": 0.98, "tags": ["python", "rest"]}
    mock_json_response = {
        "choices": [{"message": {"content": json.dumps(valid_payload)}}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 12},
    }

    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=mock_json_response)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenAIProvider(api_key="sk-test-key", client=client)
        resp = await provider.generate_structured("Extract skill", SampleStructuredOutput)

        assert resp.structured_data == valid_payload
        assert resp.structured_data["skill_name"] == "FastAPI"


@pytest.mark.asyncio
async def test_openai_api_error_handling():
    """Verify HTTP 401/429 errors from OpenAI are converted into AIProviderError."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(401, json={"error": {"message": "Incorrect API key provided"}})
    )
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenAIProvider(api_key="sk-bad-key", client=client)
        with pytest.raises(AIProviderError, match="OpenAI API error \\(401\\)"):
            await provider.generate_text("Hello")


@pytest.mark.asyncio
async def test_openai_embedding_provider_mocked_http():
    """Verify OpenAIEmbeddingProvider parsing vector payload."""
    mock_embeddings_resp = {
        "object": "list",
        "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2, 0.3, 0.4]}],
    }
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=mock_embeddings_resp)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenAIEmbeddingProvider(api_key="sk-test-key", client=client, dimension=4)
        vectors = await provider.get_embeddings(["python microservices"])

        assert len(vectors) == 1
        assert vectors[0] == [0.1, 0.2, 0.3, 0.4]


# --------------------------------------------------------------------------
# 4. Ollama Provider Tests
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ollama_generate_text_mocked_http():
    """Verify OllamaProvider handles chat completion API."""
    mock_ollama_response = {
        "model": "llama3.2",
        "message": {"role": "assistant", "content": "Local model analysis response."},
        "prompt_eval_count": 10,
        "eval_count": 6,
    }
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=mock_ollama_response)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OllamaProvider(base_url="http://localhost:11434", client=client)
        resp = await provider.generate_text("Analyze JD")

        assert resp.provider == "ollama"
        assert resp.content == "Local model analysis response."
        assert resp.input_tokens == 10
        assert resp.output_tokens == 6


@pytest.mark.asyncio
async def test_ollama_generate_structured_mocked_http():
    """Verify OllamaProvider structured JSON validation."""
    valid_payload = {"skill_name": "Docker", "confidence": 0.90, "tags": ["devops"]}
    mock_ollama_response = {
        "model": "llama3.2",
        "message": {"role": "assistant", "content": json.dumps(valid_payload)},
    }
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=mock_ollama_response)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OllamaProvider(base_url="http://localhost:11434", client=client)
        resp = await provider.generate_structured("Extract tags", SampleStructuredOutput)

        assert resp.structured_data == valid_payload
        assert resp.structured_data["skill_name"] == "Docker"


@pytest.mark.asyncio
async def test_ollama_embeddings_mocked_http():
    """Verify OllamaEmbeddingProvider batch and single embedding responses."""
    mock_embed_resp = {
        "embeddings": [[0.5, -0.5, 0.25], [0.1, 0.2, 0.3]]
    }
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=mock_embed_resp)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OllamaEmbeddingProvider(base_url="http://localhost:11434", client=client)
        vectors = await provider.get_embeddings(["text 1", "text 2"])

        assert len(vectors) == 2
        assert vectors[0] == [0.5, -0.5, 0.25]

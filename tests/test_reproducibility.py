"""Tests for model tracking, reproducibility metadata, and configuration explainability."""

import pytest
from backend.app.modules.analysis.reproducibility import (
    ReproducibilityMetadata,
    ReproducibilityService,
)


def test_compute_configuration_hash_deterministic():
    """Verify configuration hash is strictly deterministic for identical inputs."""
    hash1 = ReproducibilityService.compute_configuration_hash(
        llm_provider="mock",
        llm_model="mock-llm-v1",
        embedding_provider="tfidf",
        embedding_model="tfidf-base",
        embedding_version="v1.0.0",
        prompt_version="v1.0.0",
        scoring_version="v1.0.0",
    )
    hash2 = ReproducibilityService.compute_configuration_hash(
        llm_provider="mock",
        llm_model="mock-llm-v1",
        embedding_provider="tfidf",
        embedding_model="tfidf-base",
        embedding_version="v1.0.0",
        prompt_version="v1.0.0",
        scoring_version="v1.0.0",
    )
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex length


def test_compute_configuration_hash_divergence():
    """Verify configuration hash changes when any model, provider, or version changes."""
    base_hash = ReproducibilityService.compute_configuration_hash(
        llm_provider="mock",
        llm_model="mock-llm-v1",
        embedding_provider="tfidf",
        embedding_model="tfidf-base",
        embedding_version="v1.0.0",
        prompt_version="v1.0.0",
        scoring_version="v1.0.0",
    )
    # Different scoring version
    diff_scoring_hash = ReproducibilityService.compute_configuration_hash(
        llm_provider="mock",
        llm_model="mock-llm-v1",
        embedding_provider="tfidf",
        embedding_model="tfidf-base",
        embedding_version="v1.0.0",
        prompt_version="v1.0.0",
        scoring_version="v1.1.0",
    )
    assert base_hash != diff_scoring_hash

    # Different LLM model
    diff_llm_hash = ReproducibilityService.compute_configuration_hash(
        llm_provider="openai",
        llm_model="gpt-4o",
        embedding_provider="tfidf",
        embedding_model="tfidf-base",
        embedding_version="v1.0.0",
        prompt_version="v1.0.0",
        scoring_version="v1.0.0",
    )
    assert base_hash != diff_llm_hash


def test_generate_explanation_content():
    """Verify human-readable explanation describes models, versions, and non-fabrication."""
    explanation = ReproducibilityService.generate_explanation(
        llm_provider="mock",
        llm_model="mock-reasoning-v1",
        embedding_provider="tfidf",
        embedding_model="tfidf-fast",
        prompt_version="v1.0.0",
        scoring_version="v1.0.0",
    )
    assert "MOCK" in explanation
    assert "mock-reasoning-v1" in explanation
    assert "TFIDF" in explanation
    assert "v1.0.0" in explanation
    assert "grounded strictly in candidate-provided evidence" in explanation
    assert "zero hallucinated skills" in explanation


@pytest.mark.asyncio
async def test_reproducibility_api_endpoint(async_client):
    """Verify GET /api/v1/analyses/{analysis_id}/reproducibility returns full metadata."""
    # Register test user
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "repro_user@example.com", "password": "SecurePassword123!", "full_name": "Repro User"},
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["data"]["token"]["access_token"]

    # 1. Create an anonymous analysis
    anon_payload = {
        "resume_text": "Experienced Python Engineer with 5 years in FastAPI, Docker, and PostgreSQL.",
        "job_description_text": "Required: Python, FastAPI, Docker, and PostgreSQL database modeling.",
        "client_ip": "127.0.0.1",
        "user_agent": "TestRunner/1.0",
    }
    anon_res = await async_client.post("/api/v1/analyses/anonymous", json=anon_payload)
    assert anon_res.status_code == 200
    anon_data = anon_res.json()["data"]
    analysis_id = anon_data["analysis_id"]
    session_id = anon_data["session_id"]

    # 2. Claim analysis to user account
    claim_res = await async_client.post(
        f"/api/v1/analyses/{analysis_id}/claim",
        headers={"Authorization": f"Bearer {token}"},
        json={"session_id": session_id},
    )
    assert claim_res.status_code == 200

    # 3. Fetch reproducibility metadata
    repro_res = await async_client.get(
        f"/api/v1/analyses/{analysis_id}/reproducibility",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert repro_res.status_code == 200
    repro_data = repro_res.json()
    assert repro_data["success"] is True
    meta = repro_data["data"]

    assert meta["analysis_id"] == analysis_id
    assert "llm_provider" in meta
    assert "llm_model" in meta
    assert "embedding_provider" in meta
    assert "embedding_model" in meta
    assert "embedding_version" in meta
    assert "prompt_version" in meta
    assert "scoring_version" in meta
    assert "configuration_hash" in meta
    assert len(meta["configuration_hash"]) == 64
    assert "explanation" in meta

    # Privacy verification: no raw resume text or candidate names in reproducibility metadata
    assert "Experienced Python Engineer" not in str(meta)
    assert "repro_user" not in str(meta)


@pytest.mark.asyncio
async def test_reproducibility_unauthorized_access(async_client):
    """Verify unauthorized candidate cannot inspect another candidate's analysis metadata."""
    # Register user 1
    reg1 = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "owner_user@example.com", "password": "SecurePassword123!"},
    )
    assert reg1.status_code == 201
    token1 = reg1.json()["data"]["token"]["access_token"]

    # Register user 2
    reg2 = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "other_user@example.com", "password": "SecurePassword123!"},
    )
    assert reg2.status_code == 201
    token2 = reg2.json()["data"]["token"]["access_token"]

    # Create analysis under user 1
    anon_payload = {
        "resume_text": "Senior Rust and Go Systems Developer with Kubernetes.",
        "job_description_text": "Required: Rust, Go, Kubernetes distributed systems.",
        "client_ip": "127.0.0.1",
    }
    anon_res = await async_client.post("/api/v1/analyses/anonymous", json=anon_payload)
    anon_data = anon_res.json()["data"]
    analysis_id = anon_data["analysis_id"]
    session_id = anon_data["session_id"]

    await async_client.post(
        f"/api/v1/analyses/{analysis_id}/claim",
        headers={"Authorization": f"Bearer {token1}"},
        json={"session_id": session_id},
    )

    # Request unauthenticated -> 401
    unauth_res = await async_client.get(f"/api/v1/analyses/{analysis_id}/reproducibility")
    assert unauth_res.status_code == 401

    # Request with user 2 token -> 403 or 404 forbidden ownership
    forbidden_res = await async_client.get(
        f"/api/v1/analyses/{analysis_id}/reproducibility",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert forbidden_res.status_code in (403, 404)

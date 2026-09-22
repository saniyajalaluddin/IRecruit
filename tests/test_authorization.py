"""Tests for strict resource ownership and ID manipulation defenses."""

import pytest
from backend.app.models.analysis import Analysis
from backend.app.models.job_description import JobDescription
from backend.app.models.resume import Resume, ResumeVersion


@pytest.mark.asyncio
async def test_cross_user_resource_access_and_id_manipulation(async_client, test_db_session):
    """Verify that User A cannot access, view, or delete User B's resources."""
    # 1. Register User A
    user_a_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "user.a@example.com", "password": "Password123!", "full_name": "User A"},
    )
    assert user_a_res.status_code == 201
    token_a = user_a_res.json()["data"]["token"]["access_token"]
    user_a_id = user_a_res.json()["data"]["user_id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register User B
    user_b_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "user.b@example.com", "password": "Password123!", "full_name": "User B"},
    )
    assert user_b_res.status_code == 201
    token_b = user_b_res.json()["data"]["token"]["access_token"]
    user_b_id = user_b_res.json()["data"]["user_id"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Create Resume, ResumeVersion, JobDescription, and Analysis owned by User B
    resume_b = Resume(
        user_id=user_b_id,
        title="User B Confidential Resume",
        original_filename="user_b.pdf",
        file_path="/storage/temp/user_b.pdf",
        file_size_bytes=2048,
        content_type="application/pdf",
    )
    test_db_session.add(resume_b)
    await test_db_session.flush()

    version_b = ResumeVersion(
        resume_id=resume_b.id,
        version_number=1,
        raw_text="User B text",
        pii_masked_text="[REDACTED]",
        structured_data={},
    )
    test_db_session.add(version_b)
    await test_db_session.flush()

    jd_b = JobDescription(
        user_id=user_b_id,
        title="User B Job",
        raw_text="Job Description for User B",
        structured_requirements={},
    )
    test_db_session.add(jd_b)
    await test_db_session.flush()

    analysis_b = Analysis(
        user_id=user_b_id,
        resume_id=resume_b.id,
        resume_version_id=version_b.id,
        job_description_id=jd_b.id,
        overall_score=88.0,
        component_scores={"technical": 90.0},
        weights={"technical": 1.0},
        scoring_version="v1.0.0",
        prompt_version="v1.0.0",
        llm_provider="mock",
        llm_model="mock-v1",
        embedding_provider="mock",
        embedding_model="mock-embed-v1",
        execution_duration_ms=50.0,
    )
    test_db_session.add(analysis_b)
    await test_db_session.commit()

    # --- ATTACK 1: User A attempts to view User B's Resume ---
    hacked_resume_res = await async_client.get(
        f"/api/v1/resumes/{resume_b.id}",
        headers=headers_a,
    )
    assert hacked_resume_res.status_code == 403
    body = hacked_resume_res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "FORBIDDEN_RESOURCE_ACCESS"

    # --- ATTACK 2: User A attempts to delete User B's Resume ---
    delete_resume_res = await async_client.delete(
        f"/api/v1/resumes/{resume_b.id}",
        headers=headers_a,
    )
    assert delete_resume_res.status_code == 403
    body = delete_resume_res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "FORBIDDEN_RESOURCE_ACCESS"

    # --- ATTACK 3: User A attempts to view User B's Analysis ---
    hacked_analysis_res = await async_client.get(
        f"/api/v1/analyses/{analysis_b.id}",
        headers=headers_a,
    )
    assert hacked_analysis_res.status_code == 403
    body = hacked_analysis_res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "FORBIDDEN_RESOURCE_ACCESS"

    # --- ATTACK 4: User A attempts to delete User B's Analysis ---
    delete_analysis_res = await async_client.delete(
        f"/api/v1/analyses/{analysis_b.id}",
        headers=headers_a,
    )
    assert delete_analysis_res.status_code == 403
    body = delete_analysis_res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "FORBIDDEN_RESOURCE_ACCESS"

    # --- LEGITIMATE ACCESS: User B can view their own Resume and Analysis ---
    legit_resume = await async_client.get(f"/api/v1/resumes/{resume_b.id}", headers=headers_b)
    assert legit_resume.status_code == 200
    assert legit_resume.json()["data"]["title"] == "User B Confidential Resume"

    legit_analysis = await async_client.get(f"/api/v1/analyses/{analysis_b.id}", headers=headers_b)
    assert legit_analysis.status_code == 200
    assert legit_analysis.json()["data"]["overall_score"] == 88.0

    # --- Non-Existent Resource ID ---
    not_found_res = await async_client.get("/api/v1/resumes/non-existent-uuid", headers=headers_a)
    assert not_found_res.status_code == 404

    # --- Unauthenticated Request ---
    unauth_res = await async_client.get(f"/api/v1/resumes/{resume_b.id}")
    assert unauth_res.status_code == 401

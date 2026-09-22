"""Integration tests for user registration, authentication, sessions, and security."""

import pytest


@pytest.mark.asyncio
async def test_valid_registration(async_client):
    """Verify user can register with email and password and receive token bundle."""
    payload = {
        "email": "new.candidate@example.com",
        "password": "StrongPassword123!",
        "full_name": "New Candidate",
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["email"] == "new.candidate@example.com"
    assert "token" in body["data"]
    assert "access_token" in body["data"]["token"]
    assert "hashed_password" not in body["data"]


@pytest.mark.asyncio
async def test_duplicate_registration_conflict(async_client):
    """Verify registering an already existing email returns HTTP 409 Conflict."""
    payload = {
        "email": "duplicate@example.com",
        "password": "StrongPassword123!",
        "full_name": "Duplicate User",
    }
    res1 = await async_client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await async_client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    body = res2.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RESOURCE_CONFLICT"


@pytest.mark.asyncio
async def test_valid_login(async_client):
    """Verify user can log in with valid credentials and receive token."""
    reg_payload = {
        "email": "login.test@example.com",
        "password": "MySecretPassword123!",
        "full_name": "Login Tester",
    }
    await async_client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "login.test@example.com",
        "password": "MySecretPassword123!",
    }
    response = await async_client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["email"] == "login.test@example.com"
    assert body["data"]["token"]["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_invalid_login_wrong_password(async_client):
    """Verify login with incorrect password returns 401 Unauthorized."""
    reg_payload = {
        "email": "wrongpw@example.com",
        "password": "CorrectPassword123!",
    }
    await async_client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "wrongpw@example.com",
        "password": "WrongPassword999!",
    }
    response = await async_client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_invalid_login_nonexistent_user(async_client):
    """Verify login with non-existent user returns 401 Unauthorized with generic message."""
    login_payload = {
        "email": "nobody@example.com",
        "password": "AnyPassword123!",
    }
    response = await async_client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert "Invalid email address or password" in body["error"]["message"]


@pytest.mark.asyncio
async def test_unauthorized_request_without_token(async_client):
    """Verify accessing protected /api/v1/auth/me without authorization header returns 401."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_unauthorized_request_with_invalid_token(async_client):
    """Verify accessing protected endpoint with forged token returns 401."""
    headers = {"Authorization": "Bearer forged.invalid.token"}
    response = await async_client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False


@pytest.mark.asyncio
async def test_session_behavior_and_profile_retrieval(async_client):
    """Verify session flow: register, access /me with token, and perform logout."""
    reg_payload = {
        "email": "session.user@example.com",
        "password": "SecurePassword456!",
        "full_name": "Session User",
    }
    reg_res = await async_client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["data"]["token"]["access_token"]

    # Access profile with token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await async_client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_body = me_res.json()
    assert me_body["success"] is True
    assert me_body["data"]["email"] == "session.user@example.com"
    assert me_body["data"]["full_name"] == "Session User"
    assert "hashed_password" not in me_body["data"]

    # Perform logout
    logout_res = await async_client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    logout_body = logout_res.json()
    assert logout_body["success"] is True

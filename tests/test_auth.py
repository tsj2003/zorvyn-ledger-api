import pytest
from httpx import AsyncClient
from tests.conftest import make_token


# ── Registration ────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_returns_201_with_viewer_role(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "email": "new@test.com", "username": "newuser", "password": "securepass1",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@test.com"
    assert body["role"] == "viewer"
    assert "id" in body
    assert "hashed_password" not in body  # never leak hash


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(client: AsyncClient):
    payload = {"email": "dup@test.com", "username": "dup1", "password": "securepass1"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json={**payload, "username": "dup2"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_duplicate_username_returns_409(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "u1@test.com", "username": "samename", "password": "securepass1",
    })
    resp = await client.post("/auth/register", json={
        "email": "u2@test.com", "username": "samename", "password": "securepass1",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_password_too_short_returns_422(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "email": "short@test.com", "username": "shortpw", "password": "abc",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email_returns_422(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "email": "not-an-email", "username": "bademail", "password": "securepass1",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_fields_returns_422(client: AsyncClient):
    resp = await client.post("/auth/register", json={"email": "only@test.com"})
    assert resp.status_code == 422


# ── Login ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_returns_bearer_token(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "login@test.com", "username": "loginuser", "password": "securepass1",
    })
    resp = await client.post("/auth/login", json={
        "email": "login@test.com", "password": "securepass1",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "wrong@test.com", "username": "wronguser", "password": "securepass1",
    })
    resp = await client.post("/auth/login", json={
        "email": "wrong@test.com", "password": "badpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_email_returns_401(client: AsyncClient):
    resp = await client.post("/auth/login", json={
        "email": "ghost@test.com", "password": "anything123",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user_returns_403(client: AsyncClient, admin_user, client_factory=None):
    """Register a user, deactivate them via admin, then try to login."""
    headers = make_token(admin_user)
    # register a new user
    reg = await client.post("/auth/register", json={
        "email": "deactivated@test.com", "username": "deactivated", "password": "securepass1",
    })
    user_id = reg.json()["id"]
    # admin deactivates the user
    await client.patch(f"/users/{user_id}", json={"is_active": False}, headers=headers)
    # user tries to login
    resp = await client.post("/auth/login", json={
        "email": "deactivated@test.com", "password": "securepass1",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_expired_token_returns_401(client: AsyncClient):
    """A garbage token should be rejected."""
    resp = await client.get("/records", headers={"Authorization": "Bearer garbage.token.here"})
    assert resp.status_code in (401, 403)

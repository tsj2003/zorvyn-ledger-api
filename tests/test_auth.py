import pytest
from httpx import AsyncClient
from tests.conftest import make_token


@pytest.mark.asyncio
async def test_register_returns_201(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "email": "new@test.com",
        "username": "newuser",
        "password": "securepass1",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@test.com"
    assert body["role"] == "viewer"


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(client: AsyncClient):
    payload = {"email": "dup@test.com", "username": "dup1", "password": "securepass1"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json={**payload, "username": "dup2"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_returns_token(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "login@test.com", "username": "loginuser", "password": "securepass1",
    })
    resp = await client.post("/auth/login", json={
        "email": "login@test.com", "password": "securepass1",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "wrong@test.com", "username": "wronguser", "password": "securepass1",
    })
    resp = await client.post("/auth/login", json={
        "email": "wrong@test.com", "password": "badpassword",
    })
    assert resp.status_code == 401

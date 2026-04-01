import uuid
import pytest
from httpx import AsyncClient
from app.models import User
from tests.conftest import make_token


@pytest.mark.asyncio
async def test_admin_can_list_users(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.get("/users", headers=headers)
    assert resp.status_code == 200
    users = resp.json()
    assert isinstance(users, list)
    assert len(users) >= 1


@pytest.mark.asyncio
async def test_admin_can_get_single_user(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.get(f"/users/{admin_user.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test_admin@test.com"


@pytest.mark.asyncio
async def test_get_nonexistent_user_returns_404(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.get(f"/users/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_can_update_user_role(client: AsyncClient, admin_user: User, viewer_user: User):
    headers = make_token(admin_user)
    resp = await client.patch(f"/users/{viewer_user.id}", json={
        "role": "analyst",
    }, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "analyst"


@pytest.mark.asyncio
async def test_admin_can_deactivate_user(client: AsyncClient, admin_user: User, viewer_user: User):
    headers = make_token(admin_user)
    resp = await client.patch(f"/users/{viewer_user.id}", json={
        "is_active": False,
    }, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_admin_can_reactivate_user(client: AsyncClient, admin_user: User, viewer_user: User):
    headers = make_token(admin_user)
    # deactivate
    await client.patch(f"/users/{viewer_user.id}", json={"is_active": False}, headers=headers)
    # reactivate
    resp = await client.patch(f"/users/{viewer_user.id}", json={"is_active": True}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


@pytest.mark.asyncio
async def test_list_users_filter_by_role(client: AsyncClient, admin_user: User, analyst_user: User, viewer_user: User):
    headers = make_token(admin_user)
    resp = await client.get("/users?role=analyst", headers=headers)
    assert resp.status_code == 200
    users = resp.json()
    assert all(u["role"] == "analyst" for u in users)


@pytest.mark.asyncio
async def test_list_users_excludes_inactive_by_default(client: AsyncClient, admin_user: User, viewer_user: User):
    headers = make_token(admin_user)
    # deactivate viewer
    await client.patch(f"/users/{viewer_user.id}", json={"is_active": False}, headers=headers)

    resp = await client.get("/users", headers=headers)
    user_ids = [u["id"] for u in resp.json()]
    assert str(viewer_user.id) not in user_ids


@pytest.mark.asyncio
async def test_list_users_includes_inactive_when_requested(client: AsyncClient, admin_user: User, viewer_user: User):
    headers = make_token(admin_user)
    await client.patch(f"/users/{viewer_user.id}", json={"is_active": False}, headers=headers)

    resp = await client.get("/users?include_inactive=true", headers=headers)
    user_ids = [u["id"] for u in resp.json()]
    assert str(viewer_user.id) in user_ids


@pytest.mark.asyncio
async def test_update_nonexistent_user_returns_404(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.patch(f"/users/{uuid.uuid4()}", json={"role": "admin"}, headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_response_never_leaks_password(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.get(f"/users/{admin_user.id}", headers=headers)
    body = resp.json()
    assert "hashed_password" not in body
    assert "password" not in body

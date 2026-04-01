import pytest
from httpx import AsyncClient
from app.models import User
from tests.conftest import make_token


@pytest.mark.asyncio
async def test_viewer_cannot_create_record(client: AsyncClient, viewer_user: User):
    headers = make_token(viewer_user)
    resp = await client.post("/records", json={
        "amount": "100.00",
        "record_type": "income",
        "category": "salary",
        "record_date": "2025-01-15",
    }, headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_delete_record(client: AsyncClient, viewer_user: User):
    headers = make_token(viewer_user)
    resp = await client.delete("/records/00000000-0000-0000-0000-000000000001", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_list_records(client: AsyncClient, viewer_user: User):
    headers = make_token(viewer_user)
    resp = await client.get("/records", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_analyst_cannot_create_record(client: AsyncClient, analyst_user: User):
    headers = make_token(analyst_user)
    resp = await client.post("/records", json={
        "amount": "100.00",
        "record_type": "income",
        "category": "salary",
        "record_date": "2025-01-15",
    }, headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_can_access_dashboard(client: AsyncClient, viewer_user: User):
    headers = make_token(viewer_user)
    resp = await client.get("/dashboard/summary", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_viewer_cannot_manage_users(client: AsyncClient, viewer_user: User):
    headers = make_token(viewer_user)
    resp = await client.get("/users", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401_or_403(client: AsyncClient):
    resp = await client.get("/records")
    assert resp.status_code in (401, 403)

import pytest
from httpx import AsyncClient
from app.models import User
from tests.conftest import make_token


# ── Viewer restrictions ─────────────────────────────────

@pytest.mark.asyncio
async def test_viewer_cannot_create_record(client: AsyncClient, viewer_user: User):
    headers = make_token(viewer_user)
    resp = await client.post("/records", json={
        "amount": "100.00", "record_type": "income",
        "category": "salary", "record_date": "2025-01-15",
    }, headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_list_records(client: AsyncClient, viewer_user: User):
    headers = make_token(viewer_user)
    resp = await client.get("/records", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_update_record(client: AsyncClient, viewer_user: User, admin_user: User):
    # admin creates a record
    admin_h = make_token(admin_user)
    cr = await client.post("/records", json={
        "amount": "500.00", "record_type": "expense",
        "category": "rent", "record_date": "2025-02-01",
    }, headers=admin_h)
    rec_id = cr.json()["id"]
    # viewer tries to update
    viewer_h = make_token(viewer_user)
    resp = await client.patch(f"/records/{rec_id}", json={
        "amount": "600.00", "expected_updated_at": cr.json()["updated_at"],
    }, headers=viewer_h)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_delete_record(client: AsyncClient, viewer_user: User):
    headers = make_token(viewer_user)
    resp = await client.delete("/records/00000000-0000-0000-0000-000000000001", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_manage_users(client: AsyncClient, viewer_user: User):
    headers = make_token(viewer_user)
    resp = await client.get("/users", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_can_access_dashboard_summary(client: AsyncClient, viewer_user: User):
    headers = make_token(viewer_user)
    resp = await client.get("/dashboard/summary", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_viewer_can_access_dashboard_trends(client: AsyncClient, viewer_user: User):
    headers = make_token(viewer_user)
    resp = await client.get("/dashboard/trends", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_viewer_can_access_category_breakdown(client: AsyncClient, viewer_user: User):
    headers = make_token(viewer_user)
    resp = await client.get("/dashboard/category-breakdown", headers=headers)
    assert resp.status_code == 200


# ── Analyst restrictions ────────────────────────────────

@pytest.mark.asyncio
async def test_analyst_cannot_create_record(client: AsyncClient, analyst_user: User):
    headers = make_token(analyst_user)
    resp = await client.post("/records", json={
        "amount": "100.00", "record_type": "income",
        "category": "salary", "record_date": "2025-01-15",
    }, headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_analyst_cannot_delete_record(client: AsyncClient, analyst_user: User):
    headers = make_token(analyst_user)
    resp = await client.delete("/records/00000000-0000-0000-0000-000000000001", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_analyst_can_list_records(client: AsyncClient, analyst_user: User):
    headers = make_token(analyst_user)
    resp = await client.get("/records", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analyst_can_get_single_record(client: AsyncClient, admin_user: User, analyst_user: User):
    admin_h = make_token(admin_user)
    cr = await client.post("/records", json={
        "amount": "250.00", "record_type": "expense",
        "category": "software", "record_date": "2025-03-01",
    }, headers=admin_h)
    rec_id = cr.json()["id"]

    analyst_h = make_token(analyst_user)
    resp = await client.get(f"/records/{rec_id}", headers=analyst_h)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analyst_can_access_dashboard(client: AsyncClient, analyst_user: User):
    headers = make_token(analyst_user)
    resp = await client.get("/dashboard/summary", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analyst_cannot_manage_users(client: AsyncClient, analyst_user: User):
    headers = make_token(analyst_user)
    resp = await client.get("/users", headers=headers)
    assert resp.status_code == 403


# ── Admin privileges ────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_can_do_everything(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    # create
    cr = await client.post("/records", json={
        "amount": "9999.00", "record_type": "income",
        "category": "consulting", "record_date": "2025-06-01",
    }, headers=headers)
    assert cr.status_code == 201
    rec = cr.json()
    # list
    assert (await client.get("/records", headers=headers)).status_code == 200
    # get single
    assert (await client.get(f"/records/{rec['id']}", headers=headers)).status_code == 200
    # update
    assert (await client.patch(f"/records/{rec['id']}", json={
        "amount": "10000.00", "expected_updated_at": rec["updated_at"],
    }, headers=headers)).status_code == 200
    # delete
    assert (await client.delete(f"/records/{rec['id']}", headers=headers)).status_code == 204
    # manage users
    assert (await client.get("/users", headers=headers)).status_code == 200
    # dashboard
    assert (await client.get("/dashboard/summary", headers=headers)).status_code == 200


# ── Unauthenticated ─────────────────────────────────────

@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_records(client: AsyncClient):
    resp = await client.get("/records")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_dashboard(client: AsyncClient):
    resp = await client.get("/dashboard/summary")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_users(client: AsyncClient):
    resp = await client.get("/users")
    assert resp.status_code in (401, 403)

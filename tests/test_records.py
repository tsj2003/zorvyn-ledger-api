import uuid
import pytest
from httpx import AsyncClient
from app.models import User
from tests.conftest import make_token


@pytest.mark.asyncio
async def test_create_and_get_record(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    create_resp = await client.post("/records", json={
        "amount": "5000.00",
        "record_type": "income",
        "category": "consulting",
        "record_date": "2025-03-01",
        "description": "March consulting payout",
    }, headers=headers)
    assert create_resp.status_code == 201
    record_id = create_resp.json()["id"]

    get_resp = await client.get(f"/records/{record_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["category"] == "consulting"


@pytest.mark.asyncio
async def test_idempotent_post(client: AsyncClient, admin_user: User):
    headers = {**make_token(admin_user), "Idempotency-Key": f"idem-{uuid.uuid4()}"}
    payload = {
        "amount": "1200.00",
        "record_type": "expense",
        "category": "rent",
        "record_date": "2025-02-01",
    }
    first = await client.post("/records", json=payload, headers=headers)
    second = await client.post("/records", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


@pytest.mark.asyncio
async def test_soft_delete_hides_from_listing(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    create_resp = await client.post("/records", json={
        "amount": "300.00", "record_type": "expense",
        "category": "utilities", "record_date": "2025-04-01",
    }, headers=headers)
    record_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/records/{record_id}", headers=headers)
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/records/{record_id}", headers=headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_optimistic_concurrency_conflict(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    create_resp = await client.post("/records", json={
        "amount": "999.00", "record_type": "income",
        "category": "salary", "record_date": "2025-06-01",
    }, headers=headers)
    body = create_resp.json()

    # first update succeeds
    patch_resp = await client.patch(f"/records/{body['id']}", json={
        "amount": "1000.00",
        "expected_updated_at": body["updated_at"],
    }, headers=headers)
    assert patch_resp.status_code == 200

    # second update with stale timestamp → 409
    conflict_resp = await client.patch(f"/records/{body['id']}", json={
        "amount": "1001.00",
        "expected_updated_at": body["updated_at"],
    }, headers=headers)
    assert conflict_resp.status_code == 409


@pytest.mark.asyncio
async def test_filter_by_category(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    await client.post("/records", json={
        "amount": "50.00", "record_type": "expense",
        "category": "groceries", "record_date": "2025-01-10",
    }, headers=headers)
    await client.post("/records", json={
        "amount": "80.00", "record_type": "expense",
        "category": "travel", "record_date": "2025-01-11",
    }, headers=headers)

    resp = await client.get("/records?category=groceries", headers=headers)
    assert resp.status_code == 200
    records = resp.json()["records"]
    assert all(r["category"] == "groceries" for r in records)


@pytest.mark.asyncio
async def test_pagination(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    for i in range(5):
        await client.post("/records", json={
            "amount": str(10 + i), "record_type": "expense",
            "category": "misc", "record_date": "2025-05-01",
        }, headers=headers)

    resp = await client.get("/records?limit=2&offset=0", headers=headers)
    body = resp.json()
    assert len(body["records"]) == 2
    assert body["total"] >= 5

import uuid
import pytest
from httpx import AsyncClient
from app.models import User
from tests.conftest import make_token


# ── CRUD Basics ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_record_returns_201_with_all_fields(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.post("/records", json={
        "amount": "5000.00", "record_type": "income",
        "category": "consulting", "record_date": "2025-03-01",
        "description": "March consulting payout",
    }, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["amount"] == "5000.00"
    assert body["record_type"] == "income"
    assert body["category"] == "consulting"
    assert body["description"] == "March consulting payout"
    assert body["record_date"] == "2025-03-01"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body
    assert body["created_by"] == str(admin_user.id)


@pytest.mark.asyncio
async def test_create_record_without_description(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.post("/records", json={
        "amount": "100.00", "record_type": "expense",
        "category": "utilities", "record_date": "2025-04-01",
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["description"] is None


@pytest.mark.asyncio
async def test_get_single_record(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    cr = await client.post("/records", json={
        "amount": "750.00", "record_type": "income",
        "category": "freelance", "record_date": "2025-05-01",
    }, headers=headers)
    record_id = cr.json()["id"]

    resp = await client.get(f"/records/{record_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["category"] == "freelance"


@pytest.mark.asyncio
async def test_get_nonexistent_record_returns_404(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/records/{fake_id}", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_record_changes_fields(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    cr = await client.post("/records", json={
        "amount": "200.00", "record_type": "expense",
        "category": "groceries", "record_date": "2025-01-05",
    }, headers=headers)
    body = cr.json()

    resp = await client.patch(f"/records/{body['id']}", json={
        "amount": "250.00",
        "category": "organic_groceries",
        "expected_updated_at": body["updated_at"],
    }, headers=headers)
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["amount"] == "250.00"
    assert updated["category"] == "organic_groceries"
    assert updated["record_type"] == "expense"  # unchanged


@pytest.mark.asyncio
async def test_update_nonexistent_record_returns_404(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    fake_id = str(uuid.uuid4())
    resp = await client.patch(f"/records/{fake_id}", json={
        "amount": "100.00",
        "expected_updated_at": "2025-01-01T00:00:00+00:00",
    }, headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_record_returns_404(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/records/{fake_id}", headers=headers)
    assert resp.status_code == 404


# ── Soft Delete ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_soft_delete_hides_from_listing(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    cr = await client.post("/records", json={
        "amount": "300.00", "record_type": "expense",
        "category": "utilities", "record_date": "2025-04-01",
    }, headers=headers)
    record_id = cr.json()["id"]

    del_resp = await client.delete(f"/records/{record_id}", headers=headers)
    assert del_resp.status_code == 204

    # GET by ID returns 404
    assert (await client.get(f"/records/{record_id}", headers=headers)).status_code == 404

    # not in listing
    listing = await client.get("/records", headers=headers)
    ids_in_list = [r["id"] for r in listing.json()["records"]]
    assert record_id not in ids_in_list


@pytest.mark.asyncio
async def test_soft_delete_excluded_from_dashboard(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    # create and immediately delete
    cr = await client.post("/records", json={
        "amount": "99999.00", "record_type": "income",
        "category": "ghost", "record_date": "2025-07-01",
    }, headers=headers)
    record_id = cr.json()["id"]
    await client.delete(f"/records/{record_id}", headers=headers)

    # dashboard should NOT include the deleted record's amount
    summary = (await client.get("/dashboard/summary", headers=headers)).json()
    # if it was counted, total_income would be >= 99999
    # since we only have this one test record and it's deleted, income should be 0
    assert float(summary["total_income"]) < 99999


@pytest.mark.asyncio
async def test_double_delete_returns_404(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    cr = await client.post("/records", json={
        "amount": "150.00", "record_type": "expense",
        "category": "misc", "record_date": "2025-08-01",
    }, headers=headers)
    record_id = cr.json()["id"]
    await client.delete(f"/records/{record_id}", headers=headers)
    # second delete should 404 since it's already soft-deleted
    resp = await client.delete(f"/records/{record_id}", headers=headers)
    assert resp.status_code == 404


# ── Idempotency ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_idempotent_post_returns_same_record(client: AsyncClient, admin_user: User):
    idem_key = f"idem-{uuid.uuid4()}"
    headers = {**make_token(admin_user), "Idempotency-Key": idem_key}
    payload = {
        "amount": "1200.00", "record_type": "expense",
        "category": "rent", "record_date": "2025-02-01",
    }
    first = await client.post("/records", json=payload, headers=headers)
    second = await client.post("/records", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


@pytest.mark.asyncio
async def test_different_idempotency_keys_create_separate_records(client: AsyncClient, admin_user: User):
    payload = {
        "amount": "500.00", "record_type": "income",
        "category": "freelance", "record_date": "2025-03-15",
    }
    h1 = {**make_token(admin_user), "Idempotency-Key": f"key-{uuid.uuid4()}"}
    h2 = {**make_token(admin_user), "Idempotency-Key": f"key-{uuid.uuid4()}"}

    r1 = await client.post("/records", json=payload, headers=h1)
    r2 = await client.post("/records", json=payload, headers=h2)

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"]


@pytest.mark.asyncio
async def test_post_without_idempotency_key_still_works(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.post("/records", json={
        "amount": "100.00", "record_type": "expense",
        "category": "travel", "record_date": "2025-06-01",
    }, headers=headers)
    assert resp.status_code == 201


# ── Optimistic Concurrency ──────────────────────────────

@pytest.mark.asyncio
async def test_optimistic_concurrency_conflict(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    cr = await client.post("/records", json={
        "amount": "999.00", "record_type": "income",
        "category": "salary", "record_date": "2025-06-01",
    }, headers=headers)
    body = cr.json()
    stale_ts = body["updated_at"]

    # first update succeeds
    patch1 = await client.patch(f"/records/{body['id']}", json={
        "amount": "1000.00", "expected_updated_at": stale_ts,
    }, headers=headers)
    assert patch1.status_code == 200

    # second update with stale timestamp → 409
    patch2 = await client.patch(f"/records/{body['id']}", json={
        "amount": "1001.00", "expected_updated_at": stale_ts,
    }, headers=headers)
    assert patch2.status_code == 409


@pytest.mark.asyncio
async def test_sequential_updates_with_fresh_timestamps_succeed(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    cr = await client.post("/records", json={
        "amount": "100.00", "record_type": "expense",
        "category": "equipment", "record_date": "2025-09-01",
    }, headers=headers)
    body = cr.json()

    # update 1
    p1 = await client.patch(f"/records/{body['id']}", json={
        "amount": "200.00", "expected_updated_at": body["updated_at"],
    }, headers=headers)
    assert p1.status_code == 200

    # update 2 with fresh timestamp from update 1
    p2 = await client.patch(f"/records/{body['id']}", json={
        "amount": "300.00", "expected_updated_at": p1.json()["updated_at"],
    }, headers=headers)
    assert p2.status_code == 200
    assert p2.json()["amount"] == "300.00"


# ── Filtering ───────────────────────────────────────────

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
    assert len(records) >= 1
    assert all(r["category"] == "groceries" for r in records)


@pytest.mark.asyncio
async def test_filter_by_record_type(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    await client.post("/records", json={
        "amount": "1000.00", "record_type": "income",
        "category": "salary", "record_date": "2025-02-01",
    }, headers=headers)
    await client.post("/records", json={
        "amount": "200.00", "record_type": "expense",
        "category": "rent", "record_date": "2025-02-01",
    }, headers=headers)

    resp = await client.get("/records?record_type=income", headers=headers)
    records = resp.json()["records"]
    assert all(r["record_type"] == "income" for r in records)


@pytest.mark.asyncio
async def test_filter_by_date_range(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    await client.post("/records", json={
        "amount": "100.00", "record_type": "expense",
        "category": "misc", "record_date": "2025-01-15",
    }, headers=headers)
    await client.post("/records", json={
        "amount": "200.00", "record_type": "expense",
        "category": "misc", "record_date": "2025-06-15",
    }, headers=headers)

    resp = await client.get("/records?date_from=2025-01-01&date_to=2025-02-28", headers=headers)
    records = resp.json()["records"]
    for r in records:
        assert r["record_date"] >= "2025-01-01"
        assert r["record_date"] <= "2025-02-28"


@pytest.mark.asyncio
async def test_combined_filters(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    await client.post("/records", json={
        "amount": "500.00", "record_type": "income",
        "category": "consulting", "record_date": "2025-03-15",
    }, headers=headers)

    resp = await client.get(
        "/records?record_type=income&category=consulting&date_from=2025-03-01&date_to=2025-03-31",
        headers=headers,
    )
    records = resp.json()["records"]
    assert len(records) >= 1
    for r in records:
        assert r["record_type"] == "income"
        assert r["category"] == "consulting"


# ── Pagination ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_pagination_limit_and_offset(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    for i in range(5):
        await client.post("/records", json={
            "amount": str(10 + i), "record_type": "expense",
            "category": "misc", "record_date": "2025-05-01",
        }, headers=headers)

    page1 = await client.get("/records?limit=2&offset=0", headers=headers)
    body1 = page1.json()
    assert len(body1["records"]) == 2
    assert body1["total"] >= 5
    assert body1["limit"] == 2
    assert body1["offset"] == 0

    page2 = await client.get("/records?limit=2&offset=2", headers=headers)
    body2 = page2.json()
    assert len(body2["records"]) == 2
    # pages should have different records
    ids1 = {r["id"] for r in body1["records"]}
    ids2 = {r["id"] for r in body2["records"]}
    assert ids1.isdisjoint(ids2)


@pytest.mark.asyncio
async def test_pagination_offset_beyond_total_returns_empty(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.get("/records?limit=10&offset=99999", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["records"] == []


# ── Validation Edge Cases ───────────────────────────────

@pytest.mark.asyncio
async def test_create_record_with_zero_amount_returns_422(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.post("/records", json={
        "amount": "0", "record_type": "income",
        "category": "test", "record_date": "2025-01-01",
    }, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_record_with_negative_amount_returns_422(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.post("/records", json={
        "amount": "-50.00", "record_type": "expense",
        "category": "test", "record_date": "2025-01-01",
    }, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_record_with_invalid_record_type_returns_422(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.post("/records", json={
        "amount": "100.00", "record_type": "donation",
        "category": "test", "record_date": "2025-01-01",
    }, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_record_missing_required_fields_returns_422(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.post("/records", json={"amount": "100.00"}, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_record_with_empty_category_returns_422(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.post("/records", json={
        "amount": "100.00", "record_type": "income",
        "category": "", "record_date": "2025-01-01",
    }, headers=headers)
    assert resp.status_code == 422

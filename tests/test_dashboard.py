import pytest
from httpx import AsyncClient
from app.models import User
from tests.conftest import make_token


# ── Dashboard Summary ──────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_summary_with_records(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    await client.post("/records", json={
        "amount": "5000.00", "record_type": "income",
        "category": "salary", "record_date": "2025-01-01",
    }, headers=headers)
    await client.post("/records", json={
        "amount": "1200.00", "record_type": "expense",
        "category": "rent", "record_date": "2025-01-02",
    }, headers=headers)

    resp = await client.get("/dashboard/summary", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert float(body["total_income"]) >= 5000
    assert float(body["total_expenses"]) >= 1200
    net = float(body["total_income"]) - float(body["total_expenses"])
    assert float(body["net_balance"]) == net
    assert body["record_count"] >= 2


@pytest.mark.asyncio
async def test_dashboard_summary_empty_database(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.get("/dashboard/summary", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert float(body["total_income"]) == 0
    assert float(body["total_expenses"]) == 0
    assert float(body["net_balance"]) == 0
    assert body["record_count"] == 0


@pytest.mark.asyncio
async def test_dashboard_net_balance_accuracy(client: AsyncClient, admin_user: User):
    """Verify exact decimal math — no floating-point drift."""
    headers = make_token(admin_user)
    await client.post("/records", json={
        "amount": "149.99", "record_type": "income",
        "category": "refund", "record_date": "2025-05-01",
    }, headers=headers)
    await client.post("/records", json={
        "amount": "49.99", "record_type": "expense",
        "category": "groceries", "record_date": "2025-05-02",
    }, headers=headers)

    summary = (await client.get("/dashboard/summary", headers=headers)).json()
    # must be exactly 100.00, not 100.00000000000001
    assert summary["net_balance"] == "100.00"


# ── Category Breakdown ─────────────────────────────────

@pytest.mark.asyncio
async def test_category_breakdown_returns_list(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.get("/dashboard/category-breakdown", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_category_breakdown_groups_correctly(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    await client.post("/records", json={
        "amount": "100.00", "record_type": "expense",
        "category": "rent", "record_date": "2025-01-01",
    }, headers=headers)
    await client.post("/records", json={
        "amount": "200.00", "record_type": "expense",
        "category": "rent", "record_date": "2025-01-15",
    }, headers=headers)
    await client.post("/records", json={
        "amount": "50.00", "record_type": "expense",
        "category": "coffee", "record_date": "2025-01-10",
    }, headers=headers)

    breakdown = (await client.get("/dashboard/category-breakdown", headers=headers)).json()
    rent_entry = next((b for b in breakdown if b["category"] == "rent" and b["record_type"] == "expense"), None)
    assert rent_entry is not None
    assert float(rent_entry["total"]) == 300.00


@pytest.mark.asyncio
async def test_category_breakdown_sorted_by_total_desc(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    await client.post("/records", json={
        "amount": "9000.00", "record_type": "income",
        "category": "salary", "record_date": "2025-03-01",
    }, headers=headers)
    await client.post("/records", json={
        "amount": "100.00", "record_type": "income",
        "category": "tips", "record_date": "2025-03-01",
    }, headers=headers)

    breakdown = (await client.get("/dashboard/category-breakdown", headers=headers)).json()
    totals = [float(b["total"]) for b in breakdown]
    assert totals == sorted(totals, reverse=True)


# ── Monthly Trends ──────────────────────────────────────

@pytest.mark.asyncio
async def test_monthly_trends_returns_list(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.get("/dashboard/trends", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_monthly_trends_structure(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    await client.post("/records", json={
        "amount": "3000.00", "record_type": "income",
        "category": "salary", "record_date": "2025-03-15",
    }, headers=headers)

    trends = (await client.get("/dashboard/trends", headers=headers)).json()
    assert len(trends) >= 1
    t = trends[0]
    assert "year" in t
    assert "month" in t
    assert "income" in t
    assert "expenses" in t


@pytest.mark.asyncio
async def test_monthly_trends_custom_months_param(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.get("/dashboard/trends?months=3", headers=headers)
    assert resp.status_code == 200


# ── Recent Activity ─────────────────────────────────────

@pytest.mark.asyncio
async def test_recent_activity_returns_latest_first(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    await client.post("/records", json={
        "amount": "10.00", "record_type": "expense",
        "category": "first", "record_date": "2025-01-01",
    }, headers=headers)
    await client.post("/records", json={
        "amount": "20.00", "record_type": "expense",
        "category": "second", "record_date": "2025-01-02",
    }, headers=headers)

    recent = (await client.get("/dashboard/recent-activity?limit=2", headers=headers)).json()
    assert len(recent) == 2
    # most recent should be "second" (created last)
    assert recent[0]["category"] == "second"


@pytest.mark.asyncio
async def test_recent_activity_respects_limit(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    for i in range(5):
        await client.post("/records", json={
            "amount": str(10 + i), "record_type": "expense",
            "category": f"cat_{i}", "record_date": "2025-06-01",
        }, headers=headers)

    resp = await client.get("/dashboard/recent-activity?limit=3", headers=headers)
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_recent_activity_excludes_deleted_records(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    cr = await client.post("/records", json={
        "amount": "999.00", "record_type": "income",
        "category": "deleted_check", "record_date": "2025-08-01",
    }, headers=headers)
    record_id = cr.json()["id"]
    await client.delete(f"/records/{record_id}", headers=headers)

    recent = (await client.get("/dashboard/recent-activity?limit=50", headers=headers)).json()
    ids = [r["id"] for r in recent]
    assert record_id not in ids


# ── Health Endpoint ─────────────────────────────────────

@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert "db" in body


@pytest.mark.asyncio
async def test_health_is_public_no_auth_needed(client: AsyncClient):
    """Health must be accessible without any Authorization header."""
    resp = await client.get("/health")
    assert resp.status_code == 200

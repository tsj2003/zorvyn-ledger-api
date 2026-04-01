import pytest
from httpx import AsyncClient
from app.models import User
from tests.conftest import make_token


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
    assert float(body["net_balance"]) == float(body["total_income"]) - float(body["total_expenses"])


@pytest.mark.asyncio
async def test_category_breakdown(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.get("/dashboard/category-breakdown", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_monthly_trends(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.get("/dashboard/trends", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_recent_activity(client: AsyncClient, admin_user: User):
    headers = make_token(admin_user)
    resp = await client.get("/dashboard/recent-activity", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")

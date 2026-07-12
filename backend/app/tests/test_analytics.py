import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_analytics_usage(client, auth_headers):
    resp = await client.get("/api/v1/analytics/usage", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_sessions" in data
    assert "total_messages" in data
    assert "dau" in data


@pytest.mark.asyncio
async def test_analytics_errors(client, auth_headers):
    resp = await client.get("/api/v1/analytics/errors", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_analytics_top_questions(client, auth_headers):
    resp = await client.get("/api/v1/analytics/top-questions", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_analytics_cost_breakdown(client, auth_headers):
    resp = await client.get("/api/v1/analytics/cost-breakdown", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_analytics_daily(client, auth_headers):
    resp = await client.get("/api/v1/analytics/daily", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_analytics_unauthorized(client):
    resp = await client.get("/api/v1/analytics/usage")
    assert resp.status_code in (401, 403)

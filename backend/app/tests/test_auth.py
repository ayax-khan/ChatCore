import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_healthz():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_register_user(client):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "password": "StrongPass123!",
        "business_name": "New Business",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "user_id" in data
    assert data["email"] == "newuser@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await client.post("/api/v1/auth/register", json={
        "email": "dup@example.com",
        "password": "StrongPass123!",
        "business_name": "Business 1",
    })
    resp = await client.post("/api/v1/auth/register", json={
        "email": "dup@example.com",
        "password": "StrongPass456!",
        "business_name": "Business 2",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "password": "StrongPass123!",
        "business_name": "Login Business",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "StrongPass123!",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_invalid_email(client):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "not-an-email",
        "password": "StrongPass123!",
        "business_name": "Test",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_protected_endpoint_no_token(client):
    resp = await client.get("/api/v1/sites/")
    assert resp.status_code == 403 or resp.status_code == 401

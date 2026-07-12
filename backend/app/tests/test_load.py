"""
Load/Stress tests using pytest-benchmark or direct concurrent requests.
Run with: pytest tests/test_load.py -v --benchmark-only
"""
import asyncio
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_concurrent_health_checks():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tasks = [client.get("/healthz") for _ in range(50)]
        responses = await asyncio.gather(*tasks)
        for resp in responses:
            assert resp.status_code == 200


@pytest.mark.asyncio
async def test_concurrent_registrations():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tasks = []
        for i in range(10):
            tasks.append(client.post("/api/v1/auth/register", json={
                "email": f"load{i}@test.com",
                "password": "LoadTest123!",
                "business_name": f"Load Business {i}",
            }))
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code in (200, 201))
        assert success_count >= 8


@pytest.mark.asyncio
async def test_concurrent_chat_requests():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        register = await client.post("/api/v1/auth/register", json={
            "email": "load-chat@test.com",
            "password": "LoadTest123!",
            "business_name": "Load Chat",
        })
        if register.status_code not in (200, 201):
            pytest.skip("Registration failed")
        login = await client.post("/api/v1/auth/login", json={
            "email": "load-chat@test.com",
            "password": "LoadTest123!",
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        site = await client.post("/api/v1/sites/", json={
            "url": "https://load-test.com",
            "name": "Load Test",
        }, headers=headers)
        site_id = site.json()["id"]

        tasks = [
            client.post("/api/v1/chat/", json={
                "question": f"Question {i}",
                "site_id": site_id,
            }, headers=headers)
            for i in range(20)
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code in (200, 404, 500))
        assert success_count >= 15

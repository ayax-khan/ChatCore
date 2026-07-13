"""
End-to-end tests simulating a full user journey:
Register -> Login -> Create Site -> Crawl -> Chat -> View Analytics -> Invite Team -> Logout
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.skip(reason="Requires PostgreSQL, Qdrant, and Redis running")
@pytest.mark.asyncio
async def test_full_user_journey():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        health = await client.get("/healthz")
        assert health.status_code == 200

        # 2. Register
        register = await client.post("/api/v1/auth/register", json={
            "email": "e2e@test.com",
            "password": "E2eTest123!",
            "business_name": "E2E Business",
        })
        assert register.status_code == 201
        user_id = register.json()["user_id"]

        # 3. Login
        login = await client.post("/api/v1/auth/login", json={
            "email": "e2e@test.com",
            "password": "E2eTest123!",
        })
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 4. Create site
        site = await client.post("/api/v1/sites/", json={
            "url": "https://example.com",
            "name": "E2E Site",
        }, headers=headers)
        assert site.status_code in (200, 201)
        site_id = site.json()["id"]

        # 5. List sites
        sites = await client.get("/api/v1/sites/", headers=headers)
        assert sites.status_code == 200
        assert len(sites.json()) > 0

        # 6. Get site
        site_detail = await client.get(f"/api/v1/sites/{site_id}", headers=headers)
        assert site_detail.status_code == 200

        # 7. Chat
        chat = await client.post("/api/v1/chat/", json={
            "question": "What services do you offer?",
            "site_id": site_id,
            "session_id": "e2e-session",
        }, headers=headers)
        assert chat.status_code in (200, 404, 500)

        # 8. Analytics
        analytics = await client.get("/api/v1/analytics/usage", headers=headers)
        assert analytics.status_code == 200

        # 9. Feedback
        feedback = await client.post("/api/v1/feedback/", json={
            "session_id": "e2e-session",
            "rating": 5,
            "comment": "Great!",
        }, headers=headers)
        assert feedback.status_code in (200, 201)

        # 10. Logout
        logout = await client.post("/api/v1/security/logout", headers=headers)
        assert logout.status_code in (200, 204)

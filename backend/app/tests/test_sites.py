import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_list_sites(client, auth_headers):
    resp = await client.get("/api/v1/sites/", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_site(client, auth_headers):
    resp = await client.post("/api/v1/sites/", json={
        "url": "https://example.com",
        "name": "Example Site",
    }, headers=auth_headers)
    assert resp.status_code in (200, 201)
    if resp.status_code in (200, 201):
        data = resp.json()
        assert data["url"] == "https://example.com"
        assert "id" in data


@pytest.mark.asyncio
async def test_create_site_invalid_url(client, auth_headers):
    resp = await client.post("/api/v1/sites/", json={
        "url": "not-a-url",
        "name": "Invalid Site",
    }, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_site(client, auth_headers):
    create_resp = await client.post("/api/v1/sites/", json={
        "url": "https://example.com",
        "name": "Test Site",
    }, headers=auth_headers)
    if create_resp.status_code not in (200, 201):
        pytest.skip("Site creation failed")
    site_id = create_resp.json()["id"]
    resp = await client.get(f"/api/v1/sites/{site_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == site_id


@pytest.mark.asyncio
async def test_delete_site(client, auth_headers):
    create_resp = await client.post("/api/v1/sites/", json={
        "url": "https://delete-me.com",
        "name": "Delete Me",
    }, headers=auth_headers)
    if create_resp.status_code not in (200, 201):
        pytest.skip("Site creation failed")
    site_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/v1/sites/{site_id}", headers=auth_headers)
    assert resp.status_code in (200, 204)


@pytest.mark.asyncio
async def test_trigger_crawl(client, auth_headers):
    create_resp = await client.post("/api/v1/sites/", json={
        "url": "https://crawl-test.com",
        "name": "Crawl Test",
    }, headers=auth_headers)
    if create_resp.status_code not in (200, 201):
        pytest.skip("Site creation failed")
    site_id = create_resp.json()["id"]
    resp = await client.post(f"/api/v1/sites/{site_id}/crawl", headers=auth_headers)
    assert resp.status_code in (200, 202)

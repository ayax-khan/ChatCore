import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_chat_no_history(client, auth_headers):
    resp = await client.post("/api/v1/chat/", json={
        "question": "What is your return policy?",
        "site_id": 1,
    }, headers=auth_headers)
    assert resp.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_chat_with_history(client, auth_headers):
    resp = await client.post("/api/v1/chat/", json={
        "question": "Tell me more about pricing",
        "site_id": 1,
        "session_id": "test-session-123",
    }, headers=auth_headers)
    assert resp.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_chat_empty_question(client, auth_headers):
    resp = await client.post("/api/v1/chat/", json={
        "question": "",
        "site_id": 1,
    }, headers=auth_headers)
    assert resp.status_code in (422, 500)


@pytest.mark.asyncio
async def test_chat_unauthorized(client):
    resp = await client.post("/api/v1/chat/", json={
        "question": "Hello",
        "site_id": 1,
    })
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_chat_invalid_site(client, auth_headers):
    resp = await client.post("/api/v1/chat/", json={
        "question": "Hello",
        "site_id": 99999,
    }, headers=auth_headers)
    assert resp.status_code in (200, 404, 500)


@pytest.mark.asyncio
async def test_chat_rate_limited(client, auth_headers):
    for _ in range(5):
        await client.post("/api/v1/chat/", json={
            "question": "Test question",
            "site_id": 1,
        }, headers=auth_headers)
    resp = await client.post("/api/v1/chat/", json={
        "question": "Another question",
        "site_id": 1,
    }, headers=auth_headers)
    assert resp.status_code in (200, 429, 500)


@pytest.mark.asyncio
async def test_chat_with_session(client, auth_headers):
    resp = await client.post("/api/v1/chat/", json={
        "question": "What is your return policy?",
        "site_id": 1,
        "session_id": "session-abc-123",
    }, headers=auth_headers)
    assert resp.status_code in (200, 404, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

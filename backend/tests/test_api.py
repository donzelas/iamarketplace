import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_auth_register_and_login(client):
    resp = await client.post("/api/auth/register", json={"username": "testuser", "password": "testpass123"})
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data

    resp = await client.post("/api/auth/login", json={"username": "testuser", "password": "testpass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_auth_login_wrong_password(client):
    await client.post("/api/auth/register", json={"username": "testuser2", "password": "pass"})
    resp = await client.post("/api/auth/login", json={"username": "testuser2", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_duplicate_register(client):
    await client.post("/api/auth/register", json={"username": "dupe", "password": "pass"})
    resp = await client.post("/api/auth/register", json={"username": "dupe", "password": "pass"})
    assert resp.status_code == 409

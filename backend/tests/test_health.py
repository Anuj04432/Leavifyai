import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "WorkforceAI"
    assert data["status"] == "operational"


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "redis" in data

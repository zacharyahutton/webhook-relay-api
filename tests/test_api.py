import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(autouse=True)
def clean_store(tmp_path, monkeypatch):
    data_file = tmp_path / "store.json"
    monkeypatch.setattr("app.store.DATA_FILE", data_file)
    yield


@pytest.mark.anyio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "webhook-relay-api"


@pytest.mark.anyio
async def test_register_webhook_requires_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/webhooks", json={"url": "https://example.com/hook"})
    assert r.status_code == 422


@pytest.mark.anyio
async def test_register_and_list_deliveries_empty():
    headers = {"X-API-Key": "demo-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        reg = await client.post(
            "/webhooks",
            headers=headers,
            json={"url": "https://example.com/hook"},
        )
        assert reg.status_code == 201
        deliveries = await client.get("/deliveries", headers=headers)
    assert deliveries.status_code == 200
    assert deliveries.json() == []

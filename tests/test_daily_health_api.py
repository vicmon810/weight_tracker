import sqlite3

import httpx
import pytest

from api.health_api import create_app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client_and_database(tmp_path):
    database_path = tmp_path / "health.db"
    transport = httpx.ASGITransport(app=create_app(str(database_path)))
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client, database_path


@pytest.mark.anyio
async def test_create_and_read_daily_health(client_and_database):
    client, _ = client_and_database
    payload = {
        "date": "2026-08-24",
        "weight_kg": 78.2,
        "steps": 8560,
        "sleep_hours": 7.5,
    }

    response = await client.post("/daily-health", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "date": "2026-08-24"}
    stored = await client.get("/daily-health/2026-08-24")
    assert stored.status_code == 200
    assert stored.json()["weight_kg"] == 78.2
    assert stored.json()["steps"] == 8560
    assert stored.json()["sleep_hours"] == 7.5


@pytest.mark.anyio
async def test_same_date_update_keeps_one_row_and_preserves_non_null_metrics(
    client_and_database,
):
    client, database_path = client_and_database
    first = {
        "date": "2026-08-24",
        "weight_kg": 78.2,
        "steps": 8560,
        "sleep_hours": 7.5,
    }
    partial_update = {
        "date": "2026-08-24",
        "weight_kg": 77.9,
        "steps": None,
        "sleep_hours": None,
    }

    assert (await client.post("/daily-health", json=first)).status_code == 200
    assert (
        await client.post("/daily-health", json=partial_update)
    ).status_code == 200

    stored = (await client.get("/daily-health/2026-08-24")).json()
    assert stored["weight_kg"] == 77.9
    assert stored["steps"] == 8560
    assert stored["sleep_hours"] == 7.5
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM daily_health WHERE date = ?",
            ("2026-08-24",),
        ).fetchone()[0]
    assert count == 1


@pytest.mark.anyio
async def test_partial_snapshot_is_accepted(client_and_database):
    client, _ = client_and_database

    response = await client.post(
        "/daily-health",
        json={"date": "2026-08-24", "steps": 1200},
    )

    assert response.status_code == 200


@pytest.mark.anyio
async def test_snapshot_requires_at_least_one_metric(client_and_database):
    client, _ = client_and_database

    response = await client.post(
        "/daily-health",
        json={"date": "2026-08-24"},
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_snapshot_rejects_invalid_values(client_and_database):
    client, _ = client_and_database
    invalid_payloads = [
        {"date": "invalid", "steps": 1},
        {"date": "2026-08-24", "weight_kg": 0},
        {"date": "2026-08-24", "steps": -1},
        {"date": "2026-08-24", "sleep_hours": 24.1},
    ]

    for payload in invalid_payloads:
        assert (
            await client.post("/daily-health", json=payload)
        ).status_code == 422


@pytest.mark.anyio
async def test_unknown_date_returns_not_found(client_and_database):
    client, _ = client_and_database

    response = await client.get("/daily-health/2026-08-25")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_health_endpoint_reports_ok(client_and_database):
    client, _ = client_and_database

    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

"""Database-free API health and route-surface tests."""

import os
from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings
from app.database import Database
from app.main import create_app


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    """Create an isolated test API without reading the local .env."""
    setting_names = {name.casefold() for name in Settings.model_fields}

    for environment_name in list(os.environ):
        if environment_name.casefold() in setting_names:
            monkeypatch.delenv(environment_name, raising=False)

    settings = Settings(
        _env_file=None,
        app_env="test",
    )

    application = create_app(settings)

    with TestClient(application) as test_client:
        yield test_client


def test_liveness_does_not_query_database(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Process liveness remains independent of PostgreSQL connectivity."""
    ping = AsyncMock()
    monkeypatch.setattr(Database, "ping", ping)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["environment"] == "test"
    assert response.json()["is_paper"] is True

    ping.assert_not_awaited()


def test_readiness_reports_reachable_database(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful database probe produces a ready response."""
    ping = AsyncMock()
    monkeypatch.setattr(Database, "ping", ping)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "reachable",
    }

    ping.assert_awaited_once()


def test_readiness_hides_database_error_details(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Database exception text must not appear in the HTTP response."""
    ping = AsyncMock(side_effect=SQLAlchemyError("example-sensitive-connection-detail"))
    monkeypatch.setattr(Database, "ping", ping)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "database": "unavailable",
    }
    assert "example-sensitive-connection-detail" not in response.text


def test_readiness_handles_connection_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed network connection produces an unavailable response."""
    ping = AsyncMock(side_effect=OSError("Connection unavailable"))
    monkeypatch.setattr(Database, "ping", ping)

    response = client.get("/health/ready")

    assert response.status_code == 503


def test_read_only_routes_are_registered(client: TestClient) -> None:
    """The expected versioned inspection routes appear in OpenAPI."""
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    expected = {
        "/api/v1/strategies",
        "/api/v1/strategies/{strategy_id}",
        "/api/v1/signals",
        "/api/v1/orders",
        "/api/v1/orders/{order_id}",
        "/api/v1/trades",
        "/api/v1/portfolio/snapshots",
        "/api/v1/portfolio/latest",
    }

    assert expected.issubset(paths)


def test_trading_write_endpoints_are_not_exposed(
    client: TestClient,
) -> None:
    """This development stage exposes no HTTP write operations."""
    paths = client.get("/openapi.json").json()["paths"]
    write_methods = {"post", "put", "patch", "delete"}

    for operations in paths.values():
        assert not write_methods.intersection(operations)

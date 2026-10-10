"""Tests for /health readiness semantics."""

from __future__ import annotations

from types import SimpleNamespace


def test_health_ready_when_model_and_database_available(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["api"] == "ok"
    assert body["model_loaded"] is True
    assert body["database"] == "ok"
    assert "path" not in str(body).lower()
    assert "pkl" not in str(body).lower()
    assert "\\" not in str(body)
    assert "/Users/" not in str(body)
    assert "/home/" not in str(body)


def test_health_model_unavailable_returns_503_unhealthy(client, monkeypatch):
    monkeypatch.setattr(
        "main.get_model_service",
        lambda: SimpleNamespace(loaded=False),
    )
    monkeypatch.setattr("main.ping_database", lambda: True)
    response = client.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unhealthy"
    assert body["api"] == "ok"
    assert body["model_loaded"] is False
    assert body["database"] == "ok"


def test_health_database_unavailable_returns_503_unhealthy(client, monkeypatch):
    monkeypatch.setattr(
        "main.get_model_service",
        lambda: SimpleNamespace(loaded=True),
    )
    monkeypatch.setattr("main.ping_database", lambda: False)
    response = client.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unhealthy"
    assert body["api"] == "ok"
    assert body["model_loaded"] is True
    assert body["database"] == "unavailable"


def test_health_response_fields_remain_compatible(client):
    """Existing consumers expect status, api, and model_loaded keys."""
    body = client.get("/health").json()
    assert set(body.keys()) >= {"status", "api", "model_loaded", "database"}


def test_health_unavailable_has_no_filesystem_paths(client, monkeypatch):
    monkeypatch.setattr(
        "main.get_model_service",
        lambda: SimpleNamespace(loaded=False, load_error="C:\\secret\\model.pkl"),
    )
    monkeypatch.setattr("main.ping_database", lambda: True)
    response = client.get("/health")
    assert response.status_code == 503
    text = response.text
    assert "secret" not in text.lower()
    assert "model.pkl" not in text
    assert "C:\\" not in text

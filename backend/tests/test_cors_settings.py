"""Tests for APP_ENV-aware CORS origin configuration."""

from __future__ import annotations

import pytest

from cors_settings import (
    ALLOW_CREDENTIALS,
    DEFAULT_DEV_ORIGINS,
    PRODUCTION_CORS_ERROR,
    WILDCARD_CORS_ERROR,
    parse_cors_origins,
    resolve_cors_origins,
)


@pytest.fixture
def clear_cors_env(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)


def test_development_unset_uses_localhost_defaults(clear_cors_env):
    assert resolve_cors_origins() == DEFAULT_DEV_ORIGINS
    assert resolve_cors_origins() == [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
    ]


def test_development_configured_origins_are_used(clear_cors_env, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://preview.example,http://127.0.0.1:3000")
    assert resolve_cors_origins() == [
        "https://preview.example",
        "http://127.0.0.1:3000",
    ]


def test_comma_separated_origins_parsed_correctly():
    assert parse_cors_origins(
        "http://localhost:3000,https://app.example"
    ) == ["http://localhost:3000", "https://app.example"]


def test_whitespace_is_trimmed():
    assert parse_cors_origins(
        " http://localhost:3000 , https://app.example "
    ) == ["http://localhost:3000", "https://app.example"]


def test_empty_entries_are_ignored():
    assert parse_cors_origins(
        "http://localhost:3000,, ,https://app.example,"
    ) == ["http://localhost:3000", "https://app.example"]


def test_production_without_cors_origins_fails(clear_cors_env, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="CORS_ORIGINS must be configured") as exc:
        resolve_cors_origins()
    assert str(exc.value) == PRODUCTION_CORS_ERROR


def test_production_with_empty_cors_origins_fails(clear_cors_env, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "  ,  ")
    with pytest.raises(RuntimeError, match="CORS_ORIGINS must be configured"):
        resolve_cors_origins()


def test_production_with_cors_origins_succeeds(clear_cors_env, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://frontend.example")
    assert resolve_cors_origins() == ["https://frontend.example"]


def test_wildcard_always_fails(clear_cors_env, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="cannot include '\\*'") as exc:
        resolve_cors_origins()
    assert str(exc.value) == WILDCARD_CORS_ERROR


def test_wildcard_among_origins_fails(clear_cors_env, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://frontend.example,*")
    with pytest.raises(RuntimeError, match="cannot include '\\*'"):
        resolve_cors_origins()


def test_allow_credentials_remains_true():
    assert ALLOW_CREDENTIALS is True


def test_predict_options_preflight_allows_localhost_3001(client):
    """
    Regression: Vite often falls back to :3001 when :3000 is busy.
    Browser preflight must succeed or Axios surfaces ERR_NETWORK.
    """
    response = client.options(
        "/api/predict",
        headers={
            "Origin": "http://localhost:3001",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == (
        "http://localhost:3001"
    )
    assert response.headers.get("access-control-allow-credentials") == "true"
    allow_methods = response.headers.get("access-control-allow-methods", "")
    assert "POST" in allow_methods.upper()

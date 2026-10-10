"""Tests for production JWT SECRET_KEY configuration."""

from __future__ import annotations

import os

import pytest

from jwt_settings import (
    INSECURE_DEFAULT_SECRET,
    PRODUCTION_SECRET_ERROR,
    resolve_jwt_secret_key,
)


@pytest.fixture
def clear_secret_env(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)


def test_development_without_secret_uses_local_default(clear_secret_env):
    assert resolve_jwt_secret_key() == INSECURE_DEFAULT_SECRET


def test_development_with_custom_secret(clear_secret_env, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "local-dev-only-not-for-production")
    assert resolve_jwt_secret_key() == "local-dev-only-not-for-production"


def test_production_missing_secret_fails(clear_secret_env, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="SECRET_KEY must be configured") as exc:
        resolve_jwt_secret_key()
    assert str(exc.value) == PRODUCTION_SECRET_ERROR
    assert INSECURE_DEFAULT_SECRET not in str(exc.value)


def test_production_empty_secret_fails(clear_secret_env, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "   ")
    with pytest.raises(RuntimeError, match="SECRET_KEY must be configured"):
        resolve_jwt_secret_key()


def test_production_insecure_default_fails(clear_secret_env, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", INSECURE_DEFAULT_SECRET)
    with pytest.raises(RuntimeError, match="SECRET_KEY must be configured"):
        resolve_jwt_secret_key()


def test_production_insecure_placeholder_fails(clear_secret_env, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("SECRET_KEY", "changeme")
    with pytest.raises(RuntimeError, match="SECRET_KEY must be configured"):
        resolve_jwt_secret_key()


def test_production_strong_secret_succeeds(clear_secret_env, monkeypatch):
    strong = "f4c8e2a1b9d0-production-signing-key-not-a-placeholder"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", strong)
    assert resolve_jwt_secret_key() == strong


def test_production_error_never_echoes_configured_secret(
    clear_secret_env, monkeypatch
):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "changeme")
    with pytest.raises(RuntimeError) as exc:
        resolve_jwt_secret_key()
    assert "changeme" not in str(exc.value)
    assert str(exc.value) == PRODUCTION_SECRET_ERROR


def test_production_env_via_environment_variable(clear_secret_env, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "configured-prod-key-with-sufficient-entropy")
    assert resolve_jwt_secret_key() == "configured-prod-key-with-sufficient-entropy"

"""Tests for production uvicorn startup configuration."""

from __future__ import annotations

import pytest

from startup_settings import (
    DEFAULT_PORT,
    DEFAULT_PRODUCTION_HOST,
    DEFAULT_WORKERS,
    INVALID_PORT_ERROR,
    INVALID_WORKERS_ERROR,
    build_production_uvicorn_kwargs,
    production_reload_enabled,
    resolve_port,
    resolve_workers,
)


@pytest.fixture
def clear_startup_env(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("WEB_CONCURRENCY", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)


def test_development_port_default_matches_project(clear_startup_env):
    """Local docs use --port 8001; production default matches that port."""
    assert DEFAULT_PORT == 8001
    assert resolve_port() == 8001


def test_production_config_never_enables_reload(clear_startup_env):
    assert production_reload_enabled() is False
    kwargs = build_production_uvicorn_kwargs()
    assert kwargs["reload"] is False


def test_default_production_port_when_port_absent(clear_startup_env):
    assert resolve_port() == DEFAULT_PORT
    assert build_production_uvicorn_kwargs()["port"] == 8001


def test_port_environment_variable_is_respected(clear_startup_env, monkeypatch):
    monkeypatch.setenv("PORT", "9000")
    assert resolve_port() == 9000
    assert build_production_uvicorn_kwargs()["port"] == 9000


def test_invalid_port_rejected_safely(clear_startup_env, monkeypatch):
    monkeypatch.setenv("PORT", "not-a-port")
    with pytest.raises(RuntimeError) as exc:
        resolve_port()
    assert str(exc.value) == INVALID_PORT_ERROR
    assert "SECRET" not in str(exc.value).upper()
    assert "sqlite" not in str(exc.value).lower()


def test_out_of_range_port_rejected(clear_startup_env, monkeypatch):
    monkeypatch.setenv("PORT", "0")
    with pytest.raises(RuntimeError) as exc:
        resolve_port()
    assert str(exc.value) == INVALID_PORT_ERROR

    monkeypatch.setenv("PORT", "65536")
    with pytest.raises(RuntimeError) as exc:
        resolve_port()
    assert str(exc.value) == INVALID_PORT_ERROR


def test_workers_default_conservative(clear_startup_env):
    assert resolve_workers() == DEFAULT_WORKERS
    assert build_production_uvicorn_kwargs()["workers"] == 1


def test_workers_environment_variable_is_respected(clear_startup_env, monkeypatch):
    monkeypatch.setenv("WEB_CONCURRENCY", "2")
    assert resolve_workers() == 2
    # Do not launch workers — only validate configuration.
    assert build_production_uvicorn_kwargs()["workers"] == 2


def test_invalid_workers_rejected_safely(clear_startup_env, monkeypatch):
    monkeypatch.setenv("WEB_CONCURRENCY", "abc")
    with pytest.raises(RuntimeError) as exc:
        resolve_workers()
    assert str(exc.value) == INVALID_WORKERS_ERROR

    monkeypatch.setenv("WEB_CONCURRENCY", "0")
    with pytest.raises(RuntimeError) as exc:
        resolve_workers()
    assert str(exc.value) == INVALID_WORKERS_ERROR


def test_production_host_is_all_interfaces(clear_startup_env):
    kwargs = build_production_uvicorn_kwargs()
    assert kwargs["host"] == DEFAULT_PRODUCTION_HOST
    assert kwargs["host"] == "0.0.0.0"
    assert kwargs["app"] == "main:app"


def test_error_messages_do_not_expose_secrets(clear_startup_env, monkeypatch):
    monkeypatch.setenv("PORT", "bad")
    monkeypatch.setenv("SECRET_KEY", "super-secret-value-should-not-leak")
    with pytest.raises(RuntimeError) as exc:
        resolve_port()
    message = str(exc.value)
    assert "super-secret" not in message
    assert message == INVALID_PORT_ERROR


def test_production_kwargs_exclude_reload_flag_true(clear_startup_env, monkeypatch):
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    kwargs = build_production_uvicorn_kwargs()
    assert kwargs == {
        "app": "main:app",
        "host": "0.0.0.0",
        "port": 8080,
        "workers": 1,
        "reload": False,
    }

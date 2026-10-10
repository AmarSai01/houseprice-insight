"""Tests for APP_ENV-aware OpenAPI / docs exposure."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openapi_settings import resolve_openapi_docs_kwargs


@pytest.fixture
def clear_app_env(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)


def test_development_docs_available(client, clear_app_env):
    response = client.get("/docs")
    assert response.status_code == 200


def test_development_openapi_json_available(client, clear_app_env):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    payload = response.json()
    assert "openapi" in payload
    assert "paths" in payload


def test_development_redoc_available(client, clear_app_env):
    response = client.get("/redoc")
    assert response.status_code == 200


def test_development_resolve_keeps_docs_urls(clear_app_env):
    kwargs = resolve_openapi_docs_kwargs()
    assert kwargs == {
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
    }


def test_production_docs_unavailable(clear_app_env, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    kwargs = resolve_openapi_docs_kwargs()
    assert kwargs["docs_url"] is None
    assert kwargs["redoc_url"] is None
    assert kwargs["openapi_url"] is None

    mini = FastAPI(**kwargs)
    with TestClient(mini) as prod_client:
        assert prod_client.get("/docs").status_code == 404
        assert prod_client.get("/openapi.json").status_code == 404
        assert prod_client.get("/redoc").status_code == 404


def test_production_environment_alias_disables_docs(clear_app_env, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    kwargs = resolve_openapi_docs_kwargs()
    assert kwargs["docs_url"] is None
    assert kwargs["openapi_url"] is None
    assert kwargs["redoc_url"] is None

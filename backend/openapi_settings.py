"""
OpenAPI / docs route exposure (APP_ENV-aware).

Development keeps /docs, /redoc, and /openapi.json.
Production disables all three public documentation endpoints.
"""

from __future__ import annotations

from typing import Any

from jwt_settings import is_production_env


def resolve_openapi_docs_kwargs() -> dict[str, Any]:
    """
    Keyword arguments for FastAPI docs_url / redoc_url / openapi_url.

    Setting a URL to None removes that route (clients receive 404).
    """
    if is_production_env():
        return {
            "docs_url": None,
            "redoc_url": None,
            "openapi_url": None,
        }
    return {
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
    }

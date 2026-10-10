"""
Production uvicorn bind/process settings.

Development continues to use: uvicorn main:app --reload --port 8001

Production uses the run_production entrypoint (no --reload). Host is 0.0.0.0;
PORT and WEB_CONCURRENCY are environment-driven with conservative defaults.
"""

from __future__ import annotations

import os
from typing import Any

DEFAULT_PRODUCTION_HOST = "0.0.0.0"
DEFAULT_PORT = 8001
DEFAULT_WORKERS = 1

INVALID_PORT_ERROR = "PORT must be a valid integer between 1 and 65535."
INVALID_WORKERS_ERROR = "WEB_CONCURRENCY must be a positive integer."


def resolve_port(raw: str | None = None) -> int:
    """
    Resolve listen port from PORT (or the provided raw value).

    Defaults to 8001 when unset/empty.
    """
    value = os.getenv("PORT") if raw is None else raw
    if value is None or not str(value).strip():
        return DEFAULT_PORT

    try:
        port = int(str(value).strip())
    except (TypeError, ValueError):
        raise RuntimeError(INVALID_PORT_ERROR) from None

    if port < 1 or port > 65535:
        raise RuntimeError(INVALID_PORT_ERROR)

    return port


def resolve_workers(raw: str | None = None) -> int:
    """
    Resolve worker count from WEB_CONCURRENCY (or the provided raw value).

    Defaults to 1 (conservative; suitable for in-process model load).
    """
    value = os.getenv("WEB_CONCURRENCY") if raw is None else raw
    if value is None or not str(value).strip():
        return DEFAULT_WORKERS

    try:
        workers = int(str(value).strip())
    except (TypeError, ValueError):
        raise RuntimeError(INVALID_WORKERS_ERROR) from None

    if workers < 1:
        raise RuntimeError(INVALID_WORKERS_ERROR)

    return workers


def production_reload_enabled() -> bool:
    """Production entrypoint never enables reload."""
    return False


def build_production_uvicorn_kwargs() -> dict[str, Any]:
    """
    Keyword arguments for uvicorn.run / Config in production.

    Always sets reload=False. Does not print or embed secrets.
    Existing SECRET_KEY / DATABASE_URL / CORS checks remain in their modules.
    """
    return {
        "app": "main:app",
        "host": DEFAULT_PRODUCTION_HOST,
        "port": resolve_port(),
        "workers": resolve_workers(),
        "reload": production_reload_enabled(),
    }

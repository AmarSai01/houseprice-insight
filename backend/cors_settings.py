"""
CORS origin resolution (APP_ENV-aware).

Development may use the existing localhost defaults when CORS_ORIGINS is unset.
Production must configure CORS_ORIGINS explicitly (no wildcard with credentials).
"""

from __future__ import annotations

import os
from typing import List

from jwt_settings import is_production_env

DEFAULT_DEV_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:5173",
]

PRODUCTION_CORS_ERROR = (
    "CORS_ORIGINS must be configured with explicit frontend origin(s) in production."
)

WILDCARD_CORS_ERROR = (
    "CORS_ORIGINS cannot include '*' when credentials are enabled."
)


def parse_cors_origins(raw: str | None) -> List[str]:
    """
    Parse a comma-separated CORS_ORIGINS value.

    Trims whitespace, drops empty entries, and rejects wildcard '*'.
    """
    if raw is None:
        return []

    origins: List[str] = []
    for part in str(raw).split(","):
        origin = part.strip()
        if not origin:
            continue
        if origin == "*":
            raise RuntimeError(WILDCARD_CORS_ERROR)
        origins.append(origin)
    return origins


def resolve_cors_origins() -> List[str]:
    """
    Resolve allowed CORS origins from the environment.

    Raises RuntimeError in production when CORS_ORIGINS is missing/empty,
    or whenever a wildcard origin is supplied.
    """
    raw = os.getenv("CORS_ORIGINS")
    configured = parse_cors_origins(raw)

    if is_production_env():
        if not configured:
            raise RuntimeError(PRODUCTION_CORS_ERROR)
        return configured

    if configured:
        return configured
    return list(DEFAULT_DEV_ORIGINS)


CORS_ORIGINS = resolve_cors_origins()
ALLOW_CREDENTIALS = True

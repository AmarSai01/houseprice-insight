"""
PostgreSQL-only DATABASE_URL resolution.

SQLite is not supported. DATABASE_URL must be set explicitly in every environment.
Error messages never include credentials.
"""

from __future__ import annotations

import os
from urllib.parse import unquote, urlparse

MISSING_DATABASE_URL_ERROR = "DATABASE_URL must be configured with a PostgreSQL URL."
UNSUPPORTED_DATABASE_URL_ERROR = (
    "DATABASE_URL must use PostgreSQL (postgresql+psycopg://...). "
    "SQLite and other databases are not supported."
)
INVALID_DATABASE_URL_ERROR = "DATABASE_URL is not a valid PostgreSQL URL."

# Schemes accepted by SQLAlchemy + psycopg v3.
_ALLOWED_SCHEMES = frozenset({"postgresql+psycopg", "postgresql", "postgres"})


def _safe_urlparse(raw: str):
    """Parse a URL without raising credential-bearing messages."""
    try:
        return urlparse(raw)
    except Exception:
        raise RuntimeError(INVALID_DATABASE_URL_ERROR) from None


def database_name_from_url(database_url: str) -> str:
    """Return the database name from a SQLAlchemy URL path (no credentials)."""
    parsed = _safe_urlparse(database_url.strip())
    path = (parsed.path or "").lstrip("/")
    if not path:
        return ""
    return unquote(path.split("/", 1)[0].strip())


def is_sqlite_url(database_url: str) -> bool:
    """Return True when the URL targets SQLite (unsupported)."""
    if database_url is None:
        return False
    normalized = str(database_url).strip().lower()
    if not normalized:
        return False
    if normalized.startswith("sqlite:"):
        return True
    scheme = (_safe_urlparse(normalized).scheme or "").lower()
    return scheme.startswith("sqlite")


def is_postgres_url(database_url: str) -> bool:
    """Return True when the URL uses an accepted PostgreSQL / psycopg v3 scheme."""
    if database_url is None:
        return False
    raw = str(database_url).strip()
    if not raw:
        return False
    scheme = (_safe_urlparse(raw).scheme or "").lower()
    return scheme in _ALLOWED_SCHEMES


def normalize_postgres_url(database_url: str) -> str:
    """
    Normalize accepted PostgreSQL URLs to the psycopg v3 SQLAlchemy dialect.

    postgresql:// and postgres:// become postgresql+psycopg://.
    """
    raw = str(database_url).strip()
    parsed = _safe_urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise RuntimeError(UNSUPPORTED_DATABASE_URL_ERROR)
    if scheme == "postgresql+psycopg":
        return raw
    rest = raw.split(":", 1)[1]
    if rest.startswith("//"):
        return f"postgresql+psycopg:{rest}"
    return f"postgresql+psycopg:{rest}"


def validate_postgres_database_url(raw: str | None) -> str:
    """
    Validate and normalize a PostgreSQL application DATABASE_URL.

    Raises RuntimeError with credential-free messages on failure.
    """
    if raw is None or not str(raw).strip():
        raise RuntimeError(MISSING_DATABASE_URL_ERROR)

    candidate = str(raw).strip()

    if is_sqlite_url(candidate):
        raise RuntimeError(UNSUPPORTED_DATABASE_URL_ERROR)

    if not is_postgres_url(candidate):
        raise RuntimeError(UNSUPPORTED_DATABASE_URL_ERROR)

    normalized = normalize_postgres_url(candidate)
    if not database_name_from_url(normalized):
        raise RuntimeError(INVALID_DATABASE_URL_ERROR)

    return normalized


def resolve_database_url() -> str:
    """
    Resolve DATABASE_URL from the environment.

    Required in all environments. No SQLite fallback.
    """
    return validate_postgres_database_url(os.getenv("DATABASE_URL"))

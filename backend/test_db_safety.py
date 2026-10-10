"""
Fail-closed guards for the automated test database.

Tests must use TEST_DATABASE_URL pointing at exactly houseprice_test.
Never falls back to DATABASE_URL. Never prints credentials.
"""

from __future__ import annotations

import os

from database_settings import (
    database_name_from_url,
    validate_postgres_database_url,
)

TEST_DATABASE_NAME = "houseprice_test"

MISSING_TEST_DATABASE_URL_ERROR = (
    "TEST_DATABASE_URL must be configured for automated tests "
    f"and must point at the {TEST_DATABASE_NAME} database."
)
UNSAFE_TEST_DATABASE_URL_ERROR = (
    f"TEST_DATABASE_URL must point at the dedicated {TEST_DATABASE_NAME} database. "
    "Development, production, and other databases are not allowed for tests."
)

# Explicit denylist in addition to the exact-name allow rule.
_FORBIDDEN_TEST_DATABASE_NAMES = frozenset(
    {
        "houseprice_dev",
        "houseprice_prod",
        "postgres",
        "template0",
        "template1",
    }
)


def validate_test_database_url(raw: str | None = None) -> str:
    """
    Validate TEST_DATABASE_URL for pytest.

    - Requires an explicit value (never reads DATABASE_URL as fallback).
    - Must be PostgreSQL (psycopg v3 compatible).
    - Database name must equal exactly houseprice_test.
    """
    if raw is None:
        raw = os.getenv("TEST_DATABASE_URL")

    if raw is None or not str(raw).strip():
        raise RuntimeError(MISSING_TEST_DATABASE_URL_ERROR)

    # Reuse Postgres validation; remap missing-url wording for the test env var.
    try:
        normalized = validate_postgres_database_url(str(raw).strip())
    except RuntimeError as exc:
        message = str(exc)
        if "DATABASE_URL must be configured" in message:
            raise RuntimeError(MISSING_TEST_DATABASE_URL_ERROR) from None
        # Keep unsupported/invalid messages credential-free as raised.
        raise

    name = database_name_from_url(normalized)
    if not name or name in _FORBIDDEN_TEST_DATABASE_NAMES or name != TEST_DATABASE_NAME:
        raise RuntimeError(UNSAFE_TEST_DATABASE_URL_ERROR)

    return normalized

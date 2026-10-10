"""
Pytest fixtures for HousePrice Insight.

FAIL-CLOSED DATABASE SAFETY:
- Requires TEST_DATABASE_URL before the application is imported.
- Accepts only PostgreSQL URLs whose database name is exactly houseprice_test.
- Never falls back to DATABASE_URL.
- Never prints credentials.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Validate the test DB URL BEFORE importing database/main (those resolve DATABASE_URL).
from test_db_safety import (  # noqa: E402
    MISSING_TEST_DATABASE_URL_ERROR,
    TEST_DATABASE_NAME,
    UNSAFE_TEST_DATABASE_URL_ERROR,
    validate_test_database_url,
)


def _read_test_database_url() -> str | None:
    """
    Resolve TEST_DATABASE_URL from the environment, or from an untracked local file.

    Never falls back to DATABASE_URL. Never prints the value.
    Optional local file (gitignored): backend/.local/test_database_url
    """
    env_value = os.getenv("TEST_DATABASE_URL")
    if env_value is not None and str(env_value).strip():
        return str(env_value).strip()

    local_file = BACKEND_DIR / ".local" / "test_database_url"
    if local_file.is_file():
        text = local_file.read_text(encoding="utf-8").strip()
        if text:
            return text
    return None


try:
    _TEST_DATABASE_URL = validate_test_database_url(_read_test_database_url())
except RuntimeError as exc:
    pytest.exit(str(exc), returncode=2)

# Point the application engine at the validated test database only.
os.environ["DATABASE_URL"] = _TEST_DATABASE_URL

from database import SessionLocal, configure_engine, get_db, init_db  # noqa: E402
from main import app  # noqa: E402
from ml.model_service import get_model_service  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

# Ensure engine/session are bound to the validated test URL (import may have raced).
configure_engine(_TEST_DATABASE_URL)
init_db()


def _override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return _TEST_DATABASE_URL


@pytest.fixture(scope="session")
def client():
    service = get_model_service()
    assert service.loaded, "Production model must be loadable for tests"
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db() -> Session:
    """SQLAlchemy session bound exclusively to houseprice_test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def valid_payload() -> dict:
    return {
        "area_type": "Super built-up  Area",
        "location": "Whitefield",
        "total_sqft": 1200,
        "bhk": 2,
        "bath": 2,
        "balcony": 1,
        "is_ready_to_move": True,
    }


# Re-export guard constants for tests that assert error messages.
__all__ = [
    "MISSING_TEST_DATABASE_URL_ERROR",
    "TEST_DATABASE_NAME",
    "UNSAFE_TEST_DATABASE_URL_ERROR",
]

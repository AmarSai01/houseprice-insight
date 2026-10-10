"""Tests for PostgreSQL-only DATABASE_URL and TEST_DATABASE_URL safety."""

from __future__ import annotations

import pytest

from database_settings import (
    INVALID_DATABASE_URL_ERROR,
    MISSING_DATABASE_URL_ERROR,
    UNSUPPORTED_DATABASE_URL_ERROR,
    database_name_from_url,
    is_postgres_url,
    is_sqlite_url,
    normalize_postgres_url,
    resolve_database_url,
    validate_postgres_database_url,
)
from test_db_safety import (
    MISSING_TEST_DATABASE_URL_ERROR,
    UNSAFE_TEST_DATABASE_URL_ERROR,
    validate_test_database_url,
)


@pytest.fixture
def clear_database_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)


def test_missing_database_url_fails(clear_database_env):
    with pytest.raises(RuntimeError) as exc:
        resolve_database_url()
    assert str(exc.value) == MISSING_DATABASE_URL_ERROR


def test_empty_database_url_fails(clear_database_env, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "   ")
    with pytest.raises(RuntimeError) as exc:
        resolve_database_url()
    assert str(exc.value) == MISSING_DATABASE_URL_ERROR


def test_sqlite_url_is_rejected(clear_database_env, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./house_prediction.db")
    with pytest.raises(RuntimeError) as exc:
        resolve_database_url()
    assert str(exc.value) == UNSUPPORTED_DATABASE_URL_ERROR
    assert "sqlite:///./house_prediction.db" not in str(exc.value)


def test_sqlite_url_rejected_in_production(clear_database_env, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:////var/data/house_prediction.db")
    with pytest.raises(RuntimeError) as exc:
        resolve_database_url()
    assert str(exc.value) == UNSUPPORTED_DATABASE_URL_ERROR


def test_valid_postgresql_psycopg_url_is_accepted(clear_database_env, monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://houseprice_app:secret@127.0.0.1:5432/houseprice_dev",
    )
    url = resolve_database_url()
    assert url.startswith("postgresql+psycopg://")
    assert database_name_from_url(url) == "houseprice_dev"
    assert "secret" not in MISSING_DATABASE_URL_ERROR


def test_postgresql_url_is_normalized_to_psycopg(clear_database_env, monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://houseprice_app:secret@127.0.0.1:5432/houseprice_dev",
    )
    url = resolve_database_url()
    assert url.startswith("postgresql+psycopg://")
    assert "houseprice_dev" in url


def test_psycopg2_url_is_rejected(clear_database_env, monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg2://user:pass@db.example:5432/houseprice",
    )
    with pytest.raises(RuntimeError) as exc:
        resolve_database_url()
    assert str(exc.value) == UNSUPPORTED_DATABASE_URL_ERROR
    assert "pass" not in str(exc.value)


def test_error_message_does_not_expose_secrets(clear_database_env, monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://secret-user:super-secret@db.example/app",
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError) as exc:
        resolve_database_url()
    message = str(exc.value)
    assert "super-secret" not in message
    assert "secret-user" not in message
    assert message == MISSING_DATABASE_URL_ERROR


def test_unsupported_url_error_does_not_echo_credentials():
    with pytest.raises(RuntimeError) as exc:
        validate_postgres_database_url(
            "mysql://secret-user:super-secret@db.example/app"
        )
    message = str(exc.value)
    assert message == UNSUPPORTED_DATABASE_URL_ERROR
    assert "super-secret" not in message
    assert "secret-user" not in message


def test_is_sqlite_and_postgres_detection():
    assert is_sqlite_url("sqlite:///./house_prediction.db") is True
    assert is_sqlite_url("SQLITE:////tmp/app.db") is True
    assert is_postgres_url("postgresql+psycopg://u@localhost/db") is True
    assert is_postgres_url("postgresql://u@localhost/db") is True
    assert is_postgres_url("sqlite:///./x.db") is False


def test_normalize_requires_database_name():
    with pytest.raises(RuntimeError) as exc:
        validate_postgres_database_url("postgresql+psycopg://localhost")
    assert str(exc.value) == INVALID_DATABASE_URL_ERROR


def test_missing_test_database_url_fails(clear_database_env):
    with pytest.raises(RuntimeError) as exc:
        validate_test_database_url(None)
    assert str(exc.value) == MISSING_TEST_DATABASE_URL_ERROR


def test_test_database_url_never_falls_back_to_database_url(
    clear_database_env, monkeypatch
):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://houseprice_app:secret@127.0.0.1:5432/houseprice_dev",
    )
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError) as exc:
        validate_test_database_url(None)
    assert str(exc.value) == MISSING_TEST_DATABASE_URL_ERROR


def test_test_database_rejects_dev_database():
    with pytest.raises(RuntimeError) as exc:
        validate_test_database_url(
            "postgresql+psycopg://houseprice_app:secret@127.0.0.1:5432/houseprice_dev"
        )
    assert str(exc.value) == UNSAFE_TEST_DATABASE_URL_ERROR
    assert "secret" not in str(exc.value)


def test_test_database_rejects_prod_database():
    with pytest.raises(RuntimeError) as exc:
        validate_test_database_url(
            "postgresql+psycopg://houseprice_app:secret@db.example:5432/houseprice_prod"
        )
    assert str(exc.value) == UNSAFE_TEST_DATABASE_URL_ERROR


def test_test_database_rejects_sqlite():
    with pytest.raises(RuntimeError) as exc:
        validate_test_database_url("sqlite:///./house_prediction.db")
    assert "sqlite:///./house_prediction.db" not in str(exc.value)


def test_test_database_accepts_houseprice_test_only():
    url = validate_test_database_url(
        "postgresql+psycopg://houseprice_app:secret@127.0.0.1:5432/houseprice_test"
    )
    assert database_name_from_url(url) == "houseprice_test"
    assert url.startswith("postgresql+psycopg://")


def test_normalize_postgres_url_helper():
    assert normalize_postgres_url(
        "postgres://u:p@localhost:5432/houseprice_dev"
    ).startswith("postgresql+psycopg://")

"""
JWT signing secret resolution (APP_ENV-aware).

Production deployments must provide a strong SECRET_KEY via environment variables.
Development/local mode may use the documented local default when unset.
"""

from __future__ import annotations

import os

INSECURE_DEFAULT_SECRET = "your-secret-key-change-in-production"

PRODUCTION_SECRET_ERROR = (
    "SECRET_KEY must be configured with a strong value in production."
)

INSECURE_PLACEHOLDER_SECRETS = frozenset(
    {
        INSECURE_DEFAULT_SECRET.lower(),
        "secret",
        "changeme",
        "your-secret-key",
        "development-secret",
    }
)


def get_application_env() -> str:
    """Match email_service / password-reset dev detection."""
    return os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower().strip()


def is_production_env(app_env: str | None = None) -> bool:
    env = app_env if app_env is not None else get_application_env()
    return env in {"production", "prod"}


def _is_insecure_secret(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return True
    return normalized in INSECURE_PLACEHOLDER_SECRETS


def resolve_jwt_secret_key() -> str:
    """
    Resolve JWT SECRET_KEY from the environment.

    Raises RuntimeError in production when the secret is missing or insecure.
    """
    if is_production_env():
        raw = os.getenv("SECRET_KEY")
        if raw is None or not str(raw).strip():
            raise RuntimeError(PRODUCTION_SECRET_ERROR)
        secret = str(raw).strip()
        if _is_insecure_secret(secret):
            raise RuntimeError(PRODUCTION_SECRET_ERROR)
        return secret

    raw = os.getenv("SECRET_KEY")
    if raw is not None and str(raw).strip():
        return str(raw).strip()
    return INSECURE_DEFAULT_SECRET


SECRET_KEY = resolve_jwt_secret_key()

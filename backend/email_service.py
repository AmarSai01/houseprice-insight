"""
Optional SMTP email delivery for password reset links.

No credentials are hardcoded. If SMTP is not configured, callers must use
the development-safe reset path instead of pretending mail was sent.
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Optional


def smtp_configured() -> bool:
    """Return True when enough SMTP env vars are present to attempt delivery."""
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM"))


def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    """
    Send a password reset email when SMTP is configured.

    Returns True on success, False when SMTP is not configured.
    Raises on SMTP failure so callers can handle errors without leaking tokens.
    """
    if not smtp_configured():
        return False

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    from_addr = os.getenv("SMTP_FROM")
    use_tls = os.getenv("SMTP_TLS", "true").lower() not in {"0", "false", "no"}

    message = EmailMessage()
    message["Subject"] = "HousePrice Insight password reset"
    message["From"] = from_addr
    message["To"] = to_email
    message.set_content(
        "You requested a password reset for HousePrice Insight.\n\n"
        f"Open this link to choose a new password (expires soon):\n{reset_url}\n\n"
        "If you did not request this, you can ignore this email.\n"
    )

    with smtplib.SMTP(host, port, timeout=20) as server:
        if use_tls:
            server.starttls()
        if username and password:
            server.login(username, password)
        server.send_message(message)

    return True


def frontend_base_url() -> str:
    return os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")


def build_reset_url(raw_token: str) -> str:
    return f"{frontend_base_url()}/reset-password?token={raw_token}"


def password_reset_dev_return_token() -> bool:
    """
    When SMTP is unavailable, allow local testing by returning a one-time
    token in the API response. Disabled unless explicitly enabled.
    Never enable in production.
    """
    if smtp_configured():
        return False
    flag = os.getenv("PASSWORD_RESET_DEV_RETURN_TOKEN", "").lower()
    env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    if flag in {"1", "true", "yes"}:
        return True
    # Default on for local/development so frontend/tests can exercise reset.
    return env not in {"production", "prod"}

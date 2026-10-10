"""Tests for forgot-password / reset-password authentication flow."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from auth import (
    get_password_hash,
    hash_reset_token,
    verify_password,
)
from datetime_utils import utc_now
from models import User, PasswordResetToken


FORGOT_MESSAGE = (
    "If an account exists for that email, a password reset link has been sent."
)


@pytest.fixture
def reset_user(db: Session):
    email = "reset_flow_user@example.com"
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == existing.id
        ).delete()
        db.delete(existing)
        db.commit()

    user = User(
        name="Reset Flow",
        email=email,
        hashed_password=get_password_hash("OldPass123"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user

    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id
    ).delete()
    db.query(User).filter(User.id == user.id).delete()
    db.commit()


def _login(client, email: str, password: str):
    return client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    )


def test_forgot_password_existing_email(client, reset_user):
    response = client.post(
        "/api/auth/forgot-password",
        json={"email": reset_user.email},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == FORGOT_MESSAGE
    assert data.get("dev_reset_token")
    assert data.get("dev_reset_url")


def test_forgot_password_unknown_email(client):
    response = client.post(
        "/api/auth/forgot-password",
        json={"email": "unknown_no_account_xyz@example.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == FORGOT_MESSAGE


def test_forgot_password_same_public_response(client, reset_user):
    known = client.post(
        "/api/auth/forgot-password",
        json={"email": reset_user.email},
    ).json()
    unknown = client.post(
        "/api/auth/forgot-password",
        json={"email": "definitely_missing_abc@example.com"},
    ).json()
    assert known["message"] == unknown["message"] == FORGOT_MESSAGE
    # Same response keys (enumeration-safe shape)
    assert set(known.keys()) == set(unknown.keys())


def test_reset_token_works(client, reset_user):
    forgot = client.post(
        "/api/auth/forgot-password",
        json={"email": reset_user.email},
    ).json()
    token = forgot["dev_reset_token"]

    reset = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "NewPass456"},
    )
    assert reset.status_code == 200
    assert "successfully" in reset.json()["message"].lower()


def test_expired_token_rejected(client, reset_user, db: Session):
    forgot = client.post(
        "/api/auth/forgot-password",
        json={"email": reset_user.email},
    ).json()
    token = forgot["dev_reset_token"]

    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == hash_reset_token(token))
        .first()
    )
    assert row is not None
    row.expires_at = utc_now() - timedelta(minutes=5)
    db.commit()

    response = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "NewPass456"},
    )
    assert response.status_code == 400
    assert "invalid or expired" in response.json()["detail"].lower()


def test_invalid_token_rejected(client):
    response = client.post(
        "/api/auth/reset-password",
        json={"token": "not-a-real-token-value", "new_password": "NewPass456"},
    )
    assert response.status_code == 400


def test_token_cannot_be_reused(client, reset_user):
    forgot = client.post(
        "/api/auth/forgot-password",
        json={"email": reset_user.email},
    ).json()
    token = forgot["dev_reset_token"]

    first = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "NewPass456"},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "AnotherPass789"},
    )
    assert second.status_code == 400


def test_new_password_is_bcrypt_hashed(client, reset_user, db: Session):
    forgot = client.post(
        "/api/auth/forgot-password",
        json={"email": reset_user.email},
    ).json()
    client.post(
        "/api/auth/reset-password",
        json={"token": forgot["dev_reset_token"], "new_password": "NewPass456"},
    )

    db.expire_all()
    user = db.query(User).filter(User.id == reset_user.id).first()
    assert user.hashed_password.startswith("$2")
    assert verify_password("NewPass456", user.hashed_password)


def test_old_password_no_longer_works(client, reset_user):
    forgot = client.post(
        "/api/auth/forgot-password",
        json={"email": reset_user.email},
    ).json()
    client.post(
        "/api/auth/reset-password",
        json={"token": forgot["dev_reset_token"], "new_password": "NewPass456"},
    )

    assert _login(client, reset_user.email, "OldPass123").status_code == 401


def test_new_password_works(client, reset_user):
    forgot = client.post(
        "/api/auth/forgot-password",
        json={"email": reset_user.email},
    ).json()
    client.post(
        "/api/auth/reset-password",
        json={"token": forgot["dev_reset_token"], "new_password": "NewPass456"},
    )

    login = _login(client, reset_user.email, "NewPass456")
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_existing_login_still_works(client, reset_user):
    # Before any reset, original password still authenticates.
    login = _login(client, reset_user.email, "OldPass123")
    assert login.status_code == 200
    assert login.json()["user"]["email"] == reset_user.email


def test_existing_user_not_modified_on_forgot(client, reset_user, db: Session):
    before = reset_user.hashed_password
    client.post(
        "/api/auth/forgot-password",
        json={"email": reset_user.email},
    )
    db.expire_all()
    after = db.query(User).filter(User.id == reset_user.id).first()
    assert after.hashed_password == before
    assert after.email == reset_user.email
    assert after.name == reset_user.name

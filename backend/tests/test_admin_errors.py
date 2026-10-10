"""Tests for admin error safety (no filesystem path leakage)."""

from __future__ import annotations

import uuid

import pytest

from auth import get_password_hash
from database import SessionLocal
from models import User


def _unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _create_user(email: str, password: str, role: str = "user") -> User:
    db = SessionLocal()
    try:
        user = User(
            name="Admin Test",
            email=email,
            hashed_password=get_password_hash(password),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _delete_user(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.delete(user)
            db.commit()
    finally:
        db.close()


def _login_headers(client, email: str, password: str) -> dict[str, str]:
    login = client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_user(client):
    email = _unique_email("admin_err")
    password = "AdminPass123"
    _create_user(email, password, role="admin")
    try:
        yield {"email": email, "password": password}
    finally:
        _delete_user(email)


@pytest.fixture
def regular_user(client):
    email = _unique_email("user_err")
    password = "UserPass123"
    _create_user(email, password, role="user")
    try:
        yield {"email": email, "password": password}
    finally:
        _delete_user(email)


def test_admin_missing_dataset_does_not_leak_path(client, admin_user, tmp_path):
    headers = _login_headers(client, admin_user["email"], admin_user["password"])
    missing = tmp_path / "definitely_missing_house_data.csv"
    assert not missing.exists()

    response = client.post(
        "/api/admin/retrain",
        json={"csv_path": str(missing)},
        headers=headers,
    )
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail == "Dataset file could not be processed."
    assert str(missing) not in detail
    assert "house_data.csv" not in detail
    assert ":" not in detail  # no Windows drive / path separators in message
    assert "/" not in detail
    assert "\\" not in detail


def test_admin_retrain_success_unchanged(client, admin_user, tmp_path, monkeypatch):
    headers = _login_headers(client, admin_user["email"], admin_user["password"])
    csv_path = tmp_path / "ok_dataset.csv"
    csv_path.write_text("col\n1\n", encoding="utf-8")

    monkeypatch.setattr("routes.admin.train_model", lambda path: None)

    response = client.post(
        "/api/admin/retrain",
        json={"csv_path": str(csv_path)},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "retraining" in body["message"].lower()
    assert str(csv_path) not in response.text


def test_admin_auth_required_for_retrain(client, tmp_path):
    missing = tmp_path / "nope.csv"
    response = client.post(
        "/api/admin/retrain",
        json={"csv_path": str(missing)},
    )
    assert response.status_code == 401


def test_non_admin_forbidden_for_retrain(client, regular_user, tmp_path):
    headers = _login_headers(
        client, regular_user["email"], regular_user["password"]
    )
    missing = tmp_path / "nope.csv"
    response = client.post(
        "/api/admin/retrain",
        json={"csv_path": str(missing)},
        headers=headers,
    )
    assert response.status_code == 403

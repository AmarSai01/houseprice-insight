"""
Authentication utilities: password hashing, JWT token generation/verification,
and password-reset token helpers.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
import hashlib
import secrets
import os

import jwt
from jwt import PyJWTError
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from models import User, PasswordResetToken
from database import get_db
from jwt_settings import SECRET_KEY
from datetime_utils import as_utc, utc_now

# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Shared password rules (register + reset)
MIN_PASSWORD_LENGTH = 8
PASSWORD_RESET_EXPIRE_MINUTES = int(os.getenv("PASSWORD_RESET_EXPIRE_MINUTES", "30"))

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="api/auth/login",
    auto_error=False,
)


def _password_to_bytes(password: str) -> bytes:
    """Encode password to UTF-8 bytes, truncating to bcrypt's 72-byte limit."""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    return password_bytes


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash (including existing $2b$ hashes)."""
    try:
        return bcrypt.checkpw(
            _password_to_bytes(plain_password),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    """Hash a password with bcrypt ($2b$ hashes, compatible with existing DB values)."""
    hashed = bcrypt.hashpw(_password_to_bytes(password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def validate_password_strength(password: str) -> Optional[str]:
    """Return an error message if password fails shared rules, else None."""
    if password is None or not str(password).strip():
        return "Password is required"
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    return None


def hash_reset_token(raw_token: str) -> str:
    """Store only SHA-256 hashes of reset tokens (never the plaintext token)."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_password_reset_token(db: Session, user: User) -> str:
    """
    Create a cryptographically secure single-use reset token for the user.
    Invalidates prior unused tokens for that user. Returns the raw token once.
    """
    # Invalidate outstanding unused tokens for this user.
    now = utc_now()
    outstanding = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .all()
    )
    for row in outstanding:
        row.used_at = now

    raw_token = secrets.token_urlsafe(32)
    record = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(raw_token),
        expires_at=now + timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES),
        used_at=None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return raw_token


def get_valid_reset_token(
    db: Session, raw_token: str
) -> Tuple[Optional[PasswordResetToken], Optional[str]]:
    """
    Look up a usable reset token by plaintext value.
    Returns (record, error_message). error_message is set when invalid/expired/used.
    """
    if not raw_token or not str(raw_token).strip():
        return None, "Invalid or expired reset token"

    token_hash = hash_reset_token(raw_token.strip())
    record = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash)
        .first()
    )
    if record is None:
        return None, "Invalid or expired reset token"
    if record.used_at is not None:
        return None, "Invalid or expired reset token"

    expires_at = as_utc(record.expires_at)
    if expires_at < utc_now():
        return None, "Invalid or expired reset token"

    return record, None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    # JWT 'sub' must be a string (PyJWT validates it as a string claim).
    if "sub" in to_encode and to_encode["sub"] is not None:
        to_encode["sub"] = str(to_encode["sub"])
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exception
        user_id = int(subject)
    except (PyJWTError, TypeError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user


def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current user and verify they are an admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Return the authenticated user when a valid Bearer token is present."""
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if subject is None:
            return None
        user_id = int(subject)
    except (PyJWTError, TypeError, ValueError):
        return None

    return db.query(User).filter(User.id == user_id).first()





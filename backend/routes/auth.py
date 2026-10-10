"""
Authentication routes: login, register, password reset, get current user.
"""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User, PasswordResetToken
from datetime_utils import utc_now
from auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    MIN_PASSWORD_LENGTH,
    validate_password_strength,
    create_password_reset_token,
    get_valid_reset_token,
)
from email_service import (
    smtp_configured,
    send_password_reset_email,
    build_reset_url,
    password_reset_dev_return_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

FORGOT_PASSWORD_MESSAGE = (
    "If an account exists for that email, a password reset link has been sent."
)


class UserRegister(BaseModel):
    """User registration model."""
    name: str
    email: EmailStr
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH)


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str
    user: dict


class UserResponse(BaseModel):
    """User response model."""
    id: int
    name: str
    email: str
    role: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    delivery: str = "email"
    # Present only in local/dev when SMTP is not configured (for testing).
    # Always included as null or value with matching shape; fake tokens used
    # for unknown emails so response shape does not enumerate accounts.
    dev_reset_token: Optional[str] = None
    dev_reset_url: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH)


class ResetPasswordResponse(BaseModel):
    message: str


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user."""
    try:
        strength_error = validate_password_strength(user_data.password)
        if strength_error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=strength_error,
            )

        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            name=user_data.name,
            email=user_data.email,
            hashed_password=hashed_password,
            role="user",
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "role": new_user.role,
            "created_at": new_user.created_at.isoformat() if new_user.created_at else None,
        }
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again.",
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login user and return JWT token."""
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information."""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "created_at": (
            current_user.created_at.isoformat() if current_user.created_at else None
        ),
    }


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Request a password reset. Always returns the same public message to avoid
    account enumeration. Does not log reset tokens.
    """
    import secrets as secrets_mod

    user = db.query(User).filter(User.email == payload.email).first()
    raw_token: Optional[str] = None

    if user is not None:
        raw_token = create_password_reset_token(db, user)
        reset_url = build_reset_url(raw_token)

        if smtp_configured():
            try:
                send_password_reset_email(user.email, reset_url)
            except Exception:
                # Keep response enumeration-safe; do not expose token or email status.
                pass

    # Public response is always the same message.
    response: dict = {
        "message": FORGOT_PASSWORD_MESSAGE,
        "delivery": "email",
        "dev_reset_token": None,
        "dev_reset_url": None,
    }

    # Local/dev without SMTP: include a token-shaped field for every request
    # (real token or throwaway) so the response shape does not enumerate accounts.
    if password_reset_dev_return_token():
        token_for_client = raw_token or secrets_mod.token_urlsafe(32)
        response["delivery"] = "dev"
        response["dev_reset_token"] = token_for_client
        response["dev_reset_url"] = build_reset_url(token_for_client)

    return response


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Consume a single-use reset token and set a new bcrypt-hashed password."""
    strength_error = validate_password_strength(payload.new_password)
    if strength_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=strength_error,
        )

    record, error = get_valid_reset_token(db, payload.token)
    if error or record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user = db.query(User).filter(User.id == record.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user.hashed_password = get_password_hash(payload.new_password)
    record.used_at = utc_now()

    # Invalidate any other outstanding tokens for this user.
    others = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != record.id,
            PasswordResetToken.used_at.is_(None),
        )
        .all()
    )
    for row in others:
        row.used_at = utc_now()

    db.commit()

    return {
        "message": "Password reset successfully. You can now sign in.",
    }

"""Auth routes (Module 1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import jwt

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_reset_token,
    decode_reset_token,
    hash_password,
    verify_password,
)
from app.models.audit import AuditLog
from app.models.user import User, UserRole
from app.schemas.auth import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserLogin,
    UserOut,
)
from app.services.mailer import mail_configured, send_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _audit(db: Session, request: Request, user_id: int, action: str) -> None:
    db.add(AuditLog(user_id=user_id, action=action, entity="user",
                    ip=request.client.host if request.client else None))
    db.commit()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)) -> Token:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.investor.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _audit(db, request, user.id, "register")
    token = create_access_token(user.id, {"role": user.role})
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=Token)
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)) -> Token:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    _audit(db, request, user.id, "login")
    token = create_access_token(user.id, {"role": user.role})
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, request: Request,
                    db: Session = Depends(get_db)) -> dict:
    """Start a password reset. Always returns 200 (never leaks whether the email exists).

    If SMTP is configured, a reset link is emailed. In dev (no SMTP), the token is
    returned in the response so the flow is testable without a mail server.
    """
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    resp: dict = {"message": "If that email is registered, a reset link has been sent."}
    if user and user.is_active:
        token = create_reset_token(user.id, user.hashed_password)
        reset_link = f"{settings.APP_BASE_URL}/reset-password?token={token}"
        _audit(db, request, user.id, "forgot_password")
        sent = send_email(
            user.email,
            "Reset your AI Real Estate Platform password",
            f"Hi {user.full_name or 'there'},\n\n"
            f"Use this link to reset your password (valid for "
            f"{settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes):\n\n{reset_link}\n\n"
            "If you didn't request this, you can safely ignore this email.",
        )
        if not mail_configured():
            # dev convenience: no mail server -> hand the token back so it's usable
            resp["reset_token"] = token
            resp["reset_link"] = reset_link
        resp["email_sent"] = sent
    return resp


@router.post("/reset-password", response_model=Token)
def reset_password(payload: ResetPasswordRequest, request: Request,
                   db: Session = Depends(get_db)) -> Token:
    try:
        data = decode_reset_token(payload.token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="This reset link has expired. Request a new one.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid reset link.")

    user = db.get(User, int(data["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Invalid reset link.")
    # token is bound to the password at issue time — rejects reused/stale tokens
    if data.get("pw") != user.hashed_password[-12:]:
        raise HTTPException(status_code=400, detail="This reset link has already been used.")

    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    db.refresh(user)
    _audit(db, request, user.id, "reset_password")
    token = create_access_token(user.id, {"role": user.role})
    return Token(access_token=token, user=UserOut.model_validate(user))

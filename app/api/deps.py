"""Shared API dependencies: auth + role guards."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTH = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated",
                        headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _UNAUTH
    try:
        payload = decode_token(credentials.credentials)
        user_id = int(payload["sub"])
    except Exception:  # noqa: BLE001
        raise _UNAUTH
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _UNAUTH
    return user


def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.is_superuser or user.role in roles:
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return dependency

"""Admin Panel routes — admin role required for all endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.engagement import Favorite, SavedSearch
from app.models.portfolio import PortfolioHolding
from app.models.property import Property
from app.models.user import User
from app.schemas.auth import UserOut

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_roles("admin"))])


class UserPatch(BaseModel):
    role: str | None = None
    is_active: bool | None = None


def _count(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


@router.get("/stats")
def stats(db: Session = Depends(get_db)) -> dict:
    return {
        "users": _count(db, User),
        "properties": _count(db, Property),
        "favorites": _count(db, Favorite),
        "saved_searches": _count(db, SavedSearch),
        "portfolio_holdings": _count(db, PortfolioHolding),
        "audit_logs": _count(db, AuditLog),
    }


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[UserOut]:
    rows = db.scalars(select(User).order_by(User.id)).all()
    return [UserOut.model_validate(u) for u in rows]


@router.patch("/users/{user_id}", response_model=UserOut)
def patch_user(user_id: int, body: UserPatch, db: Session = Depends(get_db)) -> UserOut:
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if body.role is not None:
        if body.role not in {"admin", "investor", "agent", "guest"}:
            raise HTTPException(status_code=422, detail="Invalid role")
        u.role = body.role
    if body.is_active is not None:
        u.is_active = body.is_active
    db.commit()
    db.refresh(u)
    return UserOut.model_validate(u)

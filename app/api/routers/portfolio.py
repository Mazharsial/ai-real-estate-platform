"""Portfolio Manager routes (Module 14) — requires authentication."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.portfolio import PortfolioHolding
from app.models.user import User
from app.schemas.portfolio import HoldingCreate, HoldingOut
from app.services.portfolio import portfolio_summary

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


def _holding_dict(h: PortfolioHolding) -> dict:
    return {c.name: getattr(h, c.name) for c in PortfolioHolding.__table__.columns}


@router.get("")
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(
        select(PortfolioHolding).where(PortfolioHolding.user_id == user.id).order_by(PortfolioHolding.id.desc())
    ).all()
    return portfolio_summary([_holding_dict(h) for h in rows])


@router.post("", response_model=HoldingOut, status_code=status.HTTP_201_CREATED)
def add(payload: HoldingCreate, user: User = Depends(get_current_user),
        db: Session = Depends(get_db)) -> HoldingOut:
    h = PortfolioHolding(user_id=user.id, **payload.model_dump())
    db.add(h)
    db.commit()
    db.refresh(h)
    return HoldingOut.model_validate(h)


@router.put("/{holding_id}", response_model=HoldingOut)
def update(holding_id: int, payload: HoldingCreate, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)) -> HoldingOut:
    h = db.get(PortfolioHolding, holding_id)
    if not h or h.user_id != user.id:
        raise HTTPException(status_code=404, detail="Holding not found")
    for k, v in payload.model_dump().items():
        setattr(h, k, v)
    db.commit()
    db.refresh(h)
    return HoldingOut.model_validate(h)


@router.delete("/{holding_id}")
def delete(holding_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    h = db.get(PortfolioHolding, holding_id)
    if not h or h.user_id != user.id:
        raise HTTPException(status_code=404, detail="Holding not found")
    db.delete(h)
    db.commit()
    return {"deleted": True, "id": holding_id}

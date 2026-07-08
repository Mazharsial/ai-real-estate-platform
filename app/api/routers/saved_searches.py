"""Saved Searches (Module 11) — requires authentication."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.engagement import SavedSearch
from app.models.user import User
from app.schemas.engagement import SavedSearchCreate, SavedSearchOut

router = APIRouter(prefix="/api/saved-searches", tags=["saved-searches"])


@router.get("", response_model=list[SavedSearchOut])
def my_searches(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[SavedSearchOut]:
    rows = db.scalars(
        select(SavedSearch).where(SavedSearch.user_id == user.id).order_by(SavedSearch.id.desc())
    ).all()
    return [SavedSearchOut.model_validate(r) for r in rows]


@router.post("", response_model=SavedSearchOut, status_code=status.HTTP_201_CREATED)
def create(payload: SavedSearchCreate, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)) -> SavedSearchOut:
    obj = SavedSearch(user_id=user.id, name=payload.name, filters=payload.filters,
                      alert_enabled=1 if payload.alert_enabled else 0)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return SavedSearchOut.model_validate(obj)


@router.delete("/{search_id}")
def delete(search_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    obj = db.get(SavedSearch, search_id)
    if not obj or obj.user_id != user.id:
        raise HTTPException(status_code=404, detail="Saved search not found")
    db.delete(obj)
    db.commit()
    return {"deleted": True, "id": search_id}

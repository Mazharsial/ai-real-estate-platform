"""Favorites (Module 11) — requires authentication."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.engagement import Favorite
from app.models.property import Property
from app.models.user import User
from app.schemas.property import PropertyOut
from app.services.property_service import property_to_dict

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.get("", response_model=list[PropertyOut])
def my_favorites(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[PropertyOut]:
    stmt = (
        select(Property)
        .join(Favorite, Favorite.property_id == Property.id)
        .where(Favorite.user_id == user.id)
    )
    rows = db.scalars(stmt).all()
    return [PropertyOut.model_validate(property_to_dict(r)) for r in rows]


@router.post("/{property_id}", status_code=status.HTTP_201_CREATED)
def add_favorite(property_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if not db.get(Property, property_id):
        raise HTTPException(status_code=404, detail="Property not found")
    exists = db.scalar(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.property_id == property_id)
    )
    if not exists:
        db.add(Favorite(user_id=user.id, property_id=property_id))
        db.commit()
    return {"favorited": True, "property_id": property_id}


@router.delete("/{property_id}")
def remove_favorite(property_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    fav = db.scalar(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.property_id == property_id)
    )
    if fav:
        db.delete(fav)
        db.commit()
    return {"favorited": False, "property_id": property_id}

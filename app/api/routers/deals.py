"""Deal Finder routes (Module 9)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.deal_finder import find_deals
from app.services.property_service import list_properties, property_to_dict, run_search

router = APIRouter(prefix="/api/deals", tags=["deals"])


def _property_set(db: Session, city: str | None) -> list[dict]:
    rows = list_properties(db, city=city, limit=200)
    if not rows:
        run_search(db, {"city": city} if city else {})
        rows = list_properties(db, city=city, limit=200)
    return [property_to_dict(r) for r in rows]


@router.get("")
def deals(db: Session = Depends(get_db), city: str | None = None, top_n: int = Query(6, le=20)) -> dict:
    return find_deals(_property_set(db, city), top_n=top_n)

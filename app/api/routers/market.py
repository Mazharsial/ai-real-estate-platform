"""Market Analysis routes (Module 7)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.market import market_overview
from app.services.property_service import list_properties, property_to_dict, run_search

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), city: str | None = None) -> dict:
    rows = list_properties(db, city=city, limit=300)
    if not rows:
        run_search(db, {"city": city} if city else {})
        rows = list_properties(db, city=city, limit=300)
    props = [property_to_dict(r) for r in rows]
    return market_overview(props, city=city)

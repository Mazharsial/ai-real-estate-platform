"""Analytics dashboard routes (Module 13)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.analytics import analytics_summary
from app.services.property_service import list_properties, property_to_dict, run_search

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), city: str | None = None) -> dict:
    rows = list_properties(db, city=city, limit=300)
    if not rows:
        run_search(db, {"city": city} if city else {})
        rows = list_properties(db, city=city, limit=300)
    return analytics_summary([property_to_dict(r) for r in rows])

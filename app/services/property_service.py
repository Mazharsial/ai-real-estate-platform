"""Property orchestration: fetch -> analyze -> persist -> query (Repository pattern)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.property import Property
from app.services.analysis import analyze_properties, full_financials, investment_score, score_reasons
from app.services.data_sources import fetch_properties

# Columns we persist from an analyzed dict
_PERSIST_COLS = [
    "source", "external_id", "title", "address", "city", "state", "zip", "lat", "lng",
    "price", "beds", "baths", "sqft", "lot_size", "property_type", "year_built",
    "days_on_market", "hoa", "taxes", "description", "image_url", "agent_name", "agent_phone",
    "school_rating", "crime_score", "appreciation_trend", "price_per_sqft", "rent_estimate",
    "rental_yield", "neighborhood_avg_ppsf", "undervalued_pct", "investment_score",
    "predicted_value_3yr", "price_history", "ai_summary",
]


def property_to_dict(p: Property) -> dict[str, Any]:
    return {c: getattr(p, c) for c in ["id", *_PERSIST_COLS, "created_at", "updated_at"] if hasattr(p, c)}


def upsert_property(db: Session, data: dict) -> Property:
    obj = db.scalar(select(Property).where(Property.external_id == data["external_id"]))
    if obj is None:
        obj = Property(external_id=data["external_id"])
        db.add(obj)
    for col in _PERSIST_COLS:
        if col == "external_id":
            continue
        if col in data and data[col] is not None:
            setattr(obj, col, data[col])
    return obj


def run_search(db: Session, criteria: dict | None = None) -> dict:
    """Full pipeline. Returns source, note, count, and ranked property dicts."""
    result = fetch_properties(criteria or {})
    analyzed = analyze_properties(result["properties"])
    objs = [upsert_property(db, p) for p in analyzed]
    db.commit()
    for o in objs:
        db.refresh(o)
    props = sorted((property_to_dict(o) for o in objs), key=lambda x: x["investment_score"], reverse=True)
    return {
        "source": result["source"],
        "note": result.get("note"),
        "count": len(props),
        "properties": props,
    }


def list_properties(db: Session, city: str | None = None, min_score: int = 0,
                    limit: int = 60, offset: int = 0) -> list[Property]:
    stmt = select(Property).where(Property.investment_score >= min_score)
    if city:
        stmt = stmt.where(Property.city.ilike(city))
    stmt = stmt.order_by(Property.investment_score.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def get_property(db: Session, property_id: int) -> Property | None:
    return db.get(Property, property_id)


def analyze_one(p: Property, assumptions: dict | None = None) -> dict:
    """Return the full analysis bundle for a single property (Modules 5 & 6)."""
    d = property_to_dict(p)
    return {
        "property": d,
        "score": investment_score(d),
        "reasons": score_reasons(d),
        "financials": full_financials(d, assumptions),
    }

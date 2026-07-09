"""Property discovery, analysis & AI advice (Modules 2, 5, 6, 8)."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.property import AnalyzeRequest, PropertyOut, SearchCriteria, SearchResult
from app.services.ai.advisor import investment_advice
from app.services.geo import nearby_amenities
from app.services.reports import build_property_report
from app.services.property_service import (
    analyze_one,
    get_property,
    list_properties,
    property_to_dict,
    run_search,
)

router = APIRouter(prefix="/api/properties", tags=["properties"])


@router.post("/search", response_model=SearchResult)
def search(criteria: SearchCriteria, db: Session = Depends(get_db)) -> SearchResult:
    result = run_search(db, criteria.model_dump(exclude_none=True))
    return SearchResult(**result)


@router.get("", response_model=list[PropertyOut])
def list_all(
    db: Session = Depends(get_db),
    city: str | None = None,
    min_score: int = 0,
    limit: int = Query(60, le=200),
    offset: int = 0,
) -> list[PropertyOut]:
    rows = list_properties(db, city=city, min_score=min_score, limit=limit, offset=offset)
    if not rows:  # auto-seed on first call so the app is never empty
        run_search(db, {})
        rows = list_properties(db, city=city, min_score=min_score, limit=limit, offset=offset)
    return [PropertyOut.model_validate(property_to_dict(r)) for r in rows]


@router.get("/{property_id}", response_model=PropertyOut)
def detail(property_id: int, db: Session = Depends(get_db)) -> PropertyOut:
    p = get_property(db, property_id)
    if not p:
        raise HTTPException(status_code=404, detail="Property not found")
    return PropertyOut.model_validate(property_to_dict(p))


@router.post("/{property_id}/analyze")
def analyze(property_id: int, body: AnalyzeRequest | None = None, db: Session = Depends(get_db)) -> dict:
    p = get_property(db, property_id)
    if not p:
        raise HTTPException(status_code=404, detail="Property not found")
    return analyze_one(p, body.assumptions if body else None)


@router.get("/{property_id}/advice")
def advice(property_id: int, db: Session = Depends(get_db)) -> dict:
    p = get_property(db, property_id)
    if not p:
        raise HTTPException(status_code=404, detail="Property not found")
    bundle = analyze_one(p)
    return {"property_id": property_id, "advice": investment_advice(bundle["property"], bundle["financials"])}


@router.get("/{property_id}/nearby")
def nearby(property_id: int, radius: int = Query(1500, ge=200, le=5000),
           db: Session = Depends(get_db)) -> dict:
    p = get_property(db, property_id)
    if not p:
        raise HTTPException(status_code=404, detail="Property not found")
    return nearby_amenities(p.lat, p.lng, radius_m=radius)


@router.get("/{property_id}/report")
def report(property_id: int, db: Session = Depends(get_db)) -> StreamingResponse:
    p = get_property(db, property_id)
    if not p:
        raise HTTPException(status_code=404, detail="Property not found")
    bundle = analyze_one(p)
    advice = investment_advice(bundle["property"], bundle["financials"])
    pdf = build_property_report(bundle, advice)
    filename = f"investment-report-{property_id}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )

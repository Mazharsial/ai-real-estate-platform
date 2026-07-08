"""Data export (CSV / JSON / Excel)."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.property_service import list_properties, property_to_dict, run_search

router = APIRouter(prefix="/api/export", tags=["export"])

FIELDS = [
    "id", "address", "city", "state", "zip", "price", "beds", "baths", "sqft",
    "property_type", "year_built", "price_per_sqft", "rent_estimate", "rental_yield",
    "undervalued_pct", "investment_score", "predicted_value_3yr",
]


def _rows(db: Session, city: str | None) -> list[dict]:
    rows = list_properties(db, city=city, limit=500)
    if not rows:
        run_search(db, {"city": city} if city else {})
        rows = list_properties(db, city=city, limit=500)
    return [property_to_dict(r) for r in rows]


@router.get("/properties")
def export_properties(format: str = Query("csv", pattern="^(csv|json|xlsx)$"),
                      city: str | None = None, db: Session = Depends(get_db)):
    data = _rows(db, city)
    slim = [{k: d.get(k) for k in FIELDS} for d in data]

    if format == "json":
        return JSONResponse(
            slim, headers={"Content-Disposition": 'attachment; filename="properties.json"'})

    if format == "xlsx":
        wb = Workbook()
        ws = wb.active
        ws.title = "Properties"
        ws.append(FIELDS)
        for row in slim:
            ws.append([row.get(k) for k in FIELDS])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="properties.xlsx"'})

    # default: CSV
    sbuf = io.StringIO()
    writer = csv.DictWriter(sbuf, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(slim)
    return StreamingResponse(
        io.BytesIO(sbuf.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="properties.csv"'})

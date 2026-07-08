"""CSV import — admin only."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.services.analysis import analyze_properties
from app.services.property_service import upsert_property

router = APIRouter(prefix="/api/import", tags=["import"], dependencies=[Depends(require_roles("admin"))])

_NUMERIC = {"price", "beds", "baths", "sqft", "lot_size", "year_built", "days_on_market",
            "hoa", "taxes", "school_rating", "crime_score", "appreciation_trend", "rent_estimate"}


@router.post("/properties")
async def import_properties(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    content = (await file.read()).decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(content))

    raw: list[dict] = []
    for i, row in enumerate(reader):
        d = {k.strip(): v for k, v in row.items() if k and v not in (None, "")}
        for k in list(d):
            if k in _NUMERIC:
                try:
                    d[k] = float(d[k])
                except ValueError:
                    d.pop(k)
        if not d.get("external_id"):
            d["external_id"] = f"import-{d.get('address', 'row')}-{i}"
        d.setdefault("source", "import")
        d.setdefault("city", "")
        raw.append(d)

    if not raw:
        raise HTTPException(status_code=400, detail="No rows found in the CSV")

    analyzed = analyze_properties(raw)
    for p in analyzed:
        upsert_property(db, p)
    db.commit()
    return {"imported": len(analyzed)}

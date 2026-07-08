"""Property Comparison routes (Module 10)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.property import CompareRequest
from app.services.comparison import compare_properties
from app.services.property_service import get_property, property_to_dict

router = APIRouter(prefix="/api/comparison", tags=["comparison"])


@router.post("")
def compare(body: CompareRequest, db: Session = Depends(get_db)) -> dict:
    props = []
    for pid in body.ids:
        p = get_property(db, pid)
        if p:
            props.append(property_to_dict(p))
    if len(props) < 2:
        raise HTTPException(status_code=400, detail="Provide at least two valid property ids")
    return compare_properties(props)

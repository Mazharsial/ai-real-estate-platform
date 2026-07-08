"""Automation routes (Module 15) — deal scan + alerts (called by n8n cron)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.monitor import recent_alerts, run_scan

router = APIRouter(prefix="/api/monitor", tags=["automation"])


@router.get("/scan")
def scan(db: Session = Depends(get_db), city: str | None = None,
         min_under: float = Query(12), min_score: int = Query(70)) -> dict:
    return run_scan(db, city=city, min_under=min_under, min_score=min_score)


@router.get("/alerts")
def alerts(db: Session = Depends(get_db), limit: int = Query(50, le=200)) -> dict:
    rows = recent_alerts(db, limit=limit)
    return {"count": len(rows), "alerts": rows}

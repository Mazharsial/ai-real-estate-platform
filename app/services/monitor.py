"""Automation (Module 15) — daily deal scan that records alerts."""
from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.property import Alert
from app.services.property_service import run_search


def run_scan(db: Session, city: str | None = None, min_under: float = 12, min_score: int = 70) -> dict:
    result = run_search(db, {"city": city} if city else {})
    deals = [
        p for p in result["properties"]
        if (p.get("undervalued_pct") or 0) >= min_under or (p.get("investment_score") or 0) >= min_score
    ]

    start_of_day = datetime.combine(date.today(), time.min)
    fresh: list[dict] = []
    for p in deals:
        already = db.scalar(
            select(Alert).where(Alert.external_id == p["external_id"], Alert.created_at >= start_of_day)
        )
        if already:
            continue
        message = (f"{p['address']} — ${int(p['price']):,} · score {p['investment_score']} · "
                   f"{p['undervalued_pct']}% below market · {p['rental_yield']}% yield")
        db.add(Alert(external_id=p["external_id"], address=p["address"], kind="deal", message=message))
        fresh.append({"id": p["id"], "address": p["address"], "price": p["price"],
                      "investment_score": p["investment_score"], "message": message})
    db.commit()

    city_label = city or "all cities"
    email_text = (
        f"Good morning! {len(fresh)} new investment opportunit"
        f"{'y' if len(fresh) == 1 else 'ies'} in {city_label}:\n\n"
        + "\n".join(f"{i + 1}. {f['message']}" for i, f in enumerate(fresh))
    ) if fresh else f"No new qualifying deals in {city_label} today."

    return {"city": city_label, "new_deals": len(fresh), "deals": fresh, "email_text": email_text}


def recent_alerts(db: Session, limit: int = 50) -> list[dict]:
    rows = db.scalars(select(Alert).order_by(Alert.id.desc()).limit(limit)).all()
    return [
        {"id": a.id, "external_id": a.external_id, "address": a.address, "kind": a.kind,
         "message": a.message, "created_at": a.created_at.isoformat() if a.created_at else None}
        for a in rows
    ]

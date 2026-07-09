"""Automation (Module 15) — daily deal scan that records alerts + emails subscribers."""
from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engagement import SavedSearch
from app.models.property import Alert
from app.models.user import User
from app.services.ai.assistant import apply_filters
from app.services.mailer import send_email
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

    notified = notify_subscribers(db, fresh) if fresh else 0

    return {"city": city_label, "new_deals": len(fresh), "deals": fresh,
            "email_text": email_text, "subscribers_notified": notified}


def notify_subscribers(db: Session, fresh_deals: list[dict]) -> int:
    """Email each user whose alert-enabled saved search matches any fresh deal.

    Matching reuses the natural-language search filter engine. No-ops cleanly when
    SMTP isn't configured (send_email returns False), so it never breaks the scan.
    """
    if not fresh_deals:
        return 0
    searches = db.scalars(select(SavedSearch).where(SavedSearch.alert_enabled == 1)).all()
    sent = 0
    for s in searches:
        matches = apply_filters(fresh_deals, {**(s.filters or {}), "sort": "investment_score"})
        if not matches:
            continue
        user = db.get(User, s.user_id)
        if not user or not user.is_active:
            continue
        lines = "\n".join(
            f"{i + 1}. {m.get('address')} — ${int(m.get('price') or 0):,} · "
            f"score {m.get('investment_score')} · {m.get('rental_yield')}% yield"
            for i, m in enumerate(matches[:10])
        )
        body = (
            f"Hi {user.full_name or 'there'},\n\n"
            f"{len(matches)} new deal(s) match your saved search \"{s.name}\":\n\n{lines}\n\n"
            "Log in to view full analysis and AI advice.\n"
            "— AI Real Estate Platform (reply STOP to stop these alerts)"
        )
        if send_email(user.email, f'New deals for "{s.name}"', body):
            sent += 1
    return sent


def recent_alerts(db: Session, limit: int = 50) -> list[dict]:
    rows = db.scalars(select(Alert).order_by(Alert.id.desc()).limit(limit)).all()
    return [
        {"id": a.id, "external_id": a.external_id, "address": a.address, "kind": a.kind,
         "message": a.message, "created_at": a.created_at.isoformat() if a.created_at else None}
        for a in rows
    ]

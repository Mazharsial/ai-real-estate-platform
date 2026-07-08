"""Deal Finder (Module 9) — bucket properties into named opportunity categories."""
from __future__ import annotations

from app.services.analysis import full_financials


def _enrich(properties: list[dict]) -> list[dict]:
    out = []
    for p in properties:
        fin = full_financials(p)
        out.append({
            **p,
            "monthly_cash_flow": fin["monthly_cash_flow"],
            "cap_rate": fin["cap_rate"],
            "cash_on_cash": fin["cash_on_cash"],
        })
    return out


# category key -> (title, description, sort_fn, filter_fn)
def _categories():
    return [
        ("undervalued", "🏷️ Undervalued", "Priced below the neighborhood average $/sqft",
         lambda p: p.get("undervalued_pct") or 0, lambda p: (p.get("undervalued_pct") or 0) >= 5),
        ("high_yield", "💰 High Rental Yield", "Strongest gross rental yield",
         lambda p: p.get("rental_yield") or 0, None),
        ("best_cash_flow", "💵 Best Cash Flow", "Highest estimated monthly cash flow",
         lambda p: p.get("monthly_cash_flow") or 0, None),
        ("high_appreciation", "📈 Best Appreciation", "Highest historical appreciation trend",
         lambda p: p.get("appreciation_trend") or 0, None),
        ("new_listings", "🆕 New Listings", "Freshest on the market",
         lambda p: -(p.get("days_on_market") or 999), None),
        ("long_term", "🏦 Best Long-Term Hold", "Blend of score, appreciation and yield",
         lambda p: (p.get("investment_score") or 0) + (p.get("appreciation_trend") or 0) * 2, None),
        ("flip_potential", "🔨 Best Flip Potential", "Undervalued and fresh on the market",
         lambda p: (p.get("undervalued_pct") or 0) - (p.get("days_on_market") or 0) / 10, None),
        ("motivated_seller", "⏳ Possible Motivated Seller", "Long on market AND below market (public signals only)",
         lambda p: (p.get("days_on_market") or 0) + (p.get("undervalued_pct") or 0),
         lambda p: (p.get("days_on_market") or 0) >= 35 and (p.get("undervalued_pct") or 0) >= 3),
    ]


def find_deals(properties: list[dict], top_n: int = 6) -> dict:
    enriched = _enrich(properties)
    result = {"total": len(enriched), "categories": []}
    for key, title, desc, sort_fn, filter_fn in _categories():
        items = [p for p in enriched if (filter_fn(p) if filter_fn else True)]
        items = sorted(items, key=sort_fn, reverse=True)[:top_n]
        result["categories"].append({
            "key": key,
            "title": title,
            "description": desc,
            "count": len(items),
            "properties": items,
        })
    return result

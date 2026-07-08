"""Analytics summary (Module 13) — dashboard aggregates for charts."""
from __future__ import annotations

from collections import Counter

from app.services.deal_finder import find_deals
from app.services.market import market_overview


def analytics_summary(properties: list[dict]) -> dict:
    buckets = {"0-49": 0, "50-64": 0, "65-79": 0, "80-100": 0}
    for p in properties:
        s = p.get("investment_score") or 0
        key = "0-49" if s < 50 else "50-64" if s < 65 else "65-79" if s < 80 else "80-100"
        buckets[key] += 1

    by_type = Counter((p.get("property_type") or "?") for p in properties)
    scatter = [
        {"price": p.get("price"), "score": p.get("investment_score"), "address": p.get("address")}
        for p in properties
    ]

    deals = find_deals(properties, top_n=100)
    deal_counts = [{"key": c["key"], "title": c["title"], "count": c["count"]} for c in deals["categories"]]

    market = market_overview(properties)

    return {
        "count": len(properties),
        "avg_score": market["avg_score"],
        "avg_price": market["avg_price"],
        "avg_yield": market["avg_yield"],
        "score_distribution": [{"range": k, "count": v} for k, v in buckets.items()],
        "by_type": [{"type": k, "count": v} for k, v in by_type.items()],
        "price_vs_score": scatter,
        "deal_counts": deal_counts,
        "hot_neighborhoods": market["hot_neighborhoods"],
    }

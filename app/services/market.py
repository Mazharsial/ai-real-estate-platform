"""Market Analysis (Module 7) — aggregate statistics across a property set."""
from __future__ import annotations

import statistics
from collections import defaultdict

from app.services.analysis import predict_value, rnd


def _avg(nums: list[float]) -> float:
    nums = [n for n in nums if n]
    return rnd(sum(nums) / len(nums), 2) if nums else 0.0


def _median(nums: list[float]) -> float:
    nums = [n for n in nums if n]
    return rnd(statistics.median(nums), 0) if nums else 0.0


def market_overview(properties: list[dict], city: str | None = None) -> dict:
    if city:
        properties = [p for p in properties if (p.get("city") or "").lower() == city.lower()]

    prices = [p.get("price") for p in properties]
    ppsf = [p.get("price_per_sqft") for p in properties]
    yields = [p.get("rental_yield") for p in properties]
    dom = [p.get("days_on_market") for p in properties]
    scores = [p.get("investment_score") for p in properties]
    appr = [p.get("appreciation_trend") for p in properties]

    growths = []
    for p in properties:
        if p.get("price_history"):
            growths.append(predict_value(p["price_history"], p.get("price"))["cagr"])

    # neighborhood breakdown (by zip)
    by_zip: dict[str, list[dict]] = defaultdict(list)
    for p in properties:
        by_zip[p.get("zip") or "—"].append(p)
    neighborhoods = []
    for zc, items in by_zip.items():
        neighborhoods.append({
            "zip": zc,
            "count": len(items),
            "avg_price": _avg([i.get("price") for i in items]),
            "avg_ppsf": _avg([i.get("price_per_sqft") for i in items]),
            "avg_score": round(_avg([i.get("investment_score") for i in items])),
            "avg_yield": _avg([i.get("rental_yield") for i in items]),
        })
    neighborhoods.sort(key=lambda n: n["avg_score"], reverse=True)

    # simple price histogram for charts
    buckets = defaultdict(int)
    for pr in prices:
        if pr:
            b = int(pr // 100000) * 100
            buckets[f"${b}k-${b + 100}k"] += 1
    price_distribution = [{"range": k, "count": v} for k, v in sorted(buckets.items())]

    return {
        "city": city or (properties[0].get("city") if properties else None),
        "count": len(properties),
        "median_price": _median(prices),
        "avg_price": _avg(prices),
        "avg_ppsf": _avg(ppsf),
        "avg_yield": _avg(yields),
        "avg_days_on_market": round(_avg(dom)),
        "avg_score": round(_avg(scores)),
        "avg_appreciation": _avg(appr),
        "avg_price_growth": _avg(growths),
        "hot_neighborhoods": neighborhoods[:5],
        "neighborhoods": neighborhoods,
        "price_distribution": price_distribution,
    }

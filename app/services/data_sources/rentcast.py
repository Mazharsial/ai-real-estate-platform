"""Property data adapter — RentCast free tier with automatic demo fallback.

The ONE place to swap in another data provider later (Module 3 extension point).
"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.services.analysis import heuristic_monthly_rent
from app.services.data_sources.seed_data import filter_seed

DEFAULT_IMG = "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=800&q=60"


def _hash01(s: str, salt: str = "") -> float:
    h = 2166136261
    for ch in f"{s}{salt}":
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return (h % 1000) / 1000


def _derive_neighborhood(zc: str) -> dict:
    return {
        "school_rating": round(4 + _hash01(zc, "school") * 6),
        "crime_score": round(4 + _hash01(zc, "crime") * 6),
        "appreciation_trend": round((3 + _hash01(zc, "appr") * 5), 1),
    }


def _normalize(item: dict) -> dict:
    zc = item.get("zipCode") or item.get("zip") or ""
    price = item.get("price") or 0
    return {
        "source": "rentcast",
        "external_id": f"rc-{item.get('id') or item.get('formattedAddress')}",
        "address": item.get("formattedAddress") or item.get("addressLine1") or "Unknown address",
        "city": item.get("city") or "",
        "state": item.get("state") or "",
        "zip": zc,
        "lat": item.get("latitude"),
        "lng": item.get("longitude"),
        "price": price,
        "beds": item.get("bedrooms") or 0,
        "baths": item.get("bathrooms") or 0,
        "sqft": item.get("squareFootage") or 0,
        "lot_size": item.get("lotSize") or 0,
        "property_type": item.get("propertyType") or "House",
        "year_built": item.get("yearBuilt"),
        "days_on_market": item.get("daysOnMarket") or 0,
        "hoa": (item.get("hoa") or {}).get("fee", 0) if isinstance(item.get("hoa"), dict) else 0,
        "taxes": 0,
        "description": item.get("description")
        or f"{item.get('bedrooms', '?')} bed / {item.get('bathrooms', '?')} bath home in {item.get('city', '')}.",
        "image_url": (item.get("photos") or [DEFAULT_IMG])[0],
        "agent_name": (item.get("listingAgent") or {}).get("name", "Listing Agent"),
        "agent_phone": (item.get("listingAgent") or {}).get("phone", ""),
        "rent_estimate": heuristic_monthly_rent(price),
        "price_history": None,
        **_derive_neighborhood(zc),
    }


def fetch_properties(criteria: dict | None = None) -> dict:
    """Return {source, properties, note?}. Never raises — always yields data."""
    criteria = criteria or {}
    city = criteria.get("city") or settings.DEFAULT_CITY
    state = criteria.get("state") or settings.DEFAULT_STATE
    key = settings.RENTCAST_API_KEY

    if not key:
        return {"source": "demo", "properties": filter_seed(**{**criteria, "city": city})}

    try:
        params = {"city": city, "state": state, "status": "Active", "limit": 30}
        if criteria.get("max_price"):
            params["maxPrice"] = int(criteria["max_price"])
        if criteria.get("min_beds"):
            params["bedrooms"] = int(criteria["min_beds"])
        if criteria.get("property_type") and criteria["property_type"] != "Any":
            params["propertyType"] = criteria["property_type"]

        resp = httpx.get(
            "https://api.rentcast.io/v1/listings/sale",
            params=params,
            headers={"X-Api-Key": key, "Accept": "application/json"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        listings = data if isinstance(data, list) else data.get("listings", [])
        props = [_normalize(x) for x in listings if (x.get("price") or 0) > 0]

        if criteria.get("max_price"):
            props = [p for p in props if p["price"] <= float(criteria["max_price"])]
        if criteria.get("min_beds"):
            props = [p for p in props if p["beds"] >= int(criteria["min_beds"])]

        if not props:
            return {"source": "demo", "note": "RentCast returned no matches — showing demo data",
                    "properties": filter_seed(**{**criteria, "city": city})}
        return {"source": "rentcast", "properties": props}
    except Exception as exc:  # noqa: BLE001 — graceful fallback is intentional
        return {"source": "demo", "note": f"RentCast unavailable ({exc}) — showing demo data",
                "properties": filter_seed(**{**criteria, "city": city})}

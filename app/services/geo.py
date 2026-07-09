"""Nearby-amenity search (Module 4) via OpenStreetMap Overpass — free, no API key.

Given a property's coordinates, find nearby schools, hospitals, restaurants, transit,
etc., with straight-line distance. Degrades gracefully to an empty result if Overpass
is unreachable, so the app never breaks when offline.
"""
from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

import httpx

# Public Overpass endpoints (tried in order; the API is free but rate-limited/flaky).
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
_UA = "AI-RealEstate-Platform/1.0 (research/education)"

# category key -> (label, emoji, predicate on the element's OSM tags)
_CATEGORIES: list[tuple[str, str, str, object]] = [
    ("school", "Schools", "🏫", lambda t: t.get("amenity") == "school"),
    ("university", "Universities", "🎓", lambda t: t.get("amenity") in ("university", "college")),
    ("hospital", "Hospitals & clinics", "🏥", lambda t: t.get("amenity") in ("hospital", "clinic", "doctors")),
    ("pharmacy", "Pharmacies", "💊", lambda t: t.get("amenity") == "pharmacy"),
    ("restaurant", "Restaurants & cafés", "🍽️", lambda t: t.get("amenity") in ("restaurant", "cafe", "fast_food")),
    ("supermarket", "Groceries", "🛒", lambda t: t.get("shop") in ("supermarket", "convenience", "grocery")),
    ("bank", "Banks & ATMs", "🏦", lambda t: t.get("amenity") in ("bank", "atm")),
    ("park", "Parks", "🌳", lambda t: t.get("leisure") == "park"),
    ("gym", "Gyms", "🏋️", lambda t: t.get("leisure") == "fitness_centre" or t.get("amenity") == "gym"),
    ("transit", "Transit", "🚉", lambda t: (
        t.get("highway") == "bus_stop"
        or t.get("railway") in ("station", "halt", "tram_stop")
        or t.get("public_transport") == "station"
    )),
]
_FALLBACK_NAME = {c[0]: c[1].rstrip("s").split(" ")[0] for c in _CATEGORIES}


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in metres."""
    r = 6_371_000
    dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return round(2 * r * asin(sqrt(a)), 1)


def _build_query(lat: float, lng: float, radius_m: int) -> str:
    r = radius_m
    filters = [
        'nwr["amenity"~"^(school|university|college|hospital|clinic|doctors|pharmacy|restaurant|cafe|fast_food|bank|atm|gym)$"]',
        'nwr["shop"~"^(supermarket|convenience|grocery)$"]',
        'nwr["leisure"~"^(park|fitness_centre)$"]',
        'nwr["highway"="bus_stop"]',
        'nwr["railway"~"^(station|halt|tram_stop)$"]',
    ]
    body = "".join(f"{f}(around:{r},{lat},{lng});" for f in filters)
    return f"[out:json][timeout:20];({body});out center tags 250;"


def _overpass_fetch(query: str) -> list[dict]:
    """Raw Overpass call. Isolated so tests can monkeypatch it (no network).

    Uses GET + a User-Agent (POST/no-UA gets 406/504 from the main instance) and
    falls back across mirrors so a single flaky endpoint doesn't kill the feature.
    """
    last_exc: Exception | None = None
    for url in OVERPASS_URLS:
        try:
            r = httpx.get(url, params={"data": query}, headers={"User-Agent": _UA}, timeout=25)
            r.raise_for_status()
            return r.json().get("elements", [])
        except Exception as exc:  # noqa: BLE001 — try the next mirror
            last_exc = exc
    raise last_exc if last_exc else RuntimeError("no overpass endpoint")


def _categorize(tags: dict) -> tuple[str, str, str] | None:
    for key, label, icon, pred in _CATEGORIES:
        if pred(tags):
            return key, label, icon
    return None


def nearby_amenities(lat: float | None, lng: float | None, radius_m: int = 1500,
                     per_category: int = 6) -> dict:
    """Return categorized nearby amenities with distances, nearest first."""
    empty = {"center": {"lat": lat, "lng": lng}, "radius_m": radius_m,
             "categories": [], "total": 0}
    if lat is None or lng is None:
        return empty
    try:
        elements = _overpass_fetch(_build_query(lat, lng, radius_m))
    except Exception:  # noqa: BLE001 — Overpass down / offline => graceful empty
        return empty

    grouped: dict[str, dict] = {}
    for el in elements:
        tags = el.get("tags") or {}
        cat = _categorize(tags)
        if not cat:
            continue
        key, label, icon = cat
        elat = el.get("lat") or (el.get("center") or {}).get("lat")
        elng = el.get("lon") or (el.get("center") or {}).get("lon")
        if elat is None or elng is None:
            continue
        g = grouped.setdefault(key, {"key": key, "label": label, "icon": icon, "items": []})
        g["items"].append({
            "name": tags.get("name") or _FALLBACK_NAME[key],
            "lat": elat, "lng": elng,
            "distance_m": haversine_m(lat, lng, elat, elng),
        })

    categories = []
    total = 0
    for key, label, icon, _ in _CATEGORIES:  # stable, spec order
        if key not in grouped:
            continue
        items = sorted(grouped[key]["items"], key=lambda x: x["distance_m"])
        total += len(items)
        categories.append({
            "key": key, "label": label, "icon": icon,
            "count": len(items), "items": items[:per_category],
        })
    return {"center": {"lat": lat, "lng": lng}, "radius_m": radius_m,
            "categories": categories, "total": total}

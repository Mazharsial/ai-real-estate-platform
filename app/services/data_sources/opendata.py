"""Legal, free, no-key public open-data adapter (Module 3 extension point).

Reads a public open-data property dataset — e.g. a Socrata resource such as a city
assessor / property-sales feed (``https://data.<city>.gov/resource/<id>.json``). These
are published for public reuse, so this is a ToS-respecting alternative to scraping
listing sites. Configure via OPENDATA_URL; an optional OPENDATA_FIELD_MAP (JSON) maps
dataset-specific column names onto our schema.

Returns a normalized list; raises on failure so the dispatcher can fall back to demo.
"""
from __future__ import annotations

import json

import httpx

from app.core.config import settings
from app.services.analysis import heuristic_monthly_rent

DEFAULT_IMG = "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=800&q=60"

# Common column names seen across open-data property datasets, tried in order.
_DEFAULT_MAP = {
    "address": ["address", "property_address", "full_address", "street_address", "location_address", "site_address"],
    "city": ["city", "municipality", "town", "city_name"],
    "state": ["state", "state_code", "st"],
    "zip": ["zip", "zip_code", "zipcode", "postal_code", "zip5"],
    "price": ["sale_price", "price", "sale_amount", "amount", "total_value", "assessed_value", "market_value"],
    "beds": ["bedrooms", "beds", "number_of_bedrooms", "num_bedrooms", "bedroom"],
    "baths": ["bathrooms", "baths", "number_of_bathrooms", "num_bathrooms", "bathroom"],
    "sqft": ["square_feet", "sqft", "building_sqft", "total_area", "living_area", "gross_area"],
    "year_built": ["year_built", "yearbuilt", "year_construction", "construction_year"],
    "property_type": ["property_type", "type", "building_type", "class_description", "use"],
    "lat": ["latitude", "lat", "y_coordinate"],
    "lng": ["longitude", "lng", "lon", "long", "x_coordinate"],
}


def _field_map() -> dict:
    if settings.OPENDATA_FIELD_MAP:
        try:
            override = json.loads(settings.OPENDATA_FIELD_MAP)
            # allow either a single name or a list per field
            return {k: (v if isinstance(v, list) else [v]) for k, v in override.items()}
        except Exception:  # noqa: BLE001 — bad override JSON => ignore, use defaults
            pass
    return _DEFAULT_MAP


def _first(row: dict, names: list[str]):
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return None


def _to_float(v) -> float:
    try:
        return float(str(v).replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        return 0.0


def _coords(row: dict, fmap: dict) -> tuple[float | None, float | None]:
    lat, lng = _first(row, fmap["lat"]), _first(row, fmap["lng"])
    if lat is not None and lng is not None:
        return _to_float(lat) or None, _to_float(lng) or None
    # Socrata point/geometry objects: {"latitude":..,"longitude":..} or GeoJSON Point
    for key in ("location", "the_geom", "geocoded_column", "point", "gelocation"):
        g = row.get(key)
        if isinstance(g, dict):
            if g.get("latitude") and g.get("longitude"):
                return _to_float(g["latitude"]) or None, _to_float(g["longitude"]) or None
            coords = g.get("coordinates")
            if isinstance(coords, list) and len(coords) == 2:  # GeoJSON = [lng, lat]
                return _to_float(coords[1]) or None, _to_float(coords[0]) or None
    return None, None


def _normalize(row: dict, idx: int, fmap: dict) -> dict | None:
    price = _to_float(_first(row, fmap["price"]))
    address = _first(row, fmap["address"])
    if not address or price <= 0:
        return None
    lat, lng = _coords(row, fmap)
    zc = str(_first(row, fmap["zip"]) or "")
    return {
        "source": settings.OPENDATA_SOURCE_LABEL,
        "external_id": f"od-{idx}-{address}"[:110],
        "address": str(address),
        "city": str(_first(row, fmap["city"]) or ""),
        "state": str(_first(row, fmap["state"]) or ""),
        "zip": zc,
        "lat": lat,
        "lng": lng,
        "price": price,
        "beds": int(_to_float(_first(row, fmap["beds"]))),
        "baths": _to_float(_first(row, fmap["baths"])),
        "sqft": int(_to_float(_first(row, fmap["sqft"]))),
        "lot_size": 0,
        "property_type": str(_first(row, fmap["property_type"]) or "House"),
        "year_built": int(_to_float(_first(row, fmap["year_built"]))) or None,
        "days_on_market": 0,
        "hoa": 0,
        "taxes": 0,
        "description": f"Public-record property in {_first(row, fmap['city']) or 'the area'}.",
        "image_url": DEFAULT_IMG,
        "agent_name": "",
        "agent_phone": "",
        "rent_estimate": heuristic_monthly_rent(price),
        "price_history": None,
        "school_rating": 0,
        "crime_score": 0,
        "appreciation_trend": 0,
    }


def _opendata_get(url: str, params: dict, headers: dict) -> list[dict]:
    """Raw HTTP call. Isolated so tests can monkeypatch it (no network)."""
    resp = httpx.get(url, params=params, headers=headers, timeout=25)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("data", [])


def fetch_opendata(criteria: dict | None = None) -> list[dict]:
    """Fetch + normalize properties from the configured open-data source. [] if not set."""
    criteria = criteria or {}
    url = settings.OPENDATA_URL
    if not url:
        return []

    params: dict = {"$limit": 200}
    if criteria.get("city"):  # best-effort server-side filter (Socrata SoQL)
        params["$q"] = criteria["city"]
    headers = {"Accept": "application/json"}
    if settings.OPENDATA_APP_TOKEN:
        headers["X-App-Token"] = settings.OPENDATA_APP_TOKEN

    rows = _opendata_get(url, params, headers)
    fmap = _field_map()
    props = [p for p in (_normalize(r, i, fmap) for i, r in enumerate(rows)) if p]

    # client-side filters (datasets vary in server-side support)
    if criteria.get("city"):
        c = criteria["city"].lower()
        props = [p for p in props if not p["city"] or p["city"].lower() == c]
    if criteria.get("max_price"):
        props = [p for p in props if p["price"] <= float(criteria["max_price"])]
    if criteria.get("min_beds"):
        props = [p for p in props if p["beds"] >= int(criteria["min_beds"])]
    if criteria.get("property_type") and criteria["property_type"] != "Any":
        props = [p for p in props if p["property_type"] == criteria["property_type"]]
    return props[:60]

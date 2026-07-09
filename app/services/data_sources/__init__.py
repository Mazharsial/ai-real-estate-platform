"""Property data-source dispatcher (Module 3).

Picks the active provider from settings.DATA_SOURCE and falls back cleanly to the
built-in demo dataset if the chosen provider is unset, errors, or returns nothing —
so the app always yields data and never raises.
"""
from __future__ import annotations

from app.core.config import settings
from app.services.data_sources.opendata import fetch_opendata
from app.services.data_sources.rentcast import fetch_rentcast
from app.services.data_sources.seed_data import filter_seed


def _providers() -> list[tuple[str, object]]:
    choice = (settings.DATA_SOURCE or "auto").lower()
    out: list[tuple[str, object]] = []
    if choice == "rentcast" or (choice == "auto" and settings.RENTCAST_API_KEY):
        out.append(("rentcast", fetch_rentcast))
    if choice == "opendata" or (choice == "auto" and settings.OPENDATA_URL):
        out.append((settings.OPENDATA_SOURCE_LABEL, fetch_opendata))
    return out


def active_source_name() -> str:
    providers = _providers()
    return providers[0][0] if providers else "demo"


def fetch_properties(criteria: dict | None = None) -> dict:
    """Return {source, properties, note?}. Never raises — always yields data."""
    criteria = criteria or {}
    city = criteria.get("city") or settings.DEFAULT_CITY

    note = None
    for name, fn in _providers():
        try:
            props = fn(criteria)
            if props:
                return {"source": name, "properties": props}
            note = f"{name} returned no matches"
        except Exception as exc:  # noqa: BLE001 — graceful fallback is intentional
            note = f"{name} unavailable ({exc})"

    result = {"source": "demo", "properties": filter_seed(**{**criteria, "city": city})}
    if note:
        result["note"] = f"{note} — showing demo data"
    return result

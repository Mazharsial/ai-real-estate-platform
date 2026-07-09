"""Tests for nearby-amenity search (Module 4). Overpass is monkeypatched — no network."""
import app.services.geo as geo
from app.services.geo import haversine_m, nearby_amenities

# A small fake Overpass payload around downtown Dallas (~32.78, -96.80)
_SAMPLE = [
    {"lat": 32.7810, "lon": -96.7990, "tags": {"amenity": "school", "name": "City School"}},
    {"lat": 32.7850, "lon": -96.8010, "tags": {"amenity": "hospital", "name": "General Hospital"}},
    {"lat": 32.7805, "lon": -96.7985, "tags": {"amenity": "restaurant", "name": "Taco Place"}},
    {"lat": 32.7802, "lon": -96.7999, "tags": {"amenity": "restaurant", "name": "Sushi Bar"}},
    {"center": {"lat": 32.7799, "lon": -96.8005}, "tags": {"leisure": "park", "name": "Main Park"}},
    {"lat": 32.7808, "lon": -96.7992, "tags": {"highway": "bus_stop"}},          # unnamed -> fallback name
    {"lat": 32.7811, "lon": -96.7991, "tags": {"office": "yes", "name": "Ignore Me"}},  # uncategorized
]


def test_haversine_known_distance():
    # ~1 degree of latitude ≈ 111 km
    d = haversine_m(0, 0, 1, 0)
    assert 110_000 < d < 112_000


def test_nearby_no_coords_returns_empty():
    out = nearby_amenities(None, None)
    assert out["categories"] == [] and out["total"] == 0


def test_nearby_categorizes_and_sorts(monkeypatch):
    monkeypatch.setattr(geo, "_overpass_fetch", lambda q: _SAMPLE)
    out = nearby_amenities(32.7800, -96.8000, radius_m=1500)

    keys = [c["key"] for c in out["categories"]]
    assert "school" in keys and "hospital" in keys and "restaurant" in keys
    assert "transit" in keys and "park" in keys
    assert "office" not in keys                      # uncategorized dropped
    assert out["total"] == 6                          # the office entry is excluded

    # spec/category order preserved (school before restaurant before park before transit)
    assert keys.index("school") < keys.index("restaurant") < keys.index("transit")

    resto = next(c for c in out["categories"] if c["key"] == "restaurant")
    assert resto["count"] == 2
    dists = [it["distance_m"] for it in resto["items"]]
    assert dists == sorted(dists)                     # nearest first

    bus = next(c for c in out["categories"] if c["key"] == "transit")
    assert bus["items"][0]["name"]                    # fallback name, not empty


def test_nearby_graceful_when_overpass_fails(monkeypatch):
    def boom(q):
        raise RuntimeError("overpass down")
    monkeypatch.setattr(geo, "_overpass_fetch", boom)
    out = nearby_amenities(32.78, -96.80)
    assert out["categories"] == [] and out["total"] == 0


def test_nearby_endpoint_shape(client, monkeypatch):
    monkeypatch.setattr(geo, "_overpass_fetch", lambda q: _SAMPLE)
    # ensure at least one property exists, then hit its nearby endpoint
    props = client.get("/api/properties?limit=1").json()
    pid = props[0]["id"]
    r = client.get(f"/api/properties/{pid}/nearby")
    assert r.status_code == 200
    body = r.json()
    assert "categories" in body and "center" in body and "radius_m" in body

"""Data-source dispatcher + open-data adapter tests (network monkeypatched)."""
import app.services.data_sources as ds
import app.services.data_sources.opendata as od
from app.core.config import settings
from app.services.data_sources import fetch_properties

_SAMPLE = [
    {"property_address": "100 Main St", "city": "Dallas", "state": "TX", "zip": "75201",
     "sale_price": "250000", "bedrooms": "3", "bathrooms": "2", "square_feet": "1500",
     "year_built": "1998", "latitude": "32.78", "longitude": "-96.80"},
    {"address": "200 Oak Ave", "city": "Dallas", "sale_amount": "$180,000", "beds": "2",
     "location": {"latitude": "32.79", "longitude": "-96.81"}},
    {"address": "No price row", "city": "Dallas"},                       # no price -> dropped
    {"full_address": "300 Elm", "city": "Dallas", "price": "320000",
     "the_geom": {"type": "Point", "coordinates": [-96.82, 32.80]}},     # GeoJSON [lng,lat]
]


def test_default_source_is_demo():
    r = fetch_properties({})
    assert r["source"] == "demo" and r["properties"]


def test_opendata_normalizes_rows(monkeypatch):
    monkeypatch.setattr(settings, "OPENDATA_URL", "https://data.example/resource/x.json")
    monkeypatch.setattr(od, "_opendata_get", lambda url, params, headers: _SAMPLE)

    props = od.fetch_opendata({"city": "Dallas"})
    assert len(props) == 3                                   # the price-less row is dropped
    by_addr = {p["address"]: p for p in props}

    m = by_addr["100 Main St"]
    assert m["price"] == 250000 and m["beds"] == 3 and m["sqft"] == 1500
    assert abs(m["lat"] - 32.78) < 1e-6

    assert by_addr["200 Oak Ave"]["price"] == 180000         # "$180,000" parsed
    assert abs(by_addr["200 Oak Ave"]["lat"] - 32.79) < 1e-6  # from location{} dict

    elm = by_addr["300 Elm"]
    assert abs(elm["lat"] - 32.80) < 1e-6 and abs(elm["lng"] + 96.82) < 1e-6  # GeoJSON parsed


def test_dispatcher_selects_opendata(monkeypatch):
    monkeypatch.setattr(settings, "DATA_SOURCE", "opendata")
    monkeypatch.setattr(settings, "OPENDATA_URL", "https://x")
    monkeypatch.setattr(ds, "fetch_opendata",
                        lambda c: [{"source": "opendata", "price": 1, "external_id": "od-1",
                                    "address": "A", "city": "Dallas", "investment_score": 0}])
    r = fetch_properties({})
    assert r["source"] == "opendata"


def test_dispatcher_falls_back_to_demo_on_error(monkeypatch):
    monkeypatch.setattr(settings, "DATA_SOURCE", "opendata")
    monkeypatch.setattr(settings, "OPENDATA_URL", "https://x")

    def boom(c):
        raise RuntimeError("endpoint down")
    monkeypatch.setattr(ds, "fetch_opendata", boom)

    r = fetch_properties({})
    assert r["source"] == "demo" and "note" in r and "down" in r["note"]


def test_opendata_disabled_returns_empty():
    # settings.OPENDATA_URL is unset in tests -> adapter no-ops
    assert od.fetch_opendata({}) == []

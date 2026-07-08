"""Realistic Dallas, TX demo dataset (fallback when no RentCast key / quota).

Representative data, not live listings. Neighborhood metrics are estimates.
"""
from __future__ import annotations

IMGS = [
    "https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1570129477492-45c003edd2be?auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1605276374104-dee2a0ed3cd6?auto=format&fit=crop&w=800&q=60",
]

# address, zip, lat, lng, price, beds, baths, sqft, lot, type, year, dom, hoa, taxes, school, safety, appr, rent
_BASE = [
    ("4212 Live Oak St", "75204", 32.8021, -96.7853, 389000, 3, 2, 1850, 6200, "House", 2016, 9, 0, 8100, 8, 7, 6.2, 2850),
    ("6829 Gaston Ave", "75214", 32.8156, -96.7402, 415000, 3, 2, 2100, 7000, "House", 2009, 21, 0, 8700, 9, 8, 5.4, 2950),
    ("1820 Cedar Springs Rd", "75201", 32.7998, -96.8087, 305000, 2, 2, 1200, 0, "Condo", 2018, 33, 380, 6300, 7, 6, 4.1, 2300),
    ("5510 W Amherst Ave", "75209", 32.8480, -96.8260, 560000, 4, 3, 2650, 8200, "House", 2013, 15, 0, 11800, 9, 8, 6.9, 3600),
    ("9541 Meadowknoll Dr", "75243", 32.9110, -96.7320, 268000, 3, 2, 1700, 6800, "House", 1998, 41, 0, 5600, 6, 7, 3.6, 2100),
    ("3117 Skillman St", "75206", 32.8290, -96.7690, 342000, 2, 2, 1400, 3000, "Townhouse", 2015, 12, 210, 7200, 8, 7, 5.1, 2500),
    ("7420 La Manga Dr", "75248", 32.9660, -96.8040, 498000, 4, 3, 2900, 9000, "House", 2005, 28, 0, 10400, 9, 9, 5.8, 3200),
    ("2450 Victory Park Ln", "75219", 32.7852, -96.8110, 455000, 2, 2, 1550, 0, "Condo", 2019, 19, 520, 9400, 8, 7, 4.7, 3000),
    ("11338 Fernald Ave", "75218", 32.8420, -96.6900, 315000, 3, 2, 1780, 7400, "House", 1995, 7, 0, 6600, 7, 8, 4.9, 2400),
    ("4801 Bryan St", "75204", 32.8010, -96.7790, 372000, 3, 3, 1980, 3200, "Townhouse", 2017, 24, 240, 7800, 8, 7, 5.6, 2700),
    ("6104 Vickery Blvd", "75214", 32.8265, -96.7550, 289000, 2, 1, 1250, 6000, "House", 1948, 52, 0, 5900, 8, 7, 4.3, 2050),
    ("8207 San Benito Way", "75218", 32.8360, -96.6980, 344000, 3, 2, 1900, 7600, "House", 2001, 16, 0, 7100, 7, 8, 5.0, 2500),
    ("3900 Buena Vista St", "75204", 32.8095, -96.7960, 620000, 3, 3, 2400, 2600, "Townhouse", 2020, 30, 300, 12900, 9, 8, 7.4, 3800),
    ("10650 Steppington Dr", "75230", 32.9010, -96.7770, 410000, 3, 2, 2150, 7800, "House", 2003, 22, 0, 8600, 9, 9, 5.3, 2900),
    ("5325 Bookout Dr", "75230", 32.9075, -96.7860, 375000, 3, 2, 2000, 7200, "House", 1999, 11, 0, 7900, 9, 9, 5.2, 2750),
    ("2109 Wycliff Ave", "75219", 32.8130, -96.8180, 335000, 2, 2, 1350, 0, "Condo", 2016, 47, 450, 6900, 7, 6, 3.9, 2350),
    ("7715 Umphress Rd", "75217", 32.7220, -96.6620, 232000, 3, 2, 1600, 6500, "House", 1990, 38, 0, 4800, 5, 5, 3.2, 1900),
    ("6420 Prospect Ave", "75214", 32.8210, -96.7480, 468000, 4, 3, 2500, 7900, "House", 2011, 8, 0, 9800, 9, 8, 6.4, 3300),
]

_AGENTS = ["Sarah Collins", "James Whitfield", "Maria Gonzalez", "David Park"]


def _history(price: float, appr_pct: float) -> list[dict]:
    r = appr_pct / 100
    return [{"year": y, "value": round(price / (1 + r) ** (2024 - y))} for y in range(2019, 2025)]


def _build() -> list[dict]:
    out: list[dict] = []
    for i, b in enumerate(_BASE):
        (address, zc, lat, lng, price, beds, baths, sqft, lot, ptype, year, dom, hoa, taxes,
         school, safety, appr, rent) = b
        out.append({
            "source": "demo",
            "external_id": f"demo-{zc}-{i + 1}",
            "address": address,
            "city": "Dallas",
            "state": "TX",
            "zip": zc,
            "lat": lat,
            "lng": lng,
            "price": price,
            "beds": beds,
            "baths": baths,
            "sqft": sqft,
            "lot_size": lot,
            "property_type": ptype,
            "year_built": year,
            "days_on_market": dom,
            "hoa": hoa,
            "taxes": taxes,
            "description": f"{beds} bed / {baths} bath {ptype.lower()} in Dallas ({zc}), built {year}. {sqft:,} sqft.",
            "image_url": IMGS[i % len(IMGS)],
            "agent_name": _AGENTS[i % len(_AGENTS)],
            "agent_phone": f"(214) 555-0{100 + i}",
            "school_rating": school,
            "crime_score": safety,
            "appreciation_trend": appr,
            "rent_estimate": rent,
            "price_history": _history(price, appr),
        })
    return out


SEED_PROPERTIES: list[dict] = _build()


def filter_seed(city: str | None = None, max_price: float | None = None,
                min_beds: int | None = None, property_type: str | None = None,
                **_ignore) -> list[dict]:
    def keep(p: dict) -> bool:
        if city and p["city"].lower() != str(city).lower():
            return False
        if max_price and p["price"] > float(max_price):
            return False
        if min_beds and p["beds"] < int(min_beds):
            return False
        if property_type and property_type != "Any" and p["property_type"] != property_type:
            return False
        return True

    return [dict(p) for p in SEED_PROPERTIES if keep(p)]

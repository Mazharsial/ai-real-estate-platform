"""AI Chatbot + Natural-Language / Semantic Search.

Turns plain-English questions ("3-bedroom houses under $150k near universities with
high rental yield") into structured property filters, retrieves the matching
properties from the database, and — when an AI provider is configured — answers in
natural language grounded on that real data.

Everything degrades to a deterministic parser + template answer, so the chatbot and
NL search work fully offline with zero API keys (and the tests stay deterministic).
"""
from __future__ import annotations

import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.property import Property
from app.services.ai.provider import generate_text
from app.services.property_service import property_to_dict, run_search

# ── plain-English → property_type ────────────────────────────────────────────
_TYPE_WORDS = {
    "house": "House", "home": "House", "homes": "House", "houses": "House",
    "apartment": "Apartment", "apartments": "Apartment", "condo": "Apartment",
    "condos": "Apartment", "flat": "Apartment", "flats": "Apartment",
    "villa": "Villa", "villas": "Villa",
    "commercial": "Commercial", "office": "Office", "offices": "Office",
    "warehouse": "Warehouse", "warehouses": "Warehouse",
    "farm": "Farm", "farms": "Farm", "land": "Land", "plot": "Land", "plots": "Land",
    "studio": "Studio", "studios": "Studio", "duplex": "Duplex", "duplexes": "Duplex",
    "penthouse": "Penthouse", "penthouses": "Penthouse",
}

_MAX_WORDS = r"under|below|less than|cheaper than|up to|within|max|maximum|budget( of)?|no more than|<"
_MIN_WORDS = r"over|above|more than|at least|starting( at)?|min|minimum|from|>"

_PRICE_RE = re.compile(
    rf"(?P<dir>{_MAX_WORDS}|{_MIN_WORDS})\s*\$?\s*(?P<num>[\d,]+(?:\.\d+)?)\s*(?P<suf>[kmKM])?",
)
_BARE_PRICE_RE = re.compile(r"\$\s*(?P<num>[\d,]+(?:\.\d+)?)\s*(?P<suf>[kmKM])?")
_BEDS_RE = re.compile(r"(\d+)[\s-]*\+?[\s-]*(?:beds?|bedrooms?|br|bd)\b", re.I)
_BATHS_RE = re.compile(r"(\d+(?:\.\d+)?)[\s-]*\+?[\s-]*(?:baths?|bathrooms?|ba)\b", re.I)
_SCORE_RE = re.compile(r"score\s*(?:above|over|of|>=|>)?\s*(\d{1,3})", re.I)


def _to_number(num: str, suf: str | None) -> float:
    n = float(num.replace(",", ""))
    if suf and suf.lower() == "k":
        n *= 1_000
    elif suf and suf.lower() == "m":
        n *= 1_000_000
    return n


def _known_cities(db: Session) -> list[str]:
    rows = db.scalars(select(Property.city).distinct()).all()
    return sorted({c for c in rows if c})


def parse_query(question: str, known_cities: list[str] | None = None) -> dict:
    """Deterministic NL → filters. No AI needed (keeps search working offline)."""
    q = question.lower()
    f: dict = {}

    # price (direction-aware, then a bare "$150k" fallback => budget/max)
    for m in _PRICE_RE.finditer(q):
        val = _to_number(m.group("num"), m.group("suf"))
        if val < 1000 and not m.group("suf"):
            continue  # e.g. "at least 2 beds" — too small to be a price
        if re.match(_MIN_WORDS, m.group("dir")):
            f["min_price"] = val
        else:
            f["max_price"] = val
    if "max_price" not in f and "min_price" not in f:
        bm = _BARE_PRICE_RE.search(q)
        if bm:
            f["max_price"] = _to_number(bm.group("num"), bm.group("suf"))

    if (bm := _BEDS_RE.search(q)):
        f["min_beds"] = int(bm.group(1))
    if (bm := _BATHS_RE.search(q)):
        f["min_baths"] = float(bm.group(1))
    if (sm := _SCORE_RE.search(q)):
        f["min_score"] = min(100, int(sm.group(1)))

    for word, canonical in _TYPE_WORDS.items():
        if re.search(rf"\b{word}\b", q):
            f["property_type"] = canonical
            break

    # city — match against DB cities first, then an "in/near <City>" fallback
    for city in (known_cities or []):
        if re.search(rf"\b{re.escape(city.lower())}\b", q):
            f["city"] = city
            break
    if "city" not in f:
        cm = re.search(r"\b(?:in|near|around|at)\s+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)", question)
        if cm:
            f["city"] = cm.group(1).strip()

    # sort intent
    if re.search(r"cheapest|lowest price|most affordable", q):
        f["sort"] = "price_asc"
    elif re.search(r"rental yield|high yield|best yield|cash ?flow|rental income|rent", q):
        f["sort"] = "rental_yield"
    elif re.search(r"undervalued|below market|discount|best deal|bargain", q):
        f["sort"] = "undervalued_pct"
    elif re.search(r"appreciat|growth|price growth|going up", q):
        f["sort"] = "appreciation_trend"
    elif re.search(r"new(est)?|just listed|recently listed", q):
        f["sort"] = "days_on_market_asc"
    else:
        f["sort"] = "investment_score"  # "best investment / roi / top deals"

    return f


def _load_working_set(db: Session, limit: int = 300) -> list[dict]:
    rows = db.scalars(select(Property).order_by(Property.investment_score.desc()).limit(limit)).all()
    if not rows:  # never answer on an empty DB
        run_search(db, {})
        rows = db.scalars(select(Property).order_by(Property.investment_score.desc()).limit(limit)).all()
    return [property_to_dict(r) for r in rows]


_SORT_KEYS = {
    "rental_yield": ("rental_yield", True),
    "undervalued_pct": ("undervalued_pct", True),
    "appreciation_trend": ("appreciation_trend", True),
    "investment_score": ("investment_score", True),
    "price_asc": ("price", False),
    "days_on_market_asc": ("days_on_market", False),
}


def apply_filters(props: list[dict], f: dict) -> list[dict]:
    out = []
    for p in props:
        if f.get("city") and (p.get("city") or "").lower() != f["city"].lower():
            continue
        if f.get("property_type") and (p.get("property_type") or "") != f["property_type"]:
            continue
        if f.get("max_price") and (p.get("price") or 0) > f["max_price"]:
            continue
        if f.get("min_price") and (p.get("price") or 0) < f["min_price"]:
            continue
        if f.get("min_beds") and (p.get("beds") or 0) < f["min_beds"]:
            continue
        if f.get("min_baths") and (p.get("baths") or 0) < f["min_baths"]:
            continue
        if f.get("min_score") and (p.get("investment_score") or 0) < f["min_score"]:
            continue
        out.append(p)
    key, reverse = _SORT_KEYS.get(f.get("sort", "investment_score"), ("investment_score", True))
    out.sort(key=lambda x: (x.get(key) or 0), reverse=reverse)
    return out


def _describe(f: dict) -> str:
    bits = []
    if f.get("min_beds"):
        bits.append(f"{f['min_beds']}+ bed")
    if f.get("min_baths"):
        bits.append(f"{f['min_baths']}+ bath")
    if f.get("property_type"):
        bits.append(f["property_type"].lower() + "s")
    else:
        bits.append("properties")
    if f.get("max_price"):
        bits.append(f"under ${f['max_price']:,.0f}")
    if f.get("min_price"):
        bits.append(f"over ${f['min_price']:,.0f}")
    if f.get("city"):
        bits.append(f"in {f['city']}")
    sort_labels = {
        "rental_yield": "ranked by rental yield", "undervalued_pct": "most undervalued first",
        "appreciation_trend": "ranked by appreciation", "price_asc": "cheapest first",
        "days_on_market_asc": "newest first", "investment_score": "ranked by investment score",
    }
    return " ".join(bits) + ", " + sort_labels.get(f.get("sort", "investment_score"), "")


def nl_search(db: Session, question: str, limit: int = 24) -> dict:
    """Semantic-ish search: plain English → filtered, ranked properties."""
    props = _load_working_set(db)
    f = parse_query(question, _known_cities(db))
    matches = apply_filters(props, f)
    return {
        "query": question,
        "filters": f,
        "explanation": _describe(f),
        "count": len(matches),
        "properties": matches[:limit],
    }


def _city_leaderboard(props: list[dict], metric: str) -> list[dict]:
    agg: dict[str, list[float]] = {}
    for p in props:
        c = p.get("city")
        if not c:
            continue
        agg.setdefault(c, []).append(float(p.get(metric) or 0))
    board = [{"city": c, "value": round(sum(v) / len(v), 2), "n": len(v)} for c, v in agg.items()]
    board.sort(key=lambda x: x["value"], reverse=True)
    return board


def _fallback_answer(question: str, f: dict, matches: list[dict], all_props: list[dict]) -> str:
    q = question.lower()
    # analytical "which city has the best yield / roi / appreciation?"
    if re.search(r"which (city|area|neighborhood|place)|highest|top city|best city", q):
        metric = ("rental_yield" if "yield" in q or "rent" in q
                  else "appreciation_trend" if "appreci" in q or "growth" in q
                  else "investment_score")
        board = _city_leaderboard(all_props, metric)
        if board:
            label = {"rental_yield": "rental yield", "appreciation_trend": "appreciation",
                     "investment_score": "investment score"}[metric]
            top = board[0]
            runners = ", ".join(f"{b['city']} ({b['value']})" for b in board[1:3])
            return (f"By average {label}, **{top['city']}** leads at {top['value']} "
                    f"across {top['n']} listings." + (f" Next: {runners}." if runners else ""))
    if not matches:
        return ("I couldn't find properties matching that. Try widening the price range, "
                "the city, or the number of bedrooms.")
    top = matches[0]
    avg_price = round(sum(p.get("price") or 0 for p in matches) / len(matches))
    avg_yield = round(sum(p.get("rental_yield") or 0 for p in matches) / len(matches), 2)
    return (f"Found **{len(matches)}** matching {_describe(f)}. "
            f"Top pick: {top.get('address')} ({top.get('city')}) at ${top.get('price'):,.0f}, "
            f"investment score {top.get('investment_score')}/100, "
            f"{top.get('rental_yield')}% yield. "
            f"Average price ${avg_price:,.0f}, average yield {avg_yield}%.")


def chat(db: Session, question: str, max_cards: int = 6) -> dict:
    """The AI chatbot: NL question → grounded answer + relevant property cards."""
    all_props = _load_working_set(db)
    f = parse_query(question, _known_cities(db))
    matches = apply_filters(all_props, f)
    cards = matches[:max_cards]

    fallback = _fallback_answer(question, f, matches, all_props)

    top_json = json.dumps([
        {k: p.get(k) for k in ("address", "city", "price", "beds", "baths", "property_type",
                               "investment_score", "rental_yield", "undervalued_pct")}
        for p in cards
    ])
    prompt = (
        "You are a helpful real-estate investment assistant. Answer the user's question in 2-4 sentences, "
        "grounded ONLY on the data provided. Be concrete: cite prices, yields, scores, and city names. "
        "Do not invent listings. If the data is empty, say so and suggest broadening the search.\n\n"
        f"QUESTION: {question}\n"
        f"MATCHING PROPERTIES ({len(matches)} total, top {len(cards)} shown): {top_json}\n"
        f"PARSED FILTERS: {json.dumps(f)}\n"
        "ANSWER:"
    )
    text = generate_text(prompt, temperature=0.4, max_tokens=400)
    answer = text.strip() if text else fallback
    return {
        "question": question,
        "answer": answer,
        "source": "ai" if text else "rules",
        "filters": f,
        "match_count": len(matches),
        "properties": cards,
    }

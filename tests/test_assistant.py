"""Tests for the AI chatbot + natural-language search (deterministic, no external AI)."""
from app.services.ai.assistant import apply_filters, parse_query


def test_parse_query_extracts_beds_price_and_type():
    f = parse_query("3-bedroom houses under $150k with high rental yield")
    assert f["min_beds"] == 3
    assert f["property_type"] == "House"
    assert f["max_price"] == 150_000
    assert f["sort"] == "rental_yield"


def test_parse_query_min_price_and_bare_dollar():
    assert parse_query("apartments over $200,000")["min_price"] == 200_000
    assert parse_query("condos $90k")["max_price"] == 90_000  # bare amount => budget


def test_parse_query_matches_known_city():
    f = parse_query("cheapest homes in dallas", known_cities=["Dallas", "Austin"])
    assert f["city"] == "Dallas"
    assert f["sort"] == "price_asc"


def test_parse_query_beds_not_read_as_price():
    f = parse_query("at least 2 beds")
    assert f.get("min_beds") == 2
    assert "max_price" not in f and "min_price" not in f


def test_apply_filters_respects_price_and_type():
    props = [
        {"price": 100_000, "property_type": "House", "beds": 3, "investment_score": 80, "rental_yield": 7},
        {"price": 300_000, "property_type": "House", "beds": 4, "investment_score": 90, "rental_yield": 5},
        {"price": 120_000, "property_type": "Apartment", "beds": 2, "investment_score": 70, "rental_yield": 9},
    ]
    out = apply_filters(props, {"max_price": 150_000, "property_type": "House", "sort": "investment_score"})
    assert len(out) == 1 and out[0]["price"] == 100_000


def test_search_endpoint_returns_filtered_properties(client):
    r = client.post("/api/assistant/search", json={"question": "houses under $500000"})
    assert r.status_code == 200
    body = r.json()
    assert "properties" in body and "filters" in body
    assert body["filters"]["max_price"] == 500_000
    assert all(p["price"] <= 500_000 for p in body["properties"])


def test_chat_endpoint_answers_without_ai(client):
    r = client.post("/api/assistant/chat", json={"question": "show me the most undervalued properties"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "rules"          # AI disabled in tests
    assert body["answer"]                      # non-empty grounded answer
    assert body["match_count"] >= 0


def test_chat_which_city_is_analytical(client):
    r = client.post("/api/assistant/chat", json={"question": "Which city has the highest rental yield?"})
    assert r.status_code == 200
    assert "yield" in r.json()["answer"].lower()

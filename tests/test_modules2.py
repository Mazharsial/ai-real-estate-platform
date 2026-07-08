"""Tests for Deal Finder (9), Comparison (10) & Market Analysis (7)."""


def _seed(client):
    client.post("/api/properties/search", json={"city": "Dallas"})


def test_deal_finder_categories(client):
    _seed(client)
    r = client.get("/api/deals?city=Dallas")
    assert r.status_code == 200
    body = r.json()
    keys = {c["key"] for c in body["categories"]}
    assert {"undervalued", "high_yield", "best_cash_flow", "high_appreciation"} <= keys
    for c in body["categories"]:
        assert isinstance(c["properties"], list)
        assert len(c["properties"]) <= 6


def test_market_overview(client):
    _seed(client)
    r = client.get("/api/market/overview?city=Dallas")
    assert r.status_code == 200
    m = r.json()
    assert m["count"] > 0
    assert m["avg_price"] > 0
    assert m["median_price"] > 0
    assert len(m["neighborhoods"]) > 0
    assert len(m["hot_neighborhoods"]) <= 5
    assert isinstance(m["price_distribution"], list)


def test_comparison(client):
    _seed(client)
    ids = [p["id"] for p in client.get("/api/properties?limit=3").json()]
    r = client.post("/api/comparison", json={"ids": ids})
    assert r.status_code == 200
    body = r.json()
    assert body["winner_id"] in ids
    assert len(body["properties"]) == len(ids)
    assert body["recommendation"]
    assert "financials" in body["properties"][0]


def test_comparison_requires_two(client):
    _seed(client)
    one = [client.get("/api/properties?limit=1").json()[0]["id"]]
    assert client.post("/api/comparison", json={"ids": one}).status_code == 400

"""Property discovery, analysis, advice & favorites (integration via TestClient)."""


def test_search_returns_ranked(client):
    r = client.post("/api/properties/search", json={"city": "Dallas", "max_price": 500000})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] > 0
    scores = [p["investment_score"] for p in body["properties"]]
    assert scores == sorted(scores, reverse=True)  # ranked desc


def test_list_and_detail(client):
    client.post("/api/properties/search", json={"city": "Dallas"})
    r = client.get("/api/properties?limit=5")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) > 0
    pid = rows[0]["id"]
    d = client.get(f"/api/properties/{pid}")
    assert d.status_code == 200
    assert d.json()["id"] == pid
    assert client.get("/api/properties/99999999").status_code == 404


def test_analyze_financials(client):
    client.post("/api/properties/search", json={"city": "Dallas"})
    pid = client.get("/api/properties?limit=1").json()[0]["id"]
    r = client.post(f"/api/properties/{pid}/analyze", json={})
    assert r.status_code == 200
    fin = r.json()["financials"]
    assert fin["cap_rate"] is not None
    assert "monthly_cash_flow" in fin
    assert set(["score", "breakdown"]).issubset(r.json()["score"].keys())


def test_advice_fallback(client):
    # AI key is empty in tests -> deterministic rules-based advice
    client.post("/api/properties/search", json={"city": "Dallas"})
    pid = client.get("/api/properties?limit=1").json()[0]["id"]
    r = client.get(f"/api/properties/{pid}/advice")
    assert r.status_code == 200
    adv = r.json()["advice"]
    assert adv["source"] == "rules"
    assert isinstance(adv["pros"], list)
    assert adv["suggested_offer"] > 0


def test_favorites_flow(auth_client):
    auth_client.post("/api/properties/search", json={"city": "Dallas"})
    pid = auth_client.get("/api/properties?limit=1").json()[0]["id"]
    assert auth_client.post(f"/api/favorites/{pid}").status_code == 201
    favs = auth_client.get("/api/favorites").json()
    assert any(p["id"] == pid for p in favs)
    auth_client.delete(f"/api/favorites/{pid}")
    favs2 = auth_client.get("/api/favorites").json()
    assert not any(p["id"] == pid for p in favs2)

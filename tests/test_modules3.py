"""Tests for Saved Searches (11), PDF Reports (12) & Analytics (13)."""


def _seed(client):
    client.post("/api/properties/search", json={"city": "Dallas"})


def test_pdf_report(client):
    _seed(client)
    pid = client.get("/api/properties?limit=1").json()[0]["id"]
    r = client.get(f"/api/properties/{pid}/report")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 1500  # a real, non-empty document


def test_analytics_summary(client):
    _seed(client)
    r = client.get("/api/analytics/summary?city=Dallas")
    assert r.status_code == 200
    a = r.json()
    assert a["count"] > 0
    assert len(a["score_distribution"]) == 4
    assert sum(b["count"] for b in a["score_distribution"]) == a["count"]
    assert len(a["by_type"]) > 0
    assert len(a["deal_counts"]) >= 4
    assert len(a["price_vs_score"]) == a["count"]


def test_saved_searches_flow(auth_client):
    payload = {"name": "Cheap Dallas houses", "filters": {"city": "Dallas", "max_price": 350000}, "alert_enabled": True}
    r = auth_client.post("/api/saved-searches", json=payload)
    assert r.status_code == 201
    sid = r.json()["id"]
    assert r.json()["alert_enabled"] is True

    rows = auth_client.get("/api/saved-searches").json()
    assert any(s["id"] == sid for s in rows)

    assert auth_client.delete(f"/api/saved-searches/{sid}").status_code == 200
    rows2 = auth_client.get("/api/saved-searches").json()
    assert not any(s["id"] == sid for s in rows2)


def test_saved_searches_requires_auth(client):
    assert client.get("/api/saved-searches").status_code == 401

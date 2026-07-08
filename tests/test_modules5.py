"""Tests for Automation (15), security middleware & CSV import."""
import io
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.middleware import RateLimitMiddleware
from app.models.user import User


def test_monitor_scan_and_alerts(client):
    r = client.get("/api/monitor/scan?city=Dallas")
    assert r.status_code == 200
    body = r.json()
    assert "new_deals" in body
    assert "email_text" in body

    a = client.get("/api/monitor/alerts")
    assert a.status_code == 200
    assert a.json()["count"] >= 0


def test_security_headers(client):
    r = client.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"


def test_rate_limit_isolated():
    mini = FastAPI()
    mini.add_middleware(RateLimitMiddleware, per_minute=3)

    @mini.get("/ping")
    def ping():
        return {"ok": True}

    c = TestClient(mini)
    codes = [c.get("/ping").status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200]
    assert codes[-1] == 429


def _promote_admin(client):
    email = f"imp{int(time.time() * 1000000)}@t.com"
    tok = client.post("/api/auth/register", json={"email": email, "password": "supersecret1"}).json()["access_token"]
    db = SessionLocal()
    u = db.scalar(select(User).where(User.email == email))
    u.role = "admin"
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {tok}"}


def test_csv_import(client):
    headers = _promote_admin(client)
    csv_data = (
        "external_id,address,city,state,zip,price,beds,baths,sqft,property_type\n"
        "imp-1,100 Test Ave,Austin,TX,78701,320000,3,2,1800,House\n"
        "imp-2,200 Test Ave,Austin,TX,78701,410000,4,3,2400,House\n"
    )
    files = {"file": ("p.csv", io.BytesIO(csv_data.encode()), "text/csv")}
    r = client.post("/api/import/properties", files=files, headers=headers)
    assert r.status_code == 200
    assert r.json()["imported"] == 2

    # the imported rows are searchable
    got = client.get("/api/properties?city=Austin").json()
    assert any(p["address"] == "100 Test Ave" for p in got)


def test_csv_import_requires_admin(client):
    files = {"file": ("p.csv", io.BytesIO(b"external_id,price\nx,1"), "text/csv")}
    assert client.post("/api/import/properties", files=files).status_code == 401

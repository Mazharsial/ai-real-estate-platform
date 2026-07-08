"""Tests for Portfolio (14), Export & Admin panel."""
import time

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.user import User


def test_portfolio_flow(auth_client):
    payload = {
        "address": "1 Main St", "city": "Dallas", "property_type": "House",
        "purchase_price": 300000, "current_value": 360000,
        "monthly_rent": 2500, "monthly_expenses": 900, "mortgage_balance": 220000,
    }
    r = auth_client.post("/api/portfolio", json=payload)
    assert r.status_code == 201
    hid = r.json()["id"]

    s = auth_client.get("/api/portfolio").json()
    assert s["count"] >= 1
    assert s["total_equity"] > 0
    h = next(x for x in s["holdings"] if x["id"] == hid)
    assert h["equity"] == 140000          # 360k - 220k mortgage
    assert h["monthly_cash_flow"] == 1600  # 2500 - 900
    assert h["roi"] > 0
    assert len(s["diversification_type"]) >= 1

    assert auth_client.delete(f"/api/portfolio/{hid}").status_code == 200


def test_export_formats(client):
    client.post("/api/properties/search", json={"city": "Dallas"})

    csv_r = client.get("/api/export/properties?format=csv")
    assert csv_r.status_code == 200 and "text/csv" in csv_r.headers["content-type"]
    assert b"investment_score" in csv_r.content

    j = client.get("/api/export/properties?format=json")
    assert j.status_code == 200 and isinstance(j.json(), list) and len(j.json()) > 0

    x = client.get("/api/export/properties?format=xlsx")
    assert x.status_code == 200
    assert x.content[:2] == b"PK"  # xlsx is a zip archive


def test_admin_guard_and_access(client):
    email = f"adm{int(time.time() * 1000000)}@t.com"
    tok = client.post("/api/auth/register", json={"email": email, "password": "supersecret1"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}

    # investor is blocked
    assert client.get("/api/admin/stats", headers=headers).status_code == 403

    # promote to admin directly in the DB
    db = SessionLocal()
    u = db.scalar(select(User).where(User.email == email))
    u.role = "admin"
    db.commit()
    db.close()

    assert client.get("/api/admin/stats", headers=headers).status_code == 200
    users = client.get("/api/admin/users", headers=headers).json()
    assert any(x["email"] == email for x in users)

    # change a role via admin
    other = client.post("/api/auth/register", json={"email": f"x{email}", "password": "supersecret1"}).json()["user"]["id"]
    r = client.patch(f"/api/admin/users/{other}", json={"role": "agent"}, headers=headers)
    assert r.status_code == 200 and r.json()["role"] == "agent"

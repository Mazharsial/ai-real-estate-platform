"""Security tests: Flask CSRF protection + secure CSV upload validation."""
import re
import time

from app.core.database import SessionLocal
from app.models.user import User


# ── Flask CSRF (session-cookie forms) ────────────────────────────────────────
def _flask_client():
    from web.app import create_app
    app = create_app()
    app.config.update(TESTING=True, SECRET_KEY="test-flask-secret")
    return app.test_client()


def test_post_without_csrf_token_is_rejected():
    c = _flask_client()
    r = c.post("/login", data={"email": "a@b.com", "password": "x"})
    assert r.status_code == 400


def test_post_with_valid_csrf_token_passes_csrf_gate():
    c = _flask_client()
    page = c.get("/login").data.decode()
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    # CSRF passes -> request proceeds (API is unreachable in the test, so it flashes and
    # re-renders with 200 — the point is it's NOT a 400 CSRF rejection).
    r = c.post("/login", data={"email": "a@b.com", "password": "x", "csrf_token": token})
    assert r.status_code == 200


def test_csrf_token_mismatch_is_rejected():
    c = _flask_client()
    c.get("/login")  # establishes a session token
    r = c.post("/login", data={"email": "a@b.com", "password": "x", "csrf_token": "wrong"})
    assert r.status_code == 400


# ── Secure CSV upload (admin-only import endpoint) ───────────────────────────
def _admin_token(client) -> str:
    email = f"admin{int(time.time() * 1_000_000)}@test.com"
    reg = client.post("/api/auth/register",
                      json={"email": email, "password": "supersecret1"}).json()
    db = SessionLocal()
    u = db.get(User, reg["user"]["id"])
    u.role = "admin"
    db.commit()
    db.close()
    return reg["access_token"]


def test_import_rejects_non_csv(client):
    tok = _admin_token(client)
    r = client.post("/api/import/properties",
                    files={"file": ("data.txt", b"not,a,csv", "text/plain")},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 400


def test_import_rejects_oversized_file(client):
    tok = _admin_token(client)
    big = b"external_id,price\n" + b"x" * (5 * 1024 * 1024 + 100)
    r = client.post("/api/import/properties",
                    files={"file": ("big.csv", big, "text/csv")},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 413


def test_import_requires_admin(client):
    # a normal investor token cannot import
    reg = client.post("/api/auth/register",
                      json={"email": f"inv{int(time.time()*1e6)}@test.com", "password": "supersecret1"}).json()
    r = client.post("/api/import/properties",
                    files={"file": ("x.csv", b"external_id\n1", "text/csv")},
                    headers={"Authorization": f"Bearer {reg['access_token']}"})
    assert r.status_code == 403

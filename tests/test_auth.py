"""Auth flow + role guard tests."""
import time


def _email():
    return f"auth{int(time.time() * 1000000)}@test.com"


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_login_me(client):
    email = _email()
    r = client.post("/api/auth/register", json={"email": email, "password": "supersecret1", "full_name": "Jane"})
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["role"] == "investor"
    token = body["access_token"]

    # duplicate registration blocked
    assert client.post("/api/auth/register", json={"email": email, "password": "supersecret1"}).status_code == 409

    # login
    r = client.post("/api/auth/login", json={"email": email, "password": "supersecret1"})
    assert r.status_code == 200

    # wrong password
    assert client.post("/api/auth/login", json={"email": email, "password": "nope"}).status_code == 401

    # me
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == email


def test_protected_requires_auth(client):
    assert client.get("/api/favorites").status_code == 401
    assert client.get("/api/favorites", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_short_password_rejected(client):
    r = client.post("/api/auth/register", json={"email": _email(), "password": "short"})
    assert r.status_code == 422

"""Password reset + email-alert tests. SMTP is disabled/monkeypatched — no network."""
import time

import app.services.monitor as monitor
from app.core.database import SessionLocal
from app.models.engagement import SavedSearch
from app.models.user import User
from app.services.mailer import mail_configured, send_email


def _unique_email() -> str:
    return f"reset{int(time.time() * 1_000_000)}@test.com"


def test_mail_not_configured_in_tests():
    assert mail_configured() is False
    assert send_email("a@b.com", "s", "body") is False  # graceful, no crash


def test_password_reset_full_flow(client):
    email = _unique_email()
    client.post("/api/auth/register", json={"email": email, "password": "supersecret1", "full_name": "R"})

    # forgot -> dev returns the token (no mail server)
    r = client.post("/api/auth/forgot-password", json={"email": email})
    assert r.status_code == 200
    token = r.json()["reset_token"]

    # reset with the token
    r = client.post("/api/auth/reset-password", json={"token": token, "new_password": "brandnewpass9"})
    assert r.status_code == 200 and r.json()["access_token"]

    # old password rejected, new password works
    assert client.post("/api/auth/login", json={"email": email, "password": "supersecret1"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": email, "password": "brandnewpass9"}).status_code == 200

    # the same token can't be reused (bound to the old password hash)
    again = client.post("/api/auth/reset-password", json={"token": token, "new_password": "another12345"})
    assert again.status_code == 400


def test_forgot_password_unknown_email_does_not_leak(client):
    r = client.post("/api/auth/forgot-password", json={"email": "nobody-here@test.com"})
    assert r.status_code == 200
    assert "reset_token" not in r.json()          # no token for a non-existent account


def test_reset_with_bad_token_rejected(client):
    r = client.post("/api/auth/reset-password", json={"token": "not-a-jwt", "new_password": "whatever12"})
    assert r.status_code == 400


def test_notify_subscribers_emails_matching_saved_search(client, monkeypatch):
    # a user with an alert-enabled saved search for cheap Dallas houses
    email = _unique_email()
    reg = client.post("/api/auth/register",
                      json={"email": email, "password": "supersecret1", "full_name": "S"}).json()
    uid = reg["user"]["id"]

    db = SessionLocal()
    db.add(SavedSearch(user_id=uid, name="Cheap Dallas",
                       filters={"city": "Dallas", "max_price": 300000}, alert_enabled=1))
    db.commit()

    captured = []
    monkeypatch.setattr(monitor, "send_email",
                        lambda to, subject, body: captured.append((to, subject)) or True)

    fresh = [
        {"address": "1 A St", "city": "Dallas", "price": 250000, "property_type": "House",
         "investment_score": 80, "rental_yield": 8},
        {"address": "2 B St", "city": "Austin", "price": 250000, "property_type": "House",
         "investment_score": 85, "rental_yield": 7},  # different city -> should NOT match
    ]
    sent = monitor.notify_subscribers(db, fresh)
    db.close()

    assert sent == 1
    assert captured and captured[0][0] == email

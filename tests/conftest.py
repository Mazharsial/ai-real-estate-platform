"""Pytest fixtures. Uses an isolated SQLite DB and disables external AI for determinism."""
import os

# Must be set BEFORE importing the app (config caches settings at import time).
os.environ["DATABASE_URL"] = "sqlite:///./test_platform.db"
os.environ["GEMINI_API_KEY"] = ""
os.environ["AI_PROVIDER"] = "gemini"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["RENTCAST_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _prepare_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_client(client):
    import time

    email = f"user{int(time.time() * 1000)}@test.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "supersecret1", "full_name": "T"})
    token = r.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client

"""Seed the database with an admin user and demo properties.

Usage:  python scripts/seed.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.core.database import SessionLocal, init_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.services.property_service import run_search  # noqa: E402

ADMIN_EMAIL = os.environ.get("SEED_ADMIN_EMAIL", "admin@platform.local")
ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "admin12345")


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        if not db.scalar(select(User).where(User.email == ADMIN_EMAIL)):
            db.add(User(
                email=ADMIN_EMAIL,
                full_name="Administrator",
                hashed_password=hash_password(ADMIN_PASSWORD),
                role=UserRole.admin.value,
                is_superuser=True,
            ))
            db.commit()
            print(f"[seed] created admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        else:
            print(f"[seed] admin already exists: {ADMIN_EMAIL}")

        result = run_search(db, {})
        print(f"[seed] {result['count']} properties loaded (source: {result['source']})")
    finally:
        db.close()


if __name__ == "__main__":
    main()

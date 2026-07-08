"""Audit log (security / traceability)."""
from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    action: Mapped[str] = mapped_column(String(80), default="")
    entity: Mapped[str] = mapped_column(String(80), default="")
    detail: Mapped[str | None] = mapped_column(Text, default=None)
    ip: Mapped[str | None] = mapped_column(String(64), default=None)

"""Saved search schemas (Module 11)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class SavedSearchCreate(BaseModel):
    name: str = "My search"
    filters: dict[str, Any] = {}
    alert_enabled: bool = False


class SavedSearchOut(BaseModel):
    id: int
    name: str
    filters: dict[str, Any]
    alert_enabled: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

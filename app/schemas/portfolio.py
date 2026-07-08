"""Portfolio schemas (Module 14)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class HoldingCreate(BaseModel):
    address: str = ""
    city: str = ""
    property_type: str = "House"
    purchase_price: float = 0
    current_value: float = 0
    monthly_rent: float = 0
    monthly_expenses: float = 0
    mortgage_balance: float = 0
    purchase_date: Optional[str] = None
    notes: Optional[str] = None
    property_id: Optional[int] = None


class HoldingOut(HoldingCreate):
    id: int
    model_config = {"from_attributes": True}

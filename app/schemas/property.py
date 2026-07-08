"""Property schemas."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class SearchCriteria(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    max_price: Optional[float] = None
    min_beds: Optional[int] = None
    property_type: Optional[str] = None


class PropertyOut(BaseModel):
    id: Optional[int] = None
    external_id: Optional[str] = None
    source: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    price: Optional[float] = None
    beds: Optional[int] = None
    baths: Optional[float] = None
    sqft: Optional[int] = None
    property_type: Optional[str] = None
    year_built: Optional[int] = None
    days_on_market: Optional[int] = None
    image_url: Optional[str] = None
    price_per_sqft: Optional[float] = None
    rent_estimate: Optional[float] = None
    rental_yield: Optional[float] = None
    school_rating: Optional[float] = None
    crime_score: Optional[float] = None
    appreciation_trend: Optional[float] = None
    neighborhood_avg_ppsf: Optional[float] = None
    undervalued_pct: Optional[float] = None
    investment_score: Optional[int] = None
    predicted_value_3yr: Optional[float] = None

    model_config = {"from_attributes": True, "extra": "ignore"}


class SearchResult(BaseModel):
    source: str
    note: Optional[str] = None
    count: int
    properties: list[PropertyOut]


class AnalyzeRequest(BaseModel):
    assumptions: Optional[dict[str, Any]] = None


class CompareRequest(BaseModel):
    ids: list[int]

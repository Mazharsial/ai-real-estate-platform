"""Property + related models (Modules 2/3/5)."""
from __future__ import annotations

from sqlalchemy import Float, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Property(Base, TimestampMixin):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(40), default="demo")
    external_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)

    # Listing / location
    title: Mapped[str | None] = mapped_column(String(255), default=None)
    address: Mapped[str] = mapped_column(String(255), default="")
    city: Mapped[str] = mapped_column(String(120), index=True, default="")
    state: Mapped[str] = mapped_column(String(40), default="")
    zip: Mapped[str] = mapped_column(String(20), index=True, default="")
    lat: Mapped[float | None] = mapped_column(Float, default=None)
    lng: Mapped[float | None] = mapped_column(Float, default=None)

    # Core attributes
    price: Mapped[float] = mapped_column(Float, default=0)
    beds: Mapped[int] = mapped_column(Integer, default=0)
    baths: Mapped[float] = mapped_column(Float, default=0)
    sqft: Mapped[int] = mapped_column(Integer, default=0)
    lot_size: Mapped[int] = mapped_column(Integer, default=0)
    property_type: Mapped[str] = mapped_column(String(60), default="House", index=True)
    year_built: Mapped[int | None] = mapped_column(Integer, default=None)
    days_on_market: Mapped[int] = mapped_column(Integer, default=0)
    hoa: Mapped[float] = mapped_column(Float, default=0)
    taxes: Mapped[float] = mapped_column(Float, default=0)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    image_url: Mapped[str | None] = mapped_column(String(500), default=None)
    agent_name: Mapped[str | None] = mapped_column(String(160), default=None)
    agent_phone: Mapped[str | None] = mapped_column(String(60), default=None)

    # Neighborhood signals
    school_rating: Mapped[float] = mapped_column(Float, default=0)
    crime_score: Mapped[float] = mapped_column(Float, default=0)  # safety, 10 = safest
    appreciation_trend: Mapped[float] = mapped_column(Float, default=0)  # %/yr

    # Computed analytics (persisted after analysis)
    price_per_sqft: Mapped[float] = mapped_column(Float, default=0)
    rent_estimate: Mapped[float] = mapped_column(Float, default=0)
    rental_yield: Mapped[float] = mapped_column(Float, default=0)
    neighborhood_avg_ppsf: Mapped[float] = mapped_column(Float, default=0)
    undervalued_pct: Mapped[float] = mapped_column(Float, default=0)
    investment_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    predicted_value_3yr: Mapped[float] = mapped_column(Float, default=0)
    price_history: Mapped[list | None] = mapped_column(JSON, default=None)
    ai_summary: Mapped[str | None] = mapped_column(Text, default=None)


class Alert(Base, TimestampMixin):
    """Deal alerts produced by the automated daily scan (Module 15)."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(120), index=True)
    address: Mapped[str] = mapped_column(String(255), default="")
    kind: Mapped[str] = mapped_column(String(40), default="deal")
    message: Mapped[str] = mapped_column(Text, default="")

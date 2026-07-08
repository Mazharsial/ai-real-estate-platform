"""Import all models so SQLAlchemy metadata is fully populated."""
from app.models.user import User, UserRole  # noqa: F401
from app.models.property import Property, Alert  # noqa: F401
from app.models.engagement import Favorite, SavedSearch  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401

__all__ = [
    "User",
    "UserRole",
    "Property",
    "Alert",
    "Favorite",
    "SavedSearch",
    "AuditLog",
]

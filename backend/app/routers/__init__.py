"""
API Routers package.
"""

from app.routers import (
    auth,
    properties,
    rooms,
    tenants,
    payments,
    notifications,
    maintenance,
)

__all__ = [
    "auth",
    "properties",
    "rooms",
    "tenants",
    "payments",
    "notifications",
    "maintenance",
]

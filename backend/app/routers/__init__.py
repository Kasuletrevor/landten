"""
API Routers package.
"""

from app.routers import auth, properties, rooms, tenants, payments, notifications

__all__ = [
    "auth",
    "properties",
    "rooms",
    "tenants",
    "payments",
    "notifications",
]

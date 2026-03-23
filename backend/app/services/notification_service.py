"""
In-app notification service using Server-Sent Events (SSE).
"""

import asyncio
import json
import logging
from typing import Dict, Set, AsyncGenerator
from datetime import datetime, timezone
from sqlmodel import Session

from app.models.notification import Notification, NotificationType


# Store active SSE connections per landlord.
# landlord_id -> set of async queues
_connections: Dict[str, Set[asyncio.Queue]] = {}

# Store active SSE connections per tenant.
# tenant_id -> set of async queues
_tenant_connections: Dict[str, Set[asyncio.Queue]] = {}

logger = logging.getLogger(__name__)


async def _subscribe(
    owner_id: str, owner_connections: Dict[str, Set[asyncio.Queue]], role_label: str
) -> AsyncGenerator[str, None]:
    queue: asyncio.Queue = asyncio.Queue()

    if owner_id not in owner_connections:
        owner_connections[owner_id] = set()
    owner_connections[owner_id].add(queue)

    try:
        yield format_sse_event(
            "connected",
            {
                "message": "Connected to notification stream",
                "role": role_label,
            },
        )

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield event
            except asyncio.TimeoutError:
                yield format_sse_event(
                    "ping", {"timestamp": datetime.now(timezone.utc).isoformat()}
                )
    finally:
        owner_connections[owner_id].discard(queue)
        if not owner_connections[owner_id]:
            del owner_connections[owner_id]


async def subscribe(landlord_id: str) -> AsyncGenerator[str, None]:
    """
    Subscribe to notifications for a landlord.
    Yields SSE-formatted events.
    """
    async for event in _subscribe(landlord_id, _connections, "landlord"):
        yield event


async def subscribe_tenant(tenant_id: str) -> AsyncGenerator[str, None]:
    """
    Subscribe to notifications for a tenant.
    Yields SSE-formatted events.
    """
    async for event in _subscribe(tenant_id, _tenant_connections, "tenant"):
        yield event


async def _broadcast(
    owner_id: str,
    owner_connections: Dict[str, Set[asyncio.Queue]],
    event_type: str,
    data: dict,
    role_label: str,
) -> None:
    if owner_id not in owner_connections:
        return

    event = format_sse_event(event_type, data)

    for queue in tuple(owner_connections[owner_id]):
        try:
            await queue.put(event)
        except Exception:
            logger.exception(
                "Failed to broadcast SSE event",
                extra={
                    "owner_id": owner_id,
                    "event_type": event_type,
                    "role": role_label,
                },
            )


def format_sse_event(event_type: str, data: dict) -> str:
    """Format data as an SSE event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def broadcast_to_landlord(landlord_id: str, event_type: str, data: dict):
    """
    Broadcast an event to all connections for a landlord.
    """
    await _broadcast(landlord_id, _connections, event_type, data, "landlord")


async def broadcast_to_tenant(tenant_id: str, event_type: str, data: dict):
    """
    Broadcast an event to all connections for a tenant.
    """
    await _broadcast(
        tenant_id,
        _tenant_connections,
        event_type,
        data,
        "tenant",
    )


async def notify_payment_due(
    landlord_id: str,
    tenant_name: str,
    amount: float,
    due_date: str,
    property_name: str,
    payment_id: str,
    session: Session,
):
    """
    Send a payment due notification.
    """
    notification = Notification(
        landlord_id=landlord_id,
        type=NotificationType.PAYMENT_DUE,
        title="Payment Due",
        message=f"{tenant_name}'s payment of ${amount:,.2f} is due on {due_date} for {property_name}",
        payment_id=payment_id,
    )
    session.add(notification)
    session.commit()

    await broadcast_to_landlord(
        landlord_id,
        "payment_due",
        {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "payment_id": payment_id,
            "created_at": notification.created_at.isoformat(),
        },
    )


async def notify_payment_overdue(
    landlord_id: str,
    tenant_name: str,
    amount: float,
    property_name: str,
    payment_id: str,
    session: Session,
):
    """
    Send a payment overdue notification.
    """
    notification = Notification(
        landlord_id=landlord_id,
        type=NotificationType.PAYMENT_OVERDUE,
        title="Payment Overdue",
        message=f"{tenant_name}'s payment of ${amount:,.2f} for {property_name} is now overdue",
        payment_id=payment_id,
    )
    session.add(notification)
    session.commit()

    await broadcast_to_landlord(
        landlord_id,
        "payment_overdue",
        {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "payment_id": payment_id,
            "created_at": notification.created_at.isoformat(),
        },
    )


async def notify_payment_received(
    landlord_id: str,
    tenant_name: str,
    amount: float,
    property_name: str,
    payment_id: str,
    session: Session,
):
    """
    Send a payment received notification.
    """
    notification = Notification(
        landlord_id=landlord_id,
        type=NotificationType.PAYMENT_RECEIVED,
        title="Payment Received",
        message=f"Received ${amount:,.2f} from {tenant_name} for {property_name}",
        payment_id=payment_id,
    )
    session.add(notification)
    session.commit()

    await broadcast_to_landlord(
        landlord_id,
        "payment_received",
        {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "payment_id": payment_id,
            "created_at": notification.created_at.isoformat(),
        },
    )


async def notify_tenant_added(
    landlord_id: str,
    tenant_name: str,
    property_name: str,
    room_name: str,
    tenant_id: str,
    session: Session,
):
    """
    Send a tenant added notification.
    """
    notification = Notification(
        landlord_id=landlord_id,
        type=NotificationType.TENANT_ADDED,
        title="New Tenant Added",
        message=f"{tenant_name} has been added to {room_name} at {property_name}",
        tenant_id=tenant_id,
    )
    session.add(notification)
    session.commit()

    await broadcast_to_landlord(
        landlord_id,
        "tenant_added",
        {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "tenant_id": tenant_id,
            "created_at": notification.created_at.isoformat(),
        },
    )


async def notify_reminder_sent(
    landlord_id: str,
    tenant_name: str,
    method: str,  # "email", "sms", or "both"
    payment_id: str,
    session: Session,
    created_at: datetime | None = None,
):
    """
    Send a notification that a reminder was sent.
    """
    notification = Notification(
        landlord_id=landlord_id,
        type=NotificationType.REMINDER_SENT,
        title="Reminder Sent",
        message=f"Payment reminder sent to {tenant_name} via {method}",
        payment_id=payment_id,
        created_at=created_at or datetime.now(timezone.utc),
    )
    session.add(notification)
    session.commit()

    await broadcast_to_landlord(
        landlord_id,
        "reminder_sent",
        {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "payment_id": payment_id,
            "created_at": notification.created_at.isoformat(),
        },
    )


def get_active_connections_count(landlord_id: str) -> int:
    """Get the number of active SSE connections for a landlord."""
    if landlord_id not in _connections:
        return 0
    return len(_connections[landlord_id])


def get_active_tenant_connections_count(tenant_id: str) -> int:
    """Get the number of active SSE connections for a tenant."""
    if tenant_id not in _tenant_connections:
        return 0
    return len(_tenant_connections[tenant_id])

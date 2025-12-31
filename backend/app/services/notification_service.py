"""
In-app notification service using Server-Sent Events (SSE).
"""

import asyncio
import json
from typing import Dict, Set, AsyncGenerator
from datetime import datetime
from sqlmodel import Session

from app.models.notification import Notification, NotificationType


# Store active SSE connections per landlord
# landlord_id -> set of async queues
_connections: Dict[str, Set[asyncio.Queue]] = {}


async def subscribe(landlord_id: str) -> AsyncGenerator[str, None]:
    """
    Subscribe to notifications for a landlord.
    Yields SSE-formatted events.
    """
    queue: asyncio.Queue = asyncio.Queue()

    # Register this connection
    if landlord_id not in _connections:
        _connections[landlord_id] = set()
    _connections[landlord_id].add(queue)

    try:
        # Send initial connection event
        yield format_sse_event(
            "connected", {"message": "Connected to notification stream"}
        )

        # Keep connection alive and yield events
        while True:
            try:
                # Wait for events with timeout (for keep-alive)
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield event
            except asyncio.TimeoutError:
                # Send keep-alive ping
                yield format_sse_event(
                    "ping", {"timestamp": datetime.utcnow().isoformat()}
                )
    finally:
        # Cleanup on disconnect
        _connections[landlord_id].discard(queue)
        if not _connections[landlord_id]:
            del _connections[landlord_id]


def format_sse_event(event_type: str, data: dict) -> str:
    """Format data as an SSE event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def broadcast_to_landlord(landlord_id: str, event_type: str, data: dict):
    """
    Broadcast an event to all connections for a landlord.
    """
    if landlord_id not in _connections:
        return

    event = format_sse_event(event_type, data)

    # Send to all connected clients
    for queue in _connections[landlord_id]:
        try:
            await queue.put(event)
        except Exception:
            pass  # Ignore failed sends


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

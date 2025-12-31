"""
SMS notification service (MOCKED).
Logs SMS messages to console for development.
Ready for future integration with Twilio, Africa's Talking, etc.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Store for mock SMS messages (useful for testing)
mock_sms_log = []


async def send_sms(phone_number: str, message: str) -> bool:
    """
    Send an SMS message (MOCKED - logs to console).

    Args:
        phone_number: Recipient phone number
        message: SMS message content (keep under 160 chars for single SMS)

    Returns:
        True (always succeeds in mock mode)
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # Log the SMS
    log_entry = {
        "timestamp": timestamp,
        "to": phone_number,
        "message": message,
        "char_count": len(message),
    }
    mock_sms_log.append(log_entry)

    logger.info(f"[MOCK SMS] To: {phone_number}")
    logger.info(f"[MOCK SMS] Message ({len(message)} chars): {message}")

    # Print to console for visibility during development
    print(f"\n{'=' * 50}")
    print(f"[MOCK SMS] {timestamp}")
    print(f"To: {phone_number}")
    print(f"Message ({len(message)} chars):")
    print(message)
    print(f"{'=' * 50}\n")

    return True


async def send_payment_reminder_sms(
    phone_number: str,
    tenant_name: str,
    amount: float,
    due_date: str,
    property_name: str,
) -> bool:
    """
    Send a payment reminder SMS to a tenant.
    """
    message = (
        f"Hi {tenant_name}, reminder: ${amount:,.2f} rent due {due_date} "
        f"for {property_name}. Please pay on time. - LandTen"
    )
    return await send_sms(phone_number, message)


async def send_overdue_sms(
    phone_number: str, tenant_name: str, amount: float, property_name: str
) -> bool:
    """
    Send an overdue payment SMS to a tenant.
    """
    message = (
        f"URGENT: {tenant_name}, your ${amount:,.2f} rent for {property_name} "
        f"is OVERDUE. Please pay immediately. - LandTen"
    )
    return await send_sms(phone_number, message)


def get_sms_log():
    """
    Get the mock SMS log (useful for testing).
    """
    return mock_sms_log.copy()


def clear_sms_log():
    """
    Clear the mock SMS log.
    """
    mock_sms_log.clear()

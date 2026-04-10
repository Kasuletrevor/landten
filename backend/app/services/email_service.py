"""
Email notification service using Gmail SMTP.
"""

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging
from html import escape

from app.core.config import settings

logger = logging.getLogger(__name__)


def _format_amount(amount: float, currency: Optional[str] = None) -> str:
    if currency:
        return f"{currency} {amount:,.2f}"
    return f"{amount:,.2f}"


def _render_email(
    *,
    heading: str,
    greeting_name: str,
    intro: str,
    details: dict[str, str],
    closing: str,
) -> tuple[str, str]:
    details_html = "".join(
        f"<li><strong>{escape(label)}:</strong> {escape(value)}</li>"
        for label, value in details.items()
        if value
    )
    details_text = "\n".join(
        f"- {label}: {value}" for label, value in details.items() if value
    )

    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #1F2937; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{escape(heading)}</h1>
            </div>
            <div class="content">
                <p>Dear {escape(greeting_name)},</p>
                <p>{escape(intro)}</p>
                <ul>{details_html}</ul>
                <p>{escape(closing)}</p>
            </div>
            <div class="footer">
                <p>This is an automated message from LandTen Property Management.</p>
            </div>
        </div>
    </body>
    </html>
    """

    body_text = (
        f"{heading}\n\n"
        f"Dear {greeting_name},\n\n"
        f"{intro}\n\n"
        f"{details_text}\n\n"
        f"{closing}\n\n"
        "---\n"
        "This is an automated message from LandTen Property Management."
    )
    return body_html, body_text


async def send_email(
    to_email: str, subject: str, body_html: str, body_text: Optional[str] = None
) -> bool:
    """
    Send an email using Gmail SMTP.

    Args:
        to_email: Recipient email address
        subject: Email subject
        body_html: HTML body content
        body_text: Plain text body (optional, will strip HTML if not provided)

    Returns:
        True if email was sent successfully, False otherwise
    """
    if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD:
        logger.warning("Email credentials not configured, skipping email send")
        return False

    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["From"] = settings.MAIL_FROM or settings.MAIL_USERNAME
        message["To"] = to_email
        message["Subject"] = subject

        # Add plain text part
        if body_text:
            part1 = MIMEText(body_text, "plain")
            message.attach(part1)

        # Add HTML part
        part2 = MIMEText(body_html, "html")
        message.attach(part2)

        # Send email
        await aiosmtplib.send(
            message,
            hostname=settings.MAIL_HOST,
            port=settings.MAIL_PORT,
            username=settings.MAIL_USERNAME,
            password=settings.MAIL_PASSWORD,
            use_tls=settings.MAIL_PORT == 465,
            start_tls=settings.MAIL_PORT == 587,
        )

        logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


async def send_payment_reminder(
    tenant_name: str,
    tenant_email: str,
    amount: float,
    due_date: str,
    property_name: str,
    room_name: str,
    landlord_name: str,
    currency: Optional[str] = None,
) -> bool:
    """
    Send a payment reminder email to a tenant.
    """
    subject = f"Payment Reminder - {property_name}"

    body_html, body_text = _render_email(
        heading="Payment Reminder",
        greeting_name=tenant_name,
        intro="This is a friendly reminder that your rent payment is due.",
        details={
            "Property": property_name,
            "Room": room_name,
            "Amount Due": _format_amount(amount, currency),
            "Due Date": due_date,
            "Landlord": landlord_name,
        },
        closing=(
            "Please ensure your payment is made on time to avoid any late fees. "
            "If you have already made this payment, please disregard this reminder."
        ),
    )

    return await send_email(tenant_email, subject, body_html, body_text)


async def send_overdue_notice(
    tenant_name: str,
    tenant_email: str,
    amount: float,
    due_date: str,
    property_name: str,
    room_name: str,
    landlord_name: str,
    currency: Optional[str] = None,
) -> bool:
    """
    Send an overdue payment notice to a tenant.
    """
    subject = f"OVERDUE: Payment Notice - {property_name}"

    body_html, body_text = _render_email(
        heading="Overdue Payment Notice",
        greeting_name=tenant_name,
        intro="Your rent payment is now overdue.",
        details={
            "Property": property_name,
            "Room": room_name,
            "Amount Due": _format_amount(amount, currency),
            "Original Due Date": due_date,
            "Landlord": landlord_name,
        },
        closing=(
            "Please make your payment as soon as possible to avoid additional penalties. "
            "If you have already made this payment, please contact your landlord with the payment reference."
        ),
    )

    return await send_email(tenant_email, subject, body_html, body_text)


async def send_receipt_rejected(
    *,
    tenant_name: str,
    tenant_email: str,
    amount: float,
    currency: Optional[str],
    property_name: str,
    room_name: Optional[str],
    landlord_name: str,
    rejection_reason: str,
) -> bool:
    subject = f"Receipt Rejected - {property_name}"
    body_html, body_text = _render_email(
        heading="Payment Receipt Rejected",
        greeting_name=tenant_name,
        intro=(
            "Your landlord reviewed the payment receipt you uploaded and rejected it."
        ),
        details={
            "Property": property_name,
            "Room": room_name or "Not specified",
            "Amount": _format_amount(amount, currency),
            "Reason": rejection_reason,
            "Landlord": landlord_name,
        },
        closing="Please upload a corrected receipt or reply in the payment discussion thread.",
    )
    return await send_email(tenant_email, subject, body_html, body_text)


async def send_payment_dispute_update(
    *,
    recipient_name: str,
    recipient_email: str,
    actor_name: str,
    property_name: str,
    room_name: Optional[str],
    amount: float,
    currency: Optional[str],
    message: str,
    has_attachment: bool = False,
) -> bool:
    subject = f"Payment Discussion Update - {property_name}"
    body_html, body_text = _render_email(
        heading="Payment Discussion Updated",
        greeting_name=recipient_name,
        intro=f"{actor_name} added a new message to a payment discussion.",
        details={
            "Property": property_name,
            "Room": room_name or "Not specified",
            "Amount": _format_amount(amount, currency),
            "Attachment": "Included" if has_attachment else "None",
            "Message": message,
        },
        closing="Open LandTen to review the discussion and respond if needed.",
    )
    return await send_email(recipient_email, subject, body_html, body_text)


async def send_maintenance_update(
    *,
    recipient_name: str,
    recipient_email: str,
    actor_name: str,
    property_name: str,
    room_name: Optional[str],
    request_title: str,
    update_summary: str,
    message: str,
) -> bool:
    subject = f"Maintenance Update - {property_name}"
    body_html, body_text = _render_email(
        heading="Maintenance Request Update",
        greeting_name=recipient_name,
        intro=f"{actor_name} updated a maintenance request.",
        details={
            "Property": property_name,
            "Room": room_name or "Not specified",
            "Request": request_title,
            "Update": update_summary,
            "Message": message,
        },
        closing="Open LandTen to review the request details and next steps.",
    )
    return await send_email(recipient_email, subject, body_html, body_text)

"""
Email notification service using Gmail SMTP.
"""

import asyncio
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


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
            use_tls=True,  # Gmail requires TLS on port 465
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
) -> bool:
    """
    Send a payment reminder email to a tenant.
    """
    subject = f"Payment Reminder - {property_name}"

    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4F46E5; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .amount {{ font-size: 24px; font-weight: bold; color: #4F46E5; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Payment Reminder</h1>
            </div>
            <div class="content">
                <p>Dear {tenant_name},</p>
                
                <p>This is a friendly reminder that your rent payment is due.</p>
                
                <p><strong>Details:</strong></p>
                <ul>
                    <li>Property: {property_name}</li>
                    <li>Room: {room_name}</li>
                    <li>Amount Due: <span class="amount">${amount:,.2f}</span></li>
                    <li>Due Date: {due_date}</li>
                </ul>
                
                <p>Please ensure your payment is made on time to avoid any late fees.</p>
                
                <p>If you have already made this payment, please disregard this reminder.</p>
                
                <p>Best regards,<br>{landlord_name}</p>
            </div>
            <div class="footer">
                <p>This is an automated message from LandTen Property Management.</p>
            </div>
        </div>
    </body>
    </html>
    """

    body_text = f"""
    Payment Reminder
    
    Dear {tenant_name},
    
    This is a friendly reminder that your rent payment is due.
    
    Details:
    - Property: {property_name}
    - Room: {room_name}
    - Amount Due: ${amount:,.2f}
    - Due Date: {due_date}
    
    Please ensure your payment is made on time to avoid any late fees.
    
    If you have already made this payment, please disregard this reminder.
    
    Best regards,
    {landlord_name}
    
    ---
    This is an automated message from LandTen Property Management.
    """

    return await send_email(tenant_email, subject, body_html, body_text)


async def send_overdue_notice(
    tenant_name: str,
    tenant_email: str,
    amount: float,
    due_date: str,
    property_name: str,
    room_name: str,
    landlord_name: str,
) -> bool:
    """
    Send an overdue payment notice to a tenant.
    """
    subject = f"OVERDUE: Payment Notice - {property_name}"

    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #DC2626; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .amount {{ font-size: 24px; font-weight: bold; color: #DC2626; }}
            .urgent {{ color: #DC2626; font-weight: bold; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>OVERDUE Payment Notice</h1>
            </div>
            <div class="content">
                <p>Dear {tenant_name},</p>
                
                <p class="urgent">Your rent payment is now OVERDUE.</p>
                
                <p><strong>Details:</strong></p>
                <ul>
                    <li>Property: {property_name}</li>
                    <li>Room: {room_name}</li>
                    <li>Amount Due: <span class="amount">${amount:,.2f}</span></li>
                    <li>Original Due Date: {due_date}</li>
                </ul>
                
                <p>Please make your payment as soon as possible to avoid any additional penalties.</p>
                
                <p>If you have already made this payment, please contact us with your payment reference.</p>
                
                <p>Best regards,<br>{landlord_name}</p>
            </div>
            <div class="footer">
                <p>This is an automated message from LandTen Property Management.</p>
            </div>
        </div>
    </body>
    </html>
    """

    body_text = f"""
    OVERDUE Payment Notice
    
    Dear {tenant_name},
    
    Your rent payment is now OVERDUE.
    
    Details:
    - Property: {property_name}
    - Room: {room_name}
    - Amount Due: ${amount:,.2f}
    - Original Due Date: {due_date}
    
    Please make your payment as soon as possible to avoid any additional penalties.
    
    If you have already made this payment, please contact us with your payment reference.
    
    Best regards,
    {landlord_name}
    
    ---
    This is an automated message from LandTen Property Management.
    """

    return await send_email(tenant_email, subject, body_html, body_text)

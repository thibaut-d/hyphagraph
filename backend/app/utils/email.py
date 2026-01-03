"""
Email service for sending verification emails and notifications.

Supports SMTP-based email sending with async support.
"""
import asyncio
import logging
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


def generate_verification_token() -> str:
    """
    Generate a secure random verification token.

    Returns:
        URL-safe random token (32 bytes = 43 characters in base64)
    """
    return secrets.token_urlsafe(32)


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str | None = None,
) -> bool:
    """
    Send an email using SMTP.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email body
        text_content: Plain text email body (optional, falls back to HTML)

    Returns:
        True if email sent successfully, False otherwise
    """
    if not settings.EMAIL_ENABLED:
        logger.info(f"Email sending disabled. Would have sent to {to_email}: {subject}")
        return False

    if not settings.SMTP_HOST:
        logger.error("SMTP_HOST not configured but EMAIL_ENABLED is True")
        return False

    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
        message["To"] = to_email
        message["Subject"] = subject

        # Add text and HTML parts
        if text_content:
            part1 = MIMEText(text_content, "plain")
            message.attach(part1)

        part2 = MIMEText(html_content, "html")
        message.attach(part2)

        # Send email with timeout to prevent hanging
        try:
            if settings.SMTP_TLS:
                # Use STARTTLS
                await asyncio.wait_for(
                    aiosmtplib.send(
                        message,
                        hostname=settings.SMTP_HOST,
                        port=settings.SMTP_PORT,
                        username=settings.SMTP_USER,
                        password=settings.SMTP_PASSWORD,
                        start_tls=True,
                    ),
                    timeout=10.0  # 10 second timeout for email sending
                )
            else:
                # Use SSL or no encryption
                await asyncio.wait_for(
                    aiosmtplib.send(
                        message,
                        hostname=settings.SMTP_HOST,
                        port=settings.SMTP_PORT,
                        username=settings.SMTP_USER,
                        password=settings.SMTP_PASSWORD,
                        use_tls=True if settings.SMTP_PORT == 465 else False,
                    ),
                    timeout=10.0  # 10 second timeout for email sending
                )
        except asyncio.TimeoutError:
            logger.error(f"Email sending to {to_email} timed out after 10 seconds")
            return False

        logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


async def send_verification_email(to_email: str, verification_token: str) -> bool:
    """
    Send email verification link to user.

    Args:
        to_email: Recipient email address
        verification_token: Verification token

    Returns:
        True if email sent successfully, False otherwise
    """
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"

    subject = f"Verify your {settings.EMAIL_FROM_NAME} account"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verify Your Email</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #f4f4f4; padding: 20px; border-radius: 5px;">
            <h1 style="color: #2c3e50; margin-top: 0;">Welcome to {settings.EMAIL_FROM_NAME}!</h1>

            <p>Thank you for registering. Please verify your email address to complete your registration.</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}"
                   style="background-color: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                    Verify Email Address
                </a>
            </div>

            <p style="color: #666; font-size: 14px;">
                If the button above doesn't work, copy and paste this link into your browser:
            </p>
            <p style="background-color: #fff; padding: 10px; border-radius: 3px; word-break: break-all; font-size: 12px;">
                {verification_url}
            </p>

            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                This verification link will expire in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours.
            </p>

            <p style="color: #999; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                If you didn't create an account with {settings.EMAIL_FROM_NAME}, you can safely ignore this email.
            </p>
        </div>
    </body>
    </html>
    """

    text_content = f"""
    Welcome to {settings.EMAIL_FROM_NAME}!

    Thank you for registering. Please verify your email address to complete your registration.

    Click the following link to verify your email:
    {verification_url}

    This verification link will expire in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours.

    If you didn't create an account with {settings.EMAIL_FROM_NAME}, you can safely ignore this email.
    """

    return await send_email(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
    )


async def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """
    Send password reset link to user.

    Args:
        to_email: Recipient email address
        reset_token: Password reset token

    Returns:
        True if email sent successfully, False otherwise
    """
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    subject = f"Reset your {settings.EMAIL_FROM_NAME} password"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reset Your Password</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #f4f4f4; padding: 20px; border-radius: 5px;">
            <h1 style="color: #2c3e50; margin-top: 0;">Password Reset Request</h1>

            <p>We received a request to reset your password. Click the button below to create a new password:</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}"
                   style="background-color: #e74c3c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                    Reset Password
                </a>
            </div>

            <p style="color: #666; font-size: 14px;">
                If the button above doesn't work, copy and paste this link into your browser:
            </p>
            <p style="background-color: #fff; padding: 10px; border-radius: 3px; word-break: break-all; font-size: 12px;">
                {reset_url}
            </p>

            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                This password reset link will expire in 1 hour.
            </p>

            <p style="color: #999; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.
            </p>
        </div>
    </body>
    </html>
    """

    text_content = f"""
    Password Reset Request

    We received a request to reset your password. Click the following link to create a new password:
    {reset_url}

    This password reset link will expire in 1 hour.

    If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.
    """

    return await send_email(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
    )

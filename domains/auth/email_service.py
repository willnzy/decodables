"""
EmailService — Send verification and password reset emails via Resend.

Generates secure tokens (SHA-256 hashed for storage) and sends
transactional emails through the Resend API.
"""

from __future__ import annotations

import logging
from typing import Optional

import resend

from .token_service import TokenService

logger = logging.getLogger(__name__)


class EmailService:
    """
    Domain service for auth-related email delivery.

    Responsibilities:
    - Send email verification links
    - Send password reset links
    - Generate secure tokens (plaintext for email, hash for storage)
    """

    def __init__(
        self,
        resend_api_key: str,
        from_email: str,
        frontend_url: str,
        app_name: str = "Make Decodables",
    ) -> None:
        """
        Initialize EmailService.

        Args:
            resend_api_key: Resend API key.
            from_email: Sender email address (e.g., noreply@makedecodables.com).
            frontend_url: Frontend base URL for building verification/reset links.
            app_name: Application name for email templates.
        """
        self._from_email = from_email
        self._frontend_url = frontend_url.rstrip("/")
        self._app_name = app_name
        resend.api_key = resend_api_key

    # -------------------------------------------------------------------
    # Email Verification
    # -------------------------------------------------------------------

    async def send_verification_email(
        self,
        to_email: str,
        token_plaintext: str,
    ) -> bool:
        """
        Send email verification link to user.

        Args:
            to_email: Recipient email address.
            token_plaintext: Plaintext verification token (included in link).

        Returns:
            True if email was sent successfully, False otherwise.
        """
        verification_url = (
            f"{self._frontend_url}/auth/verify-email"
            f"?token={token_plaintext}&email={to_email}"
        )

        subject = f"Verify your email — {self._app_name}"
        html_body = self._render_verification_email(to_email, verification_url)

        return await self._send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
        )

    # -------------------------------------------------------------------
    # Password Reset
    # -------------------------------------------------------------------

    async def send_password_reset_email(
        self,
        to_email: str,
        token_plaintext: str,
    ) -> bool:
        """
        Send password reset link to user.

        Args:
            to_email: Recipient email address.
            token_plaintext: Plaintext reset token (included in link).

        Returns:
            True if email was sent successfully, False otherwise.
        """
        reset_url = (
            f"{self._frontend_url}/auth/reset-password"
            f"?token={token_plaintext}&email={to_email}"
        )

        subject = f"Reset your password — {self._app_name}"
        html_body = self._render_password_reset_email(to_email, reset_url)

        return await self._send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
        )

    # -------------------------------------------------------------------
    # Internal: Send via Resend
    # -------------------------------------------------------------------

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
    ) -> bool:
        """
        Send an email via Resend API.

        Args:
            to_email: Recipient address.
            subject: Email subject.
            html_body: Email HTML body.

        Returns:
            True if sent successfully, False otherwise.
        """
        try:
            params: resend.Emails.SendParams = {
                "from": f"{self._app_name} <{self._from_email}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
            resend.Emails.send(params)
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
        except Exception:
            logger.exception(f"Failed to send email to {to_email}: {subject}")
            return False

    # -------------------------------------------------------------------
    # Email Templates (inline HTML — simple and portable)
    # -------------------------------------------------------------------

    def _render_verification_email(
        self,
        email: str,
        verification_url: str,
    ) -> str:
        """Render email verification HTML."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px; color: #1a1a1a;">
    <h1 style="font-size: 24px; font-weight: 600; margin-bottom: 24px;">
        Verify your email address
    </h1>
    <p style="font-size: 16px; line-height: 1.6; margin-bottom: 16px;">
        Thanks for signing up for {self._app_name}! Please verify your email
        address by clicking the button below.
    </p>
    <a href="{verification_url}"
       style="display: inline-block; padding: 12px 32px; background-color: #7C3AED;
              color: #ffffff; text-decoration: none; border-radius: 8px;
              font-size: 16px; font-weight: 500; margin: 24px 0;">
        Verify Email
    </a>
    <p style="font-size: 14px; color: #666; line-height: 1.6; margin-top: 24px;">
        This link will expire in 24 hours. If you didn't create an account,
        you can safely ignore this email.
    </p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0;">
    <p style="font-size: 12px; color: #999;">
        If the button doesn't work, copy and paste this URL into your browser:<br>
        <a href="{verification_url}" style="color: #7C3AED; word-break: break-all;">
            {verification_url}
        </a>
    </p>
</body>
</html>
"""

    def _render_password_reset_email(
        self,
        email: str,
        reset_url: str,
    ) -> str:
        """Render password reset HTML."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px; color: #1a1a1a;">
    <h1 style="font-size: 24px; font-weight: 600; margin-bottom: 24px;">
        Reset your password
    </h1>
    <p style="font-size: 16px; line-height: 1.6; margin-bottom: 16px;">
        We received a request to reset the password for your {self._app_name} account.
        Click the button below to choose a new password.
    </p>
    <a href="{reset_url}"
       style="display: inline-block; padding: 12px 32px; background-color: #7C3AED;
              color: #ffffff; text-decoration: none; border-radius: 8px;
              font-size: 16px; font-weight: 500; margin: 24px 0;">
        Reset Password
    </a>
    <p style="font-size: 14px; color: #666; line-height: 1.6; margin-top: 24px;">
        This link will expire in 1 hour. If you didn't request a password reset,
        you can safely ignore this email — your password won't be changed.
    </p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0;">
    <p style="font-size: 12px; color: #999;">
        If the button doesn't work, copy and paste this URL into your browser:<br>
        <a href="{reset_url}" style="color: #7C3AED; word-break: break-all;">
            {reset_url}
        </a>
    </p>
</body>
</html>
"""

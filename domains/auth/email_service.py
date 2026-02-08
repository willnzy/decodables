"""
EmailService — Send OTP codes and transactional emails via Resend.

Sends numeric OTP codes for:
- Registration (email verification)
- Password reset (forgot password)
- Account deletion verification
- Password change verification
"""

from __future__ import annotations

import logging
from typing import Optional

import resend
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)


def _mask_email(email: str) -> str:
    """Mask email for log output: u***@example.com"""
    if "@" not in email:
        return "***"
    local, domain = email.rsplit("@", 1)
    return f"{local[0]}***@{domain}" if local else f"***@{domain}"


class EmailService:
    """
    Domain service for auth-related email delivery.

    Responsibilities:
    - Send OTP verification codes
    - Send password reset OTP codes
    - Send account-related notification emails
    """

    def __init__(
        self,
        resend_api_key: str,
        from_email: str,
        frontend_url: str,
        app_name: str = "Foliaz",
    ) -> None:
        """
        Initialize EmailService.

        Args:
            resend_api_key: Resend API key.
            from_email: Sender email address (e.g., noreply@foliaz.com).
            frontend_url: Frontend base URL (used in email templates).
            app_name: Application name for email templates.
        """
        self._from_email = from_email
        self._frontend_url = frontend_url.rstrip("/")
        self._app_name = app_name
        resend.api_key = resend_api_key

    # -------------------------------------------------------------------
    # OTP Emails
    # -------------------------------------------------------------------

    async def send_otp_email(
        self,
        to_email: str,
        otp_code: str,
        purpose: str,
    ) -> bool:
        """
        Send an OTP verification code email.

        Args:
            to_email: Recipient email address.
            otp_code: 6-digit OTP code.
            purpose: OTP purpose (register, forgot_password, etc.).

        Returns:
            True if email was sent successfully, False otherwise.
        """
        subject_map = {
            "register": f"Your verification code — {self._app_name}",
            "forgot_password": f"Password reset code — {self._app_name}",
            "change_password": f"Password change verification — {self._app_name}",
            "delete_account": f"Account deletion verification — {self._app_name}",
        }

        subject = subject_map.get(purpose, f"Your verification code — {self._app_name}")
        html_body = self._render_otp_email(to_email, otp_code, purpose)

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
            await run_in_threadpool(resend.Emails.send, params)
            logger.info(f"Email sent to {_mask_email(to_email)}: {subject}")
            return True
        except Exception:
            logger.exception(f"Failed to send email to {_mask_email(to_email)}: {subject}")
            return False

    # -------------------------------------------------------------------
    # Email Templates
    # -------------------------------------------------------------------

    def _render_otp_email(
        self,
        email: str,
        otp_code: str,
        purpose: str,
    ) -> str:
        """Render OTP verification code email HTML."""
        purpose_messages = {
            "register": (
                "Welcome to {app}!",
                "Use the code below to verify your email address and complete your registration.",
            ),
            "forgot_password": (
                "Reset your password",
                "Use the code below to verify your identity and reset your password.",
            ),
            "change_password": (
                "Password change verification",
                "Use the code below to confirm your password change.",
            ),
            "delete_account": (
                "Account deletion verification",
                "Use the code below to confirm your account deletion. This action cannot be undone after the recovery period.",
            ),
        }

        title, description = purpose_messages.get(
            purpose,
            ("Verification code", "Use the code below to verify your identity."),
        )
        title = title.format(app=self._app_name)

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px; color: #1a1a1a;">
    <h1 style="font-size: 24px; font-weight: 600; margin-bottom: 24px;">
        {title}
    </h1>
    <p style="font-size: 16px; line-height: 1.6; margin-bottom: 24px;">
        {description}
    </p>
    <div style="background-color: #f8f9fa; border-radius: 12px; padding: 24px; text-align: center; margin: 24px 0;">
        <p style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #7C3AED; margin: 0; font-family: 'SF Mono', 'Fira Code', monospace;">
            {otp_code}
        </p>
    </div>
    <p style="font-size: 14px; color: #666; line-height: 1.6;">
        This code will expire in 10 minutes. If you didn't request this code,
        you can safely ignore this email.
    </p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0;">
    <p style="font-size: 12px; color: #999;">
        This is an automated message from {self._app_name}. Please do not reply.
    </p>
</body>
</html>
"""

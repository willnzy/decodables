"""
Tests for EmailService — Resend email delivery (mock Resend API).

Covers:
- OTP email sending for all purposes (register, forgot_password, change_password, delete_account)
- Email failure handling
- Template rendering and subject lines
- Configuration (from_email, frontend_url)
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from domains.auth.email_service import EmailService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def email_service() -> EmailService:
    """EmailService with test configuration."""
    return EmailService(
        resend_api_key="re_test_key",
        from_email="noreply@foliaz.com",
        frontend_url="https://foliaz.com",
        app_name="Foliaz",
    )


# ---------------------------------------------------------------------------
# OTP Email — Registration
# ---------------------------------------------------------------------------

class TestSendOtpEmailRegister:

    @pytest.mark.asyncio
    async def test_sends_register_otp_email(self, email_service: EmailService):
        """Registration OTP email is sent via Resend with correct parameters."""
        with patch("domains.auth.email_service.resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "email_123"}

            result = await email_service.send_otp_email(
                to_email="user@example.com",
                otp_code="123456",
                purpose="register",
            )

            assert result is True
            mock_send.assert_called_once()

            call_params = mock_send.call_args[0][0]
            assert call_params["to"] == ["user@example.com"]
            assert "verification code" in call_params["subject"]
            assert "123456" in call_params["html"]

    @pytest.mark.asyncio
    async def test_register_otp_email_contains_otp_code(self, email_service: EmailService):
        """OTP code should appear in the email body."""
        with patch("domains.auth.email_service.resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "email_123"}

            await email_service.send_otp_email(
                to_email="user@example.com",
                otp_code="987654",
                purpose="register",
            )

            html = mock_send.call_args[0][0]["html"]
            assert "987654" in html
            assert "Welcome" in html

    @pytest.mark.asyncio
    async def test_register_otp_email_failure_returns_false(self, email_service: EmailService):
        """If Resend API fails, should return False."""
        with patch("domains.auth.email_service.resend.Emails.send") as mock_send:
            mock_send.side_effect = Exception("API error")

            result = await email_service.send_otp_email(
                to_email="user@example.com",
                otp_code="123456",
                purpose="register",
            )

            assert result is False


# ---------------------------------------------------------------------------
# OTP Email — Password Reset
# ---------------------------------------------------------------------------

class TestSendOtpEmailPasswordReset:

    @pytest.mark.asyncio
    async def test_sends_reset_otp_email(self, email_service: EmailService):
        """Password reset OTP email is sent via Resend."""
        with patch("domains.auth.email_service.resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "email_456"}

            result = await email_service.send_otp_email(
                to_email="user@example.com",
                otp_code="654321",
                purpose="forgot_password",
            )

            assert result is True
            mock_send.assert_called_once()
            call_params = mock_send.call_args[0][0]
            assert "reset" in call_params["subject"].lower()
            assert "654321" in call_params["html"]

    @pytest.mark.asyncio
    async def test_reset_otp_email_body_content(self, email_service: EmailService):
        """Reset email body mentions password reset."""
        with patch("domains.auth.email_service.resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "email_456"}

            await email_service.send_otp_email(
                to_email="user@example.com",
                otp_code="111222",
                purpose="forgot_password",
            )

            html = mock_send.call_args[0][0]["html"]
            assert "111222" in html
            assert "password" in html.lower()

    @pytest.mark.asyncio
    async def test_reset_otp_failure_returns_false(self, email_service: EmailService):
        """API failure returns False."""
        with patch("domains.auth.email_service.resend.Emails.send") as mock_send:
            mock_send.side_effect = Exception("API error")

            result = await email_service.send_otp_email(
                to_email="user@example.com",
                otp_code="123456",
                purpose="forgot_password",
            )

            assert result is False


# ---------------------------------------------------------------------------
# OTP Email — Other Purposes
# ---------------------------------------------------------------------------

class TestSendOtpEmailOtherPurposes:

    @pytest.mark.asyncio
    async def test_change_password_otp_subject(self, email_service: EmailService):
        """Change password OTP has correct subject."""
        with patch("domains.auth.email_service.resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "e"}

            await email_service.send_otp_email(
                to_email="user@example.com",
                otp_code="333444",
                purpose="change_password",
            )

            call_params = mock_send.call_args[0][0]
            assert "change" in call_params["subject"].lower()

    @pytest.mark.asyncio
    async def test_delete_account_otp_subject(self, email_service: EmailService):
        """Delete account OTP has correct subject."""
        with patch("domains.auth.email_service.resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "e"}

            await email_service.send_otp_email(
                to_email="user@example.com",
                otp_code="555666",
                purpose="delete_account",
            )

            call_params = mock_send.call_args[0][0]
            assert "deletion" in call_params["subject"].lower()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class TestEmailServiceConfiguration:

    def test_frontend_url_trailing_slash_stripped(self):
        """Trailing slash on frontend_url should be stripped."""
        service = EmailService(
            resend_api_key="key",
            from_email="noreply@test.com",
            frontend_url="https://example.com/",
        )
        assert service._frontend_url == "https://example.com"

    @pytest.mark.asyncio
    async def test_from_email_in_sender(self):
        """from_email appears in the 'from' field."""
        service = EmailService(
            resend_api_key="key",
            from_email="hello@test.com",
            frontend_url="https://example.com",
            app_name="TestApp",
        )

        with patch("domains.auth.email_service.resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "e"}
            await service.send_otp_email("x@x.com", "123456", "register")
            call_params = mock_send.call_args[0][0]
            assert "hello@test.com" in call_params["from"]
            assert "TestApp" in call_params["from"]

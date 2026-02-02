"""
Tests for EmailService — Resend email delivery (mock Resend API).

Covers:
- Verification email sending
- Password reset email sending
- Email failure handling
- URL construction
- Template rendering
"""

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
        from_email="noreply@makedecodables.com",
        frontend_url="https://makedecodables.com",
        app_name="Make Decodables",
    )


# ---------------------------------------------------------------------------
# Verification Email
# ---------------------------------------------------------------------------

class TestSendVerificationEmail:

    @pytest.mark.asyncio
    async def test_sends_verification_email(self, email_service: EmailService):
        """Verification email is sent via Resend with correct parameters."""
        with patch("domains.auth.email_service.resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "email_123"}

            result = await email_service.send_verification_email(
                to_email="user@example.com",
                token_plaintext="abc123token",
            )

            assert result is True
            mock_send.assert_called_once()

            # Verify the call params
            call_params = mock_send.call_args[0][0]
            assert call_params["to"] == ["user@example.com"]
            assert "Verify" in call_params["subject"]
            assert "abc123token" in call_params["html"]
            assert "verify-email" in call_params["html"]

    @pytest.mark.asyncio
    async def test_verification_email_url_format(self, email_service: EmailService):
        """Verification URL should include token and email."""
        with patch("domains.auth.email_service.resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "email_123"}

            await email_service.send_verification_email(
                to_email="user@example.com",
                token_plaintext="mytoken",
            )

            html = mock_send.call_args[0][0]["html"]
            assert "https://makedecodables.com/auth/verify-email" in html
            assert "token=mytoken" in html
            assert "email=user@example.com" in html

    @pytest.mark.asyncio
    async def test_verification_email_failure_returns_false(self, email_service: EmailService):
        """If Resend API fails, should return False."""
        with patch("domains.auth.email_service.resend.Emails.send") as mock_send:
            mock_send.side_effect = Exception("API error")

            result = await email_service.send_verification_email(
                to_email="user@example.com",
                token_plaintext="token",
            )

            assert result is False


# ---------------------------------------------------------------------------
# Password Reset Email
# ---------------------------------------------------------------------------

class TestSendPasswordResetEmail:

    @pytest.mark.asyncio
    async def test_sends_reset_email(self, email_service: EmailService):
        """Password reset email is sent via Resend."""
        with patch("domains.auth.email_service.resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "email_456"}

            result = await email_service.send_password_reset_email(
                to_email="user@example.com",
                token_plaintext="resettoken",
            )

            assert result is True
            mock_send.assert_called_once()
            call_params = mock_send.call_args[0][0]
            assert "Reset" in call_params["subject"]
            assert "resettoken" in call_params["html"]
            assert "reset-password" in call_params["html"]

    @pytest.mark.asyncio
    async def test_reset_email_url_format(self, email_service: EmailService):
        """Reset URL should include token and email."""
        with patch("domains.auth.email_service.resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "email_456"}

            await email_service.send_password_reset_email(
                to_email="user@example.com",
                token_plaintext="rsttoken",
            )

            html = mock_send.call_args[0][0]["html"]
            assert "https://makedecodables.com/auth/reset-password" in html
            assert "token=rsttoken" in html
            assert "email=user@example.com" in html

    @pytest.mark.asyncio
    async def test_reset_email_failure_returns_false(self, email_service: EmailService):
        """API failure returns False."""
        with patch("domains.auth.email_service.resend.Emails.send") as mock_send:
            mock_send.side_effect = Exception("API error")

            result = await email_service.send_password_reset_email(
                to_email="user@example.com",
                token_plaintext="token",
            )

            assert result is False


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

    def test_from_email_in_sender(self):
        """from_email appears in the 'from' field."""
        service = EmailService(
            resend_api_key="key",
            from_email="hello@test.com",
            frontend_url="https://example.com",
            app_name="TestApp",
        )

        with patch("domains.auth.email_service.resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "e"}
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                service.send_verification_email("x@x.com", "t")
            )
            call_params = mock_send.call_args[0][0]
            assert "hello@test.com" in call_params["from"]
            assert "TestApp" in call_params["from"]

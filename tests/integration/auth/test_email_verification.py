"""
Integration tests for email verification flow.

Tests POST /auth/verify-email and POST /auth/resend-verification
through the full API pipeline.
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from domains.auth.aggregates.auth_user import AuthUser
from domains.auth.token_service import TokenService

from .conftest import TEST_EMAIL, TEST_USER_ID


class TestVerifyEmailEndpoint:

    @pytest.mark.asyncio
    async def test_verify_email_success(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
        int_token_service: TokenService,
    ):
        """POST /auth/verify-email with valid token returns 200."""
        plaintext, token_hash = int_token_service.create_secure_token()
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="h",
            email_verified=False,
            email_verification_token=token_hash,
            email_verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        int_mock_auth_user_repo.get_by_email.return_value = auth_user

        resp = await client.post("/auth/verify-email", json={
            "token": plaintext,
            "email": TEST_EMAIL,
        })

        assert resp.status_code == 200
        assert resp.json()["success"] is True
        int_mock_auth_user_repo.update_email_verified.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
    ):
        """POST /auth/verify-email with wrong token returns 400."""
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="h",
            email_verified=False,
            email_verification_token="stored_hash",
            email_verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        int_mock_auth_user_repo.get_by_email.return_value = auth_user

        resp = await client.post("/auth/verify-email", json={
            "token": "wrong-token",
            "email": TEST_EMAIL,
        })

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_verify_email_expired_token(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
        int_token_service: TokenService,
    ):
        """POST /auth/verify-email with expired token returns 400."""
        plaintext, token_hash = int_token_service.create_secure_token()
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="h",
            email_verified=False,
            email_verification_token=token_hash,
            email_verification_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        int_mock_auth_user_repo.get_by_email.return_value = auth_user

        resp = await client.post("/auth/verify-email", json={
            "token": plaintext,
            "email": TEST_EMAIL,
        })

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_verify_email_unknown_email(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
    ):
        """POST /auth/verify-email with unknown email returns 400."""
        int_mock_auth_user_repo.get_by_email.return_value = None

        resp = await client.post("/auth/verify-email", json={
            "token": "token",
            "email": "unknown@example.com",
        })

        assert resp.status_code == 400


class TestResendVerificationEndpoint:

    @pytest.mark.asyncio
    async def test_resend_verification(self, auth_client: AsyncClient):
        """POST /auth/resend-verification returns 200."""
        resp = await auth_client.post("/auth/resend-verification")
        assert resp.status_code == 200

"""
Integration tests for password reset and change via OTP.

Tests:
- POST /auth/otp/send (forgot_password purpose)
- POST /auth/otp/verify (forgot_password purpose)
- POST /auth/forgot-password/reset
- POST /auth/change-password
through the full API pipeline.
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from domains.auth.aggregates.auth_user import AuthUser
from domains.auth.constants import OTP_PURPOSE_FORGOT_PASSWORD
from domains.auth.token_service import TokenService

from .conftest import TEST_EMAIL, TEST_PASSWORD, TEST_USER_ID


class TestForgotPasswordSendOtpEndpoint:

    @pytest.mark.asyncio
    async def test_send_otp_existing_email(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
        int_mock_email_service,
    ):
        """POST /auth/otp/send with forgot_password sends OTP."""
        auth_user = AuthUser(
            id=TEST_USER_ID, email=TEST_EMAIL, password_hash="h",
        )
        int_mock_auth_user_repo.get_by_email.return_value = auth_user

        resp = await client.post("/auth/otp/send", json={
            "purpose": "forgot_password",
            "email": TEST_EMAIL,
        })

        assert resp.status_code == 200
        assert resp.json()["success"] is True
        int_mock_email_service.send_otp_email.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_otp_unknown_email(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
        int_mock_email_service,
    ):
        """POST /auth/otp/send with unknown email still returns 200 (no enumeration)."""
        int_mock_auth_user_repo.get_by_email.return_value = None

        resp = await client.post("/auth/otp/send", json={
            "purpose": "forgot_password",
            "email": "unknown@example.com",
        })

        assert resp.status_code == 200
        int_mock_email_service.send_otp_email.assert_not_awaited()


class TestForgotPasswordVerifyOtpEndpoint:

    @pytest.mark.asyncio
    async def test_verify_otp_success(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
        int_token_service: TokenService,
    ):
        """POST /auth/otp/verify with correct code returns otp_verified_token."""
        otp_code, otp_hash = int_token_service.generate_otp()
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="hashed",
            otp_code_hash=otp_hash,
            otp_purpose=OTP_PURPOSE_FORGOT_PASSWORD,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            otp_attempts=0,
        )
        int_mock_auth_user_repo.get_by_email.return_value = auth_user

        resp = await client.post("/auth/otp/verify", json={
            "purpose": "forgot_password",
            "otp_code": otp_code,
            "email": TEST_EMAIL,
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "otp_verified_token" in data

    @pytest.mark.asyncio
    async def test_verify_otp_wrong_code(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
        int_token_service: TokenService,
    ):
        """POST /auth/otp/verify with wrong code returns 400."""
        otp_code, otp_hash = int_token_service.generate_otp()
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="hashed",
            otp_code_hash=otp_hash,
            otp_purpose=OTP_PURPOSE_FORGOT_PASSWORD,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            otp_attempts=0,
        )
        int_mock_auth_user_repo.get_by_email.return_value = auth_user

        resp = await client.post("/auth/otp/verify", json={
            "purpose": "forgot_password",
            "otp_code": "000000",
            "email": TEST_EMAIL,
        })

        assert resp.status_code == 400


class TestForgotPasswordResetEndpoint:

    @pytest.mark.asyncio
    async def test_reset_password_success(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
        int_mock_session_repo,
        int_token_service: TokenService,
    ):
        """POST /auth/forgot-password/reset with valid token resets password."""
        auth_user = AuthUser(
            id=TEST_USER_ID, email=TEST_EMAIL, password_hash="old_hash",
        )
        int_mock_auth_user_repo.get_by_id.return_value = auth_user

        # Create an otp_verified_token
        otp_verified_token = int_token_service.create_purpose_token(
            user_id=TEST_USER_ID,
            purpose="otp_verified_forgot_password",
            expire_minutes=10,
        )

        resp = await client.post("/auth/forgot-password/reset", json={
            "otp_verified_token": otp_verified_token,
            "new_password": "NewStrong1Pass",
        })

        assert resp.status_code == 200
        int_mock_auth_user_repo.update_password.assert_awaited_once()
        int_mock_session_repo.revoke_all_by_user.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reset_password_weak_new_password(
        self,
        client: AsyncClient,
        int_token_service: TokenService,
    ):
        """POST /auth/forgot-password/reset with weak password returns 422."""
        otp_verified_token = int_token_service.create_purpose_token(
            user_id=TEST_USER_ID,
            purpose="otp_verified_forgot_password",
            expire_minutes=10,
        )

        resp = await client.post("/auth/forgot-password/reset", json={
            "otp_verified_token": otp_verified_token,
            "new_password": "weak",
        })

        # Pydantic validation catches min_length=8
        assert resp.status_code == 422


class TestChangePasswordEndpoint:

    @pytest.mark.asyncio
    async def test_change_password_success(
        self,
        auth_client: AsyncClient,
        int_mock_auth_user_repo,
        int_password_service,
        int_token_service: TokenService,
    ):
        """POST /auth/change-password with correct current password returns 200."""
        current_hash = int_password_service.hash_password(TEST_PASSWORD)
        auth_user = AuthUser(
            id=TEST_USER_ID, email=TEST_EMAIL, password_hash=current_hash,
        )
        int_mock_auth_user_repo.get_by_id.return_value = auth_user

        # Create an otp_verified_token for change_password
        otp_verified_token = int_token_service.create_purpose_token(
            user_id=TEST_USER_ID,
            purpose="otp_verified_change_password",
            expire_minutes=10,
        )

        resp = await auth_client.post("/auth/change-password", json={
            "otp_verified_token": otp_verified_token,
            "current_password": TEST_PASSWORD,
            "new_password": "NewStrong1Pass",
        })

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self,
        auth_client: AsyncClient,
        int_mock_auth_user_repo,
        int_password_service,
        int_token_service: TokenService,
    ):
        """POST /auth/change-password with wrong current password returns 401."""
        current_hash = int_password_service.hash_password(TEST_PASSWORD)
        auth_user = AuthUser(
            id=TEST_USER_ID, email=TEST_EMAIL, password_hash=current_hash,
        )
        int_mock_auth_user_repo.get_by_id.return_value = auth_user

        otp_verified_token = int_token_service.create_purpose_token(
            user_id=TEST_USER_ID,
            purpose="otp_verified_change_password",
            expire_minutes=10,
        )

        resp = await auth_client.post("/auth/change-password", json={
            "otp_verified_token": otp_verified_token,
            "current_password": "WrongPassword1",
            "new_password": "NewStrong1Pass",
        })

        assert resp.status_code == 401

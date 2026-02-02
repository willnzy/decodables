"""
Integration tests for Auth API — Registration (3-step OTP), Login, Refresh, Logout.

Tests the full request→router→service→response pipeline with
mocked repositories.
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from domains.auth.aggregates.auth_user import AuthUser
from domains.auth.aggregates.session import Session
from domains.auth.constants import OTP_PURPOSE_REGISTER

from .conftest import TEST_EMAIL, TEST_PASSWORD, TEST_USER_ID


# ===========================================================================
# Registration — 3-Step OTP
# ===========================================================================

class TestRegisterSendOtpEndpoint:

    @pytest.mark.asyncio
    async def test_send_otp_success(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
        int_mock_email_service,
    ):
        """POST /auth/register/send-otp returns 200 with success message."""
        pending_user = AuthUser.create_pending(
            email=TEST_EMAIL,
            otp_code_hash="hashed",
            otp_purpose=OTP_PURPOSE_REGISTER,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            user_id=TEST_USER_ID,
        )
        int_mock_auth_user_repo.create_pending.return_value = (pending_user, True)
        int_mock_auth_user_repo.get_restorable_by_email.return_value = None

        resp = await client.post("/auth/register/send-otp", json={
            "email": TEST_EMAIL,
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        int_mock_email_service.send_otp_email.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_otp_invalid_email(self, client: AsyncClient):
        """POST /auth/register/send-otp with invalid email returns 422."""
        resp = await client.post("/auth/register/send-otp", json={
            "email": "not-an-email",
        })

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_send_otp_duplicate_email(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
    ):
        """POST /auth/register/send-otp with existing email returns 409."""
        registered_user = AuthUser.create_registered(
            email=TEST_EMAIL, password_hash="hashed", user_id=TEST_USER_ID,
        )
        int_mock_auth_user_repo.get_restorable_by_email.return_value = None
        int_mock_auth_user_repo.create_pending.return_value = (registered_user, False)

        resp = await client.post("/auth/register/send-otp", json={
            "email": TEST_EMAIL,
        })

        assert resp.status_code == 409


class TestRegisterVerifyOtpEndpoint:

    @pytest.mark.asyncio
    async def test_verify_otp_success(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
        int_token_service,
    ):
        """POST /auth/register/verify-otp returns 200 with register_token."""
        otp_code, otp_hash = int_token_service.generate_otp()
        pending_user = AuthUser.create_pending(
            email=TEST_EMAIL,
            otp_code_hash=otp_hash,
            otp_purpose=OTP_PURPOSE_REGISTER,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            user_id=TEST_USER_ID,
        )
        int_mock_auth_user_repo.get_by_email.return_value = pending_user

        resp = await client.post("/auth/register/verify-otp", json={
            "email": TEST_EMAIL,
            "otp_code": otp_code,
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "register_token" in data

    @pytest.mark.asyncio
    async def test_verify_otp_wrong_code(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
        int_token_service,
    ):
        """POST /auth/register/verify-otp with wrong code returns 400."""
        otp_code, otp_hash = int_token_service.generate_otp()
        pending_user = AuthUser.create_pending(
            email=TEST_EMAIL,
            otp_code_hash=otp_hash,
            otp_purpose=OTP_PURPOSE_REGISTER,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            user_id=TEST_USER_ID,
        )
        int_mock_auth_user_repo.get_by_email.return_value = pending_user

        resp = await client.post("/auth/register/verify-otp", json={
            "email": TEST_EMAIL,
            "otp_code": "000000",
        })

        assert resp.status_code == 400


class TestRegisterCompleteEndpoint:

    @pytest.mark.asyncio
    async def test_complete_registration_success(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
        int_mock_session_repo,
        int_token_service,
    ):
        """POST /auth/register/complete with valid token returns 200 with tokens."""
        # Set up pending user
        pending_user = AuthUser.create_pending(
            email=TEST_EMAIL,
            otp_code_hash="verified_hash",
            otp_purpose=OTP_PURPOSE_REGISTER,
            otp_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            user_id=TEST_USER_ID,
        )
        completed_user = AuthUser.create_registered(
            email=TEST_EMAIL, password_hash="hashed", user_id=TEST_USER_ID,
        )
        int_mock_auth_user_repo.get_by_id.return_value = pending_user
        int_mock_auth_user_repo.complete_registration.return_value = completed_user

        # Create a register_token
        register_token = int_token_service.create_purpose_token(
            user_id=TEST_USER_ID,
            purpose="register",
            expire_minutes=15,
        )

        resp = await client.post("/auth/register/complete", json={
            "register_token": register_token,
            "password": TEST_PASSWORD,
        })

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == TEST_EMAIL


# ===========================================================================
# Login
# ===========================================================================

class TestLoginEndpoint:

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
        int_mock_session_repo,
        int_password_service,
    ):
        """POST /auth/login returns 200 with tokens."""
        real_hash = int_password_service.hash_password(TEST_PASSWORD)
        auth_user = AuthUser(
            id=TEST_USER_ID, email=TEST_EMAIL,
            password_hash=real_hash, is_active=True,
        )
        int_mock_auth_user_repo.get_by_email.return_value = auth_user
        int_mock_session_repo.count_active_by_user.return_value = 0

        resp = await client.post("/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        })

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
        int_password_service,
    ):
        """POST /auth/login with wrong password returns 401."""
        real_hash = int_password_service.hash_password(TEST_PASSWORD)
        auth_user = AuthUser(
            id=TEST_USER_ID, email=TEST_EMAIL,
            password_hash=real_hash, is_active=True,
        )
        int_mock_auth_user_repo.get_by_email.return_value = auth_user

        resp = await client.post("/auth/login", json={
            "email": TEST_EMAIL,
            "password": "WrongPassword1",
        })

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_email(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
    ):
        """POST /auth/login with unknown email returns 401."""
        int_mock_auth_user_repo.get_by_email.return_value = None

        resp = await client.post("/auth/login", json={
            "email": "unknown@example.com",
            "password": TEST_PASSWORD,
        })

        assert resp.status_code == 401


# ===========================================================================
# Token Refresh
# ===========================================================================

class TestRefreshEndpoint:

    @pytest.mark.asyncio
    async def test_refresh_success(
        self,
        client: AsyncClient,
        int_mock_session_repo,
        int_mock_auth_user_repo,
    ):
        """POST /auth/refresh returns new access token."""
        session = Session.create_new(
            user_id=TEST_USER_ID, refresh_token_hash="hash",
        )
        auth_user = AuthUser(
            id=TEST_USER_ID, email=TEST_EMAIL,
            password_hash="h", is_active=True,
        )
        int_mock_session_repo.get_by_token_hash.return_value = session
        int_mock_auth_user_repo.get_by_id.return_value = auth_user

        resp = await client.post("/auth/refresh", json={
            "refresh_token": "some-refresh-token",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(
        self,
        client: AsyncClient,
        int_mock_session_repo,
    ):
        """POST /auth/refresh with unknown token returns 401."""
        int_mock_session_repo.get_by_token_hash.return_value = None

        resp = await client.post("/auth/refresh", json={
            "refresh_token": "invalid-token",
        })

        assert resp.status_code == 401


# ===========================================================================
# Logout
# ===========================================================================

class TestLogoutEndpoint:

    @pytest.mark.asyncio
    async def test_logout_success(
        self,
        client: AsyncClient,
        int_mock_session_repo,
    ):
        """POST /auth/logout returns 200."""
        session = Session.create_new(
            user_id=TEST_USER_ID, refresh_token_hash="h",
        )
        int_mock_session_repo.get_by_token_hash.return_value = session

        resp = await client.post("/auth/logout", json={
            "refresh_token": "some-token",
        })

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_logout_all(self, auth_client: AsyncClient):
        """POST /auth/logout-all returns 200."""
        resp = await auth_client.post("/auth/logout-all")
        assert resp.status_code == 200

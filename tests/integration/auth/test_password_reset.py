"""
Integration tests for password reset flow.

Tests POST /auth/forgot-password, POST /auth/reset-password,
and POST /auth/change-password through the full API pipeline.
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from domains.auth.aggregates.auth_user import AuthUser
from domains.auth.token_service import TokenService

from .conftest import TEST_EMAIL, TEST_PASSWORD, TEST_USER_ID


class TestForgotPasswordEndpoint:

    @pytest.mark.asyncio
    async def test_forgot_password_existing_email(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
        int_mock_email_service,
    ):
        """POST /auth/forgot-password with valid email sends reset email."""
        auth_user = AuthUser(
            id=TEST_USER_ID, email=TEST_EMAIL, password_hash="h",
        )
        int_mock_auth_user_repo.get_by_email.return_value = auth_user

        resp = await client.post("/auth/forgot-password", json={
            "email": TEST_EMAIL,
        })

        assert resp.status_code == 200
        assert resp.json()["success"] is True
        int_mock_email_service.send_password_reset_email.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_forgot_password_unknown_email(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
        int_mock_email_service,
    ):
        """POST /auth/forgot-password with unknown email still returns 200 (no enumeration)."""
        int_mock_auth_user_repo.get_by_email.return_value = None

        resp = await client.post("/auth/forgot-password", json={
            "email": "unknown@example.com",
        })

        assert resp.status_code == 200
        int_mock_email_service.send_password_reset_email.assert_not_awaited()


class TestResetPasswordEndpoint:

    @pytest.mark.asyncio
    async def test_reset_password_success(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
        int_mock_session_repo,
        int_token_service: TokenService,
    ):
        """POST /auth/reset-password with valid token resets password."""
        plaintext, token_hash = int_token_service.create_secure_token()
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="old_hash",
            password_reset_token=token_hash,
            password_reset_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        int_mock_auth_user_repo.get_by_email.return_value = auth_user

        resp = await client.post("/auth/reset-password", json={
            "token": plaintext,
            "email": TEST_EMAIL,
            "new_password": "NewStrong1Pass",
        })

        assert resp.status_code == 200
        int_mock_auth_user_repo.update_password.assert_awaited_once()
        int_mock_session_repo.revoke_all_by_user.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
    ):
        """POST /auth/reset-password with wrong token returns 400."""
        auth_user = AuthUser(
            id=TEST_USER_ID,
            email=TEST_EMAIL,
            password_hash="h",
            password_reset_token="stored_hash",
            password_reset_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        int_mock_auth_user_repo.get_by_email.return_value = auth_user

        resp = await client.post("/auth/reset-password", json={
            "token": "wrong-token",
            "email": TEST_EMAIL,
            "new_password": "NewStrong1Pass",
        })

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_reset_password_weak_new_password(
        self,
        client: AsyncClient,
    ):
        """POST /auth/reset-password with weak password returns 422."""
        resp = await client.post("/auth/reset-password", json={
            "token": "any",
            "email": TEST_EMAIL,
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
    ):
        """POST /auth/change-password with correct current password returns 200."""
        current_hash = int_password_service.hash_password(TEST_PASSWORD)
        auth_user = AuthUser(
            id=TEST_USER_ID, email=TEST_EMAIL, password_hash=current_hash,
        )
        int_mock_auth_user_repo.get_by_id.return_value = auth_user

        resp = await auth_client.post("/auth/change-password", json={
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
    ):
        """POST /auth/change-password with wrong current password returns 401."""
        current_hash = int_password_service.hash_password(TEST_PASSWORD)
        auth_user = AuthUser(
            id=TEST_USER_ID, email=TEST_EMAIL, password_hash=current_hash,
        )
        int_mock_auth_user_repo.get_by_id.return_value = auth_user

        resp = await auth_client.post("/auth/change-password", json={
            "current_password": "WrongPassword1",
            "new_password": "NewStrong1Pass",
        })

        assert resp.status_code == 401

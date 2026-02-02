"""
Integration tests for session management endpoints.

Tests GET /auth/sessions, DELETE /auth/sessions/{id},
and POST /auth/delete-account through the full API pipeline.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from domains.auth.aggregates.auth_user import AuthUser
from domains.auth.aggregates.session import Session
from domains.auth.token_service import TokenService

from .conftest import TEST_EMAIL, TEST_PASSWORD, TEST_USER_ID


class TestListSessionsEndpoint:

    @pytest.mark.asyncio
    async def test_list_sessions(
        self,
        auth_client: AsyncClient,
        int_mock_session_repo,
    ):
        """GET /auth/sessions returns session list."""
        sessions = [
            Session.create_new(user_id=TEST_USER_ID, refresh_token_hash="h1"),
            Session.create_new(user_id=TEST_USER_ID, refresh_token_hash="h2"),
        ]
        int_mock_session_repo.get_active_by_user.return_value = sessions

        resp = await auth_client.get("/auth/sessions")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["sessions"]) == 2

    @pytest.mark.asyncio
    async def test_list_sessions_empty(
        self,
        auth_client: AsyncClient,
        int_mock_session_repo,
    ):
        """GET /auth/sessions with no sessions returns empty list."""
        int_mock_session_repo.get_active_by_user.return_value = []

        resp = await auth_client.get("/auth/sessions")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["sessions"] == []


class TestRevokeSessionEndpoint:

    @pytest.mark.asyncio
    async def test_revoke_session_success(
        self,
        auth_client: AsyncClient,
        int_mock_session_repo,
    ):
        """DELETE /auth/sessions/{id} revokes the session."""
        session_id = uuid4()
        session = Session.create_new(
            user_id=TEST_USER_ID, refresh_token_hash="h",
        )
        session.id = session_id
        int_mock_session_repo.get_active_by_user.return_value = [session]

        resp = await auth_client.delete(f"/auth/sessions/{session_id}")

        assert resp.status_code == 200
        int_mock_session_repo.revoke.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_revoke_session_not_found(
        self,
        auth_client: AsyncClient,
        int_mock_session_repo,
    ):
        """DELETE /auth/sessions/{id} for non-existent session returns 404."""
        int_mock_session_repo.get_active_by_user.return_value = []

        resp = await auth_client.delete(f"/auth/sessions/{uuid4()}")

        assert resp.status_code == 404


class TestDeleteAccountEndpoint:

    @pytest.mark.asyncio
    async def test_delete_account_success(
        self,
        auth_client: AsyncClient,
        int_mock_auth_user_repo,
        int_token_service: TokenService,
    ):
        """POST /auth/delete-account with valid otp_verified_token returns 200."""
        auth_user = AuthUser(
            id=TEST_USER_ID, email=TEST_EMAIL, password_hash="hashed",
        )
        int_mock_auth_user_repo.get_by_id.return_value = auth_user

        otp_verified_token = int_token_service.create_purpose_token(
            user_id=TEST_USER_ID,
            purpose="otp_verified_delete_account",
            expire_minutes=10,
        )

        resp = await auth_client.post("/auth/delete-account", json={
            "otp_verified_token": otp_verified_token,
        })

        assert resp.status_code == 200
        int_mock_auth_user_repo.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_account_invalid_token(
        self,
        auth_client: AsyncClient,
        int_mock_auth_user_repo,
    ):
        """POST /auth/delete-account with invalid token returns 401."""
        resp = await auth_client.post("/auth/delete-account", json={
            "otp_verified_token": "invalid-token",
        })

        assert resp.status_code == 401
        int_mock_auth_user_repo.delete.assert_not_awaited()

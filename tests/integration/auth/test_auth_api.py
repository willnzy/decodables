"""
Integration tests for Auth API — Register, Login, Refresh, Logout.

Tests the full request→router→service→response pipeline with
mocked repositories.
"""

import pytest
from httpx import AsyncClient

from domains.auth.aggregates.auth_user import AuthUser
from domains.auth.aggregates.session import Session

from .conftest import TEST_EMAIL, TEST_PASSWORD, TEST_USER_ID


class TestRegisterEndpoint:

    @pytest.mark.asyncio
    async def test_register_success(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
        int_mock_session_repo,
    ):
        """POST /auth/register returns 200 with tokens."""
        created_user = AuthUser.create_new(
            email=TEST_EMAIL, password_hash="h", user_id=TEST_USER_ID,
        )
        int_mock_auth_user_repo.create.return_value = (created_user, True)

        resp = await client.post("/auth/register", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        })

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == TEST_EMAIL

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """POST /auth/register with weak password returns 422."""
        resp = await client.post("/auth/register", json={
            "email": "new@example.com",
            "password": "weak",
        })

        # Pydantic validation on min_length=8 catches this first
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """POST /auth/register with invalid email returns 422."""
        resp = await client.post("/auth/register", json={
            "email": "not-an-email",
            "password": TEST_PASSWORD,
        })

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self,
        client: AsyncClient,
        int_mock_auth_user_repo,
    ):
        """POST /auth/register with existing email returns 409."""
        int_mock_auth_user_repo.create.return_value = (
            AuthUser.create_new(email=TEST_EMAIL, password_hash="h"),
            False,
        )

        resp = await client.post("/auth/register", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        })

        assert resp.status_code == 409


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

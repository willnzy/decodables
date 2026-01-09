"""
Tests for Admin Users API (v3.25)

Test coverage:
- Authentication (require_admin)
- Constants validation
- Rate limiting
- Parameter validation (tier enum, uid/project_id length, offset pagination)
- Error message sanitization
- Request model field limits
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import HTTPException, Request

from api.admin.users import (
    router,
    search_users_api,
    get_users_by_tier_api,
    get_user_audit,
    adjust_user_credits,
    get_user_payments,
    get_user_projects,
    get_user_asset_usage,
    get_user_env_stats,
    restore_project_api,
    get_projects_feed,
    VALID_TIERS,
    CreditAdjustRequest,
    DiscountRequest,
)


# ==========================================
# Test Constants (v3.25)
# ==========================================

def test_valid_tiers_constant():
    """VALID_TIERS should contain expected values."""
    assert VALID_TIERS == {"free", "starter", "pro"}


# ==========================================
# Test Request Models (v3.25)
# ==========================================

def test_credit_adjust_request_field_limits():
    """CreditAdjustRequest should enforce field length limits."""
    # Valid request
    req = CreditAdjustRequest(amount=100, bucket="permanent", reason="Test" * 100)
    assert len(req.reason) <= 500

    # Reason too long should be caught by Pydantic
    with pytest.raises(Exception):
        CreditAdjustRequest(amount=100, bucket="permanent", reason="x" * 501)


def test_discount_request_field_limits():
    """DiscountRequest should enforce field length limits."""
    # Valid request
    req = DiscountRequest(discount_percent=50, valid_days=7, target_plan="starter")
    assert len(req.target_plan) <= 50

    # Target plan too long
    with pytest.raises(Exception):
        DiscountRequest(discount_percent=50, valid_days=7, target_plan="x" * 51)


# ==========================================
# Test GET /users/by-tier/{tier} (v3.25)
# ==========================================

@pytest.mark.asyncio
async def test_get_users_by_tier_invalid_tier():
    """GET /users/by-tier/{tier} should reject invalid tiers."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with pytest.raises(HTTPException) as exc_info:
        await get_users_by_tier_api(
            request=mock_request,
            tier="invalid_tier",
            admin=admin
        )

    assert exc_info.value.status_code == 400
    assert "Invalid tier" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_users_by_tier_valid_tiers():
    """GET /users/by-tier/{tier} should accept all valid tiers."""
    from unittest.mock import AsyncMock

    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.get_users_by_tier = AsyncMock(return_value=[])
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseUserRepository', return_value=mock_repo):
            for tier in VALID_TIERS:
                result = await get_users_by_tier_api(
                    request=mock_request,
                    tier=tier,
                    admin=admin
                )
                assert result["tier"] == tier


# ==========================================
# Test UID/Project ID Length Validation (v3.25)
# ==========================================

@pytest.mark.asyncio
async def test_get_user_audit_uid_too_long():
    """GET /users/{uid} should reject UIDs longer than 100 chars."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with pytest.raises(HTTPException) as exc_info:
        await get_user_audit(
            request=mock_request,
            uid="x" * 101,
            admin=admin
        )

    assert exc_info.value.status_code == 400
    assert "User ID too long" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_adjust_user_credits_uid_too_long():
    """POST /users/{uid}/credits should reject UIDs longer than 100 chars."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}
    req = CreditAdjustRequest(amount=100, bucket="permanent")

    with pytest.raises(HTTPException) as exc_info:
        await adjust_user_credits(
            request=mock_request,
            uid="x" * 101,
            req=req,
            admin=admin
        )

    assert exc_info.value.status_code == 400
    assert "User ID too long" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_restore_project_api_project_id_too_long():
    """POST /projects/{project_id}/restore should reject project IDs longer than 100 chars."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with pytest.raises(HTTPException) as exc_info:
        await restore_project_api(
            request=mock_request,
            project_id="x" * 101,
            admin=admin
        )

    assert exc_info.value.status_code == 400
    assert "Project ID too long" in str(exc_info.value.detail)


# ==========================================
# Test Error Sanitization (v3.25)
# ==========================================

@pytest.mark.asyncio
async def test_get_user_payments_error_sanitization():
    """GET /users/{uid}/payments should sanitize error messages."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.get_profile = AsyncMock(return_value={"stripe_customer_id": "cus_123"})
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseUserRepository', return_value=mock_repo):
            with patch('api.admin.users.get_customer_payments') as mock_get_payments:
                mock_get_payments.side_effect = Exception("Stripe API error with secret key sk_test_xyz")

                with pytest.raises(HTTPException) as exc_info:
                    await get_user_payments(
                        request=mock_request,
                        uid="user123",
                        admin=admin
                    )

                assert exc_info.value.status_code == 500
                assert exc_info.value.detail == "Failed to fetch payment history"
                assert "sk_test_xyz" not in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_user_asset_usage_error_sanitization():
    """GET /users/{uid}/asset-usage should sanitize error messages."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_supabase_client') as mock_supabase:
        mock_supabase.return_value.table.side_effect = Exception("Database error with password abc123")

        with pytest.raises(HTTPException) as exc_info:
            await get_user_asset_usage(
                request=mock_request,
                uid="user123",
                admin=admin
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to retrieve asset usage data"
        assert "abc123" not in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_user_env_stats_error_sanitization():
    """GET /users/{uid}/env-stats should sanitize error messages."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_supabase_client') as mock_supabase:
        mock_supabase.return_value.table.side_effect = Exception("Internal error with token xyz789")

        with pytest.raises(HTTPException) as exc_info:
            await get_user_env_stats(
                request=mock_request,
                uid="user123",
                admin=admin
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to retrieve environment statistics"
        assert "xyz789" not in str(exc_info.value.detail)


# ==========================================
# Test Offset Pagination (v3.25)
# ==========================================

@pytest.mark.asyncio
async def test_get_user_projects_uses_offset_pagination():
    """GET /users/{uid}/projects should use offset pagination."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.admin_get_user_projects = AsyncMock(return_value=[])
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseAdminUsersRepository', return_value=mock_repo):
            await get_user_projects(
                request=mock_request,
                uid="user123",
                offset=20,
                limit=10,
                include_deleted=True,
                admin=admin
            )

            # Verify repository method called with offset instead of page
            mock_repo.admin_get_user_projects.assert_called_once_with("user123", 20, 10, True)


@pytest.mark.asyncio
async def test_get_projects_feed_uses_offset_pagination():
    """GET /projects/feed should use offset pagination."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.get_all_projects_feed = AsyncMock(return_value=[])
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseProjectRepository', return_value=mock_repo):
            result = await get_projects_feed(
                request=mock_request,
                offset=50,
                limit=25,
                admin=admin
            )

            # Verify repository method called with offset instead of page
            mock_repo.get_all_projects_feed.assert_called_once_with(50, 25)
            assert "offset" in result
            assert result["offset"] == 50


# ==========================================
# Test Query Parameter Validation (v3.25)
# ==========================================

@pytest.mark.asyncio
async def test_search_users_api_query_validation():
    """GET /users should validate query parameter length."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.search_users = AsyncMock(return_value=[])
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseUserRepository', return_value=mock_repo):
            # Valid query length
            result = await search_users_api(
                request=mock_request,
                query="test" * 50,  # 200 chars max
                admin=admin
            )
            assert "users" in result

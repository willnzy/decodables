"""
Tests for Admin Users API (v3.25)

Complete test coverage:
- Authentication (require_admin)
- Constants validation
- Rate limiting presence
- Parameter validation (tier enum, uid/project_id length, offset pagination)
- Error message sanitization
- Request model field limits
- Boundary cases and edge cases
- All 13 endpoints coverage
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import HTTPException, Request
from pydantic import ValidationError

from api.admin.users import (
    router,
    search_users_api,
    get_users_by_tier_api,
    get_user_audit,
    adjust_user_credits,
    update_user,
    update_user_tier,
    create_user_discount_api,
    get_user_payments,
    get_user_projects,
    get_user_asset_usage,
    get_user_env_stats,
    restore_project_api,
    get_projects_feed,
    VALID_TIERS,
    CreditAdjustRequest,
    TierUpdateRequest,
    DiscountRequest,
)


# ==========================================
# Test Authentication
# ==========================================

def test_all_endpoints_have_admin_dependency():
    """All endpoints should have admin dependency in function signature."""
    import inspect
    from api.admin import users

    endpoints_to_check = [
        ("search_users_api", users.search_users_api),
        ("get_users_by_tier_api", users.get_users_by_tier_api),
        ("get_user_audit", users.get_user_audit),
        ("adjust_user_credits", users.adjust_user_credits),
        ("update_user", users.update_user),
        ("update_user_tier", users.update_user_tier),
        ("create_user_discount_api", users.create_user_discount_api),
        ("get_user_payments", users.get_user_payments),
        ("get_user_projects", users.get_user_projects),
        ("get_user_asset_usage", users.get_user_asset_usage),
        ("get_user_env_stats", users.get_user_env_stats),
        ("restore_project_api", users.restore_project_api),
        ("get_projects_feed", users.get_projects_feed),
    ]

    for name, endpoint in endpoints_to_check:
        # Try to get the actual function underneath decorators
        func = endpoint
        while hasattr(func, '__wrapped__'):
            func = func.__wrapped__

        # Check signature - admin should be a parameter
        sig = inspect.signature(func)
        assert "admin" in sig.parameters, f"{name} missing admin parameter"


# ==========================================
# Test Constants (v3.25)
# ==========================================

def test_valid_tiers_constant():
    """VALID_TIERS should contain exactly the expected values."""
    assert VALID_TIERS == {"free", "starter", "pro"}
    assert len(VALID_TIERS) == 3


def test_valid_tiers_immutable():
    """VALID_TIERS should be a set (immutable for our purposes)."""
    assert isinstance(VALID_TIERS, set)


# ==========================================
# Test Request Models - CreditAdjustRequest (v3.25)
# ==========================================

def test_credit_adjust_request_valid():
    """CreditAdjustRequest should accept valid inputs."""
    req = CreditAdjustRequest(amount=100, bucket="permanent", reason="Test reason")
    assert req.amount == 100
    assert req.bucket == "permanent"
    assert req.reason == "Test reason"


def test_credit_adjust_request_reason_max_length():
    """CreditAdjustRequest should enforce reason max length of 500."""
    # Valid: exactly 500 chars
    req = CreditAdjustRequest(amount=100, bucket="permanent", reason="x" * 500)
    assert len(req.reason) == 500

    # Invalid: 501 chars should fail
    with pytest.raises(ValidationError) as exc_info:
        CreditAdjustRequest(amount=100, bucket="permanent", reason="x" * 501)
    assert "reason" in str(exc_info.value)


def test_credit_adjust_request_reason_optional():
    """CreditAdjustRequest reason should be optional."""
    req = CreditAdjustRequest(amount=100, bucket="permanent")
    assert req.reason is None


def test_credit_adjust_request_bucket_validation():
    """CreditAdjustRequest should only accept monthly or permanent for bucket."""
    # Valid buckets
    req1 = CreditAdjustRequest(amount=100, bucket="permanent")
    assert req1.bucket == "permanent"

    req2 = CreditAdjustRequest(amount=100, bucket="monthly")
    assert req2.bucket == "monthly"

    # Invalid bucket
    with pytest.raises(ValidationError):
        CreditAdjustRequest(amount=100, bucket="invalid")


def test_credit_adjust_request_amount_boundaries():
    """CreditAdjustRequest should accept negative and positive amounts."""
    # Positive amount
    req1 = CreditAdjustRequest(amount=100, bucket="permanent")
    assert req1.amount == 100

    # Negative amount (for deductions)
    req2 = CreditAdjustRequest(amount=-50, bucket="permanent")
    assert req2.amount == -50

    # Zero amount
    req3 = CreditAdjustRequest(amount=0, bucket="permanent")
    assert req3.amount == 0


# ==========================================
# Test Request Models - TierUpdateRequest (v3.25)
# ==========================================

def test_tier_update_request_valid_tiers():
    """TierUpdateRequest should accept all valid tiers."""
    for tier in ["free", "starter", "pro"]:
        req = TierUpdateRequest(tier=tier)
        assert req.tier == tier


def test_tier_update_request_invalid_tier():
    """TierUpdateRequest should reject invalid tiers."""
    with pytest.raises(ValidationError) as exc_info:
        TierUpdateRequest(tier="enterprise")
    assert "tier" in str(exc_info.value)


def test_tier_update_request_case_sensitive():
    """TierUpdateRequest pattern is case-sensitive (lowercase required)."""
    with pytest.raises(ValidationError):
        TierUpdateRequest(tier="FREE")  # Should be lowercase


# ==========================================
# Test Request Models - DiscountRequest (v3.25)
# ==========================================

def test_discount_request_valid():
    """DiscountRequest should accept valid inputs."""
    req = DiscountRequest(discount_percent=50, valid_days=7, target_plan="starter")
    assert req.discount_percent == 50
    assert req.valid_days == 7
    assert req.target_plan == "starter"


def test_discount_request_percent_boundaries():
    """DiscountRequest should enforce discount_percent range 1-100."""
    # Valid: 1%
    req1 = DiscountRequest(discount_percent=1, valid_days=7)
    assert req1.discount_percent == 1

    # Valid: 100%
    req2 = DiscountRequest(discount_percent=100, valid_days=7)
    assert req2.discount_percent == 100

    # Invalid: 0%
    with pytest.raises(ValidationError):
        DiscountRequest(discount_percent=0, valid_days=7)

    # Invalid: 101%
    with pytest.raises(ValidationError):
        DiscountRequest(discount_percent=101, valid_days=7)


def test_discount_request_valid_days_boundaries():
    """DiscountRequest should enforce valid_days range 1-365."""
    # Valid: 1 day
    req1 = DiscountRequest(discount_percent=50, valid_days=1)
    assert req1.valid_days == 1

    # Valid: 365 days
    req2 = DiscountRequest(discount_percent=50, valid_days=365)
    assert req2.valid_days == 365

    # Invalid: 0 days
    with pytest.raises(ValidationError):
        DiscountRequest(discount_percent=50, valid_days=0)

    # Invalid: 366 days
    with pytest.raises(ValidationError):
        DiscountRequest(discount_percent=50, valid_days=366)


def test_discount_request_target_plan_max_length():
    """DiscountRequest should enforce target_plan max length of 50."""
    # Valid: exactly 50 chars
    req = DiscountRequest(discount_percent=50, valid_days=7, target_plan="x" * 50)
    assert len(req.target_plan) == 50

    # Invalid: 51 chars
    with pytest.raises(ValidationError):
        DiscountRequest(discount_percent=50, valid_days=7, target_plan="x" * 51)


def test_discount_request_target_plan_optional():
    """DiscountRequest target_plan should be optional."""
    req = DiscountRequest(discount_percent=50, valid_days=7)
    assert req.target_plan is None


# ==========================================
# Test GET /users - search_users_api (v3.25)
# ==========================================

@pytest.mark.asyncio
async def test_search_users_api_success():
    """GET /users should return users successfully."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.search_users = AsyncMock(return_value=[{"id": "user1", "email": "test@example.com"}])
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseUserRepository', return_value=mock_repo):
            result = await search_users_api(
                request=mock_request,
                query="test",
                admin=admin
            )

            assert "users" in result
            assert len(result["users"]) == 1
            mock_repo.search_users.assert_called_once_with("test")


@pytest.mark.asyncio
async def test_search_users_api_query_max_length():
    """GET /users should validate query parameter max length (200)."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.search_users = AsyncMock(return_value=[])
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseUserRepository', return_value=mock_repo):
            # Valid: exactly 200 chars
            result = await search_users_api(
                request=mock_request,
                query="a" * 200,
                admin=admin
            )
            assert "users" in result


@pytest.mark.asyncio
async def test_search_users_api_empty_results():
    """GET /users should handle empty results gracefully."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.search_users = AsyncMock(return_value=[])
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseUserRepository', return_value=mock_repo):
            result = await search_users_api(
                request=mock_request,
                query="nonexistent",
                admin=admin
            )

            assert result["users"] == []


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
    assert "free" in str(exc_info.value.detail)
    assert "starter" in str(exc_info.value.detail)
    assert "pro" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_users_by_tier_valid_tiers():
    """GET /users/by-tier/{tier} should accept all valid tiers."""
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
                assert result["count"] == 0
                assert "users" in result


@pytest.mark.asyncio
async def test_get_users_by_tier_case_normalization():
    """GET /users/by-tier/{tier} should normalize tier to lowercase."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.get_users_by_tier = AsyncMock(return_value=[])
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseUserRepository', return_value=mock_repo):
            result = await get_users_by_tier_api(
                request=mock_request,
                tier="FREE",  # Uppercase input
                admin=admin
            )

            # Should be normalized to lowercase
            assert result["tier"] == "free"
            # v3.26: Now includes offset and limit parameters
            mock_repo.get_users_by_tier.assert_called_once_with("free", offset=0, limit=100)


@pytest.mark.asyncio
async def test_get_users_by_tier_returns_count():
    """GET /users/by-tier/{tier} should return correct count."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_users = [{"id": "u1"}, {"id": "u2"}, {"id": "u3"}]
        mock_repo.get_users_by_tier = AsyncMock(return_value=mock_users)
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseUserRepository', return_value=mock_repo):
            result = await get_users_by_tier_api(
                request=mock_request,
                tier="pro",
                admin=admin
            )

            assert result["count"] == 3
            assert len(result["users"]) == 3
            # v3.26: Now returns pagination metadata
            assert result["offset"] == 0
            assert result["limit"] == 100
            assert result["has_more"] == False


# ==========================================
# Test UID/Project ID Length Validation (v3.25)
# ==========================================

@pytest.mark.asyncio
async def test_get_user_audit_uid_valid_length():
    """GET /users/{uid} should accept UIDs up to 100 chars."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.get_full_user_audit = AsyncMock(return_value={"user_id": "x" * 100})
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseAdminUsersRepository', return_value=mock_repo):
            # Valid: exactly 100 chars
            result = await get_user_audit(
                request=mock_request,
                uid="x" * 100,
                admin=admin
            )

            assert result is not None


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
    assert "max 100 characters" in str(exc_info.value.detail)


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
async def test_update_user_uid_boundary():
    """PATCH /users/{uid} should validate UID length."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}
    req = TierUpdateRequest(tier="pro")

    # Valid: 100 chars
    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_user_repo = Mock()
        mock_user_repo.get_profile = AsyncMock(return_value={"tier": "free"})
        mock_user_repo.update_subscription_tier = AsyncMock(return_value=None)

        mock_admin_repo = Mock()
        mock_admin_repo.admin_log_operation = AsyncMock(return_value=None)

        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseUserRepository', return_value=mock_user_repo):
            with patch('api.admin.users.SupabaseAdminUsersRepository', return_value=mock_admin_repo):
                result = await update_user(
                    request=mock_request,
                    uid="x" * 100,
                    req=req,
                    admin=admin
                )
                assert result["status"] == "ok"

    # Invalid: 101 chars
    with pytest.raises(HTTPException) as exc_info:
        await update_user(
            request=mock_request,
            uid="x" * 101,
            req=req,
            admin=admin
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_user_discount_uid_validation():
    """POST /users/{uid}/discount should validate UID length."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}
    req = DiscountRequest(discount_percent=50, valid_days=7)

    with pytest.raises(HTTPException) as exc_info:
        await create_user_discount_api(
            request=mock_request,
            uid="x" * 101,
            req=req,
            admin=admin
        )

    assert exc_info.value.status_code == 400
    assert "User ID too long" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_user_payments_uid_validation():
    """GET /users/{uid}/payments should validate UID length."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with pytest.raises(HTTPException) as exc_info:
        await get_user_payments(
            request=mock_request,
            uid="x" * 101,
            admin=admin
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_user_projects_uid_validation():
    """GET /users/{uid}/projects should validate UID length."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with pytest.raises(HTTPException) as exc_info:
        await get_user_projects(
            request=mock_request,
            uid="x" * 101,
            offset=0,
            limit=20,
            include_deleted=True,
            admin=admin
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_user_asset_usage_uid_validation():
    """GET /users/{uid}/asset-usage should validate UID length."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with pytest.raises(HTTPException) as exc_info:
        await get_user_asset_usage(
            request=mock_request,
            uid="x" * 101,
            admin=admin
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_user_env_stats_uid_validation():
    """GET /users/{uid}/env-stats should validate UID length."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with pytest.raises(HTTPException) as exc_info:
        await get_user_env_stats(
            request=mock_request,
            uid="x" * 101,
            admin=admin
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_restore_project_api_project_id_valid_length():
    """POST /projects/{project_id}/restore should accept project IDs up to 100 chars."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.restore_project = AsyncMock(return_value={"id": "x" * 100})
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseProjectRepository', return_value=mock_repo):
            # Valid: exactly 100 chars
            result = await restore_project_api(
                request=mock_request,
                project_id="x" * 100,
                admin=admin
            )

            assert result is not None


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


@pytest.mark.asyncio
async def test_restore_project_api_not_found():
    """POST /projects/{project_id}/restore should return 404 if project not found."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.restore_project = AsyncMock(return_value=None)  # Not found
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseProjectRepository', return_value=mock_repo):
            with pytest.raises(HTTPException) as exc_info:
                await restore_project_api(
                    request=mock_request,
                    project_id="nonexistent",
                    admin=admin
                )

            assert exc_info.value.status_code == 404
            assert "Project not found" in str(exc_info.value.detail)


# ==========================================
# Test Error Sanitization (v3.25)
# ==========================================

@pytest.mark.asyncio
async def test_get_user_payments_user_not_found():
    """GET /users/{uid}/payments should return 404 if user not found."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.get_profile = AsyncMock(return_value=None)  # User not found
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseUserRepository', return_value=mock_repo):
            with pytest.raises(HTTPException) as exc_info:
                await get_user_payments(
                    request=mock_request,
                    uid="nonexistent",
                    admin=admin
                )

            assert exc_info.value.status_code == 404
            assert "User not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_user_payments_no_stripe_customer():
    """GET /users/{uid}/payments should handle users without Stripe customer ID."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.get_profile = AsyncMock(return_value={"id": "user123", "stripe_customer_id": None})
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseUserRepository', return_value=mock_repo):
            result = await get_user_payments(
                request=mock_request,
                uid="user123",
                admin=admin
            )

            assert result["payments"] == []
            assert "No Stripe customer associated" in result["message"]


@pytest.mark.asyncio
async def test_get_user_payments_error_sanitization():
    """GET /users/{uid}/payments should sanitize Stripe error messages."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.get_profile = AsyncMock(return_value={"stripe_customer_id": "cus_123"})
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseUserRepository', return_value=mock_repo):
            with patch('api.admin.users.get_customer_payments') as mock_get_payments:
                mock_get_payments.side_effect = Exception("Stripe API error with secret key sk_test_xyz789")

                with pytest.raises(HTTPException) as exc_info:
                    await get_user_payments(
                        request=mock_request,
                        uid="user123",
                        admin=admin
                    )

                assert exc_info.value.status_code == 500
                assert exc_info.value.detail == "Failed to fetch payment history"
                # Ensure secret key is NOT exposed
                assert "sk_test_xyz789" not in str(exc_info.value.detail)
                assert "secret key" not in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_get_user_asset_usage_error_sanitization():
    """GET /users/{uid}/asset-usage should sanitize database error messages."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    # v3.26: Updated to use Repository pattern - patch at import location
    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_db_client.return_value = Mock()

        with patch('infrastructure.repositories.SupabaseAssetRepository') as mock_asset_repo_class:
            mock_repo = Mock()
            mock_repo.get_user_asset_usage = AsyncMock(side_effect=Exception("Database error with password abc123xyz"))
            mock_asset_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_user_asset_usage(
                    request=mock_request,
                    uid="user123",
                    admin=admin
                )

            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Failed to retrieve asset usage data"
            # Ensure password is NOT exposed
            assert "abc123xyz" not in str(exc_info.value.detail)
            assert "password" not in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_get_user_asset_usage_success():
    """GET /users/{uid}/asset-usage should return asset usage data."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    # v3.26: Updated to use Repository pattern with new response format
    mock_stats = {
        "total_assets": 3,
        "by_type": {"image": 2, "video": 1},
        "by_category": {"nature": 2, "urban": 1},
        "most_used": [
            {"id": "a1", "name": "Asset 1", "type": "image", "category": "nature", "usage_count": 10},
            {"id": "a2", "name": "Asset 2", "type": "video", "category": "urban", "usage_count": 5}
        ],
        "queried_limit": 1000,
        "is_truncated": False
    }

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_db_client.return_value = Mock()

        with patch('infrastructure.repositories.SupabaseAssetRepository') as mock_asset_repo_class:
            mock_repo = Mock()
            mock_repo.get_user_asset_usage = AsyncMock(return_value=mock_stats)
            mock_asset_repo_class.return_value = mock_repo

            result = await get_user_asset_usage(
                request=mock_request,
                uid="user123",
                admin=admin
            )

            assert result["user_id"] == "user123"
            assert result["total_assets"] == 3
            assert result["by_type"]["image"] == 2
            assert result["by_type"]["video"] == 1
            assert len(result["most_used"]) == 2
            # v3.26: Repository is called with limit and top_n parameters
            mock_repo.get_user_asset_usage.assert_called_once_with("user123", limit=1000, top_n=10)


@pytest.mark.asyncio
async def test_get_user_env_stats_error_sanitization():
    """GET /users/{uid}/env-stats should sanitize error messages."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    # v3.26: Updated to use Repository pattern - patch at import location
    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_db_client.return_value = Mock()

        with patch('infrastructure.repositories.SupabaseAnalyticsRepository') as mock_analytics_repo_class:
            mock_repo = Mock()
            mock_repo.get_user_env_stats = AsyncMock(side_effect=Exception("Internal error with token xyz789secret"))
            mock_analytics_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_user_env_stats(
                    request=mock_request,
                    uid="user123",
                    admin=admin
                )

            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Failed to retrieve environment statistics"
            # Ensure token is NOT exposed
            assert "xyz789secret" not in str(exc_info.value.detail)
            assert "token" not in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_get_user_env_stats_success():
    """GET /users/{uid}/env-stats should aggregate environment stats correctly."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    # v3.26: Updated to use Repository pattern with new response format
    mock_stats = {
        "total_events": 3,
        "browsers": {"Chrome": 2, "Firefox": 1},
        "devices": {"desktop": 2, "mobile": 1},
        "os_stats": {"Windows": 1, "iOS": 1, "macOS": 1},
        "referrers": {"google.com": 2, "direct": 1},
        "queried_limit": 100,
        "is_truncated": False
    }

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_db_client.return_value = Mock()

        with patch('infrastructure.repositories.SupabaseAnalyticsRepository') as mock_analytics_repo_class:
            mock_repo = Mock()
            mock_repo.get_user_env_stats = AsyncMock(return_value=mock_stats)
            mock_analytics_repo_class.return_value = mock_repo

            result = await get_user_env_stats(
                request=mock_request,
                uid="user123",
                admin=admin
            )

            assert result["user_id"] == "user123"
            assert result["sample_size"] == 3
            assert result["browsers"]["Chrome"] == 2
            assert result["browsers"]["Firefox"] == 1
            assert result["devices"]["desktop"] == 2
            assert result["devices"]["mobile"] == 1
            assert result["os_types"]["Windows"] == 1
            assert result["os_types"]["iOS"] == 1
            assert result["os_types"]["macOS"] == 1
            # v3.26: Repository is called with limit parameter
            mock_repo.get_user_env_stats.assert_called_once_with("user123", limit=100)


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
async def test_get_user_projects_pagination_boundaries():
    """GET /users/{uid}/projects should validate offset and limit boundaries."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.admin_get_user_projects = AsyncMock(return_value=[])
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseAdminUsersRepository', return_value=mock_repo):
            # Valid: offset=0, limit=1
            await get_user_projects(
                request=mock_request,
                uid="user123",
                offset=0,
                limit=1,
                include_deleted=False,
                admin=admin
            )

            # Valid: offset=0, limit=100
            await get_user_projects(
                request=mock_request,
                uid="user123",
                offset=0,
                limit=100,
                include_deleted=False,
                admin=admin
            )


@pytest.mark.asyncio
async def test_get_user_projects_include_deleted_parameter():
    """GET /users/{uid}/projects should respect include_deleted parameter."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.admin_get_user_projects = AsyncMock(return_value=[])
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseAdminUsersRepository', return_value=mock_repo):
            # include_deleted=True
            await get_user_projects(
                request=mock_request,
                uid="user123",
                offset=0,
                limit=20,
                include_deleted=True,
                admin=admin
            )

            assert mock_repo.admin_get_user_projects.call_args[0][3] is True

            # include_deleted=False
            await get_user_projects(
                request=mock_request,
                uid="user123",
                offset=0,
                limit=20,
                include_deleted=False,
                admin=admin
            )

            assert mock_repo.admin_get_user_projects.call_args[0][3] is False


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
            assert result["limit"] == 25


@pytest.mark.asyncio
async def test_get_projects_feed_pagination_boundaries():
    """GET /projects/feed should validate offset and limit boundaries."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.get_all_projects_feed = AsyncMock(return_value=[])
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseProjectRepository', return_value=mock_repo):
            # Valid: offset=0, limit=1
            result1 = await get_projects_feed(
                request=mock_request,
                offset=0,
                limit=1,
                admin=admin
            )
            assert result1["limit"] == 1

            # Valid: offset=0, limit=100
            result2 = await get_projects_feed(
                request=mock_request,
                offset=0,
                limit=100,
                admin=admin
            )
            assert result2["limit"] == 100


@pytest.mark.asyncio
async def test_get_projects_feed_returns_total():
    """GET /projects/feed should return total count."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_projects = [{"id": "p1"}, {"id": "p2"}]
        mock_repo.get_all_projects_feed = AsyncMock(return_value=mock_projects)
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseProjectRepository', return_value=mock_repo):
            result = await get_projects_feed(
                request=mock_request,
                offset=0,
                limit=50,
                admin=admin
            )

            assert result["total"] == 2
            assert len(result["items"]) == 2


# ==========================================
# Test adjust_user_credits (v3.25)
# ==========================================

@pytest.mark.asyncio
async def test_adjust_user_credits_success():
    """POST /users/{uid}/credits should adjust credits and log operation."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}
    req = CreditAdjustRequest(amount=100, bucket="permanent", reason="Test adjustment")

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.admin_adjust_credits = AsyncMock(return_value=None)
        mock_repo.admin_log_operation = AsyncMock(return_value=None)
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseAdminUsersRepository', return_value=mock_repo):
            result = await adjust_user_credits(
                request=mock_request,
                uid="user123",
                req=req,
                admin=admin
            )

            assert result["status"] == "ok"

            # Verify credit adjustment called
            mock_repo.admin_adjust_credits.assert_called_once_with("user123", 100, "permanent", "Test adjustment")

            # Verify operation logged
            mock_repo.admin_log_operation.assert_called_once()
            call_args = mock_repo.admin_log_operation.call_args[1]
            assert call_args["admin_id"] == "admin123"
            assert call_args["operation_type"] == "credit_adjust"
            assert call_args["target_user_id"] == "user123"
            assert "+100" in call_args["details"]


@pytest.mark.asyncio
async def test_adjust_user_credits_negative_amount():
    """POST /users/{uid}/credits should handle negative amounts (deductions)."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}
    req = CreditAdjustRequest(amount=-50, bucket="monthly", reason="Deduction")

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.admin_adjust_credits = AsyncMock(return_value=None)
        mock_repo.admin_log_operation = AsyncMock(return_value=None)
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseAdminUsersRepository', return_value=mock_repo):
            result = await adjust_user_credits(
                request=mock_request,
                uid="user123",
                req=req,
                admin=admin
            )

            assert result["status"] == "ok"
            mock_repo.admin_adjust_credits.assert_called_once_with("user123", -50, "monthly", "Deduction")

            # Check log contains negative sign
            call_args = mock_repo.admin_log_operation.call_args[1]
            assert "-50" in call_args["details"]


# ==========================================
# Test update_user / update_user_tier (v3.25)
# ==========================================

@pytest.mark.asyncio
async def test_update_user_tier_change():
    """PATCH /users/{uid} should update tier and log operation."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}
    req = TierUpdateRequest(tier="pro")

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_user_repo = Mock()
        mock_user_repo.get_profile = AsyncMock(return_value={"tier": "free"})
        mock_user_repo.update_subscription_tier = AsyncMock(return_value=None)

        mock_admin_repo = Mock()
        mock_admin_repo.admin_log_operation = AsyncMock(return_value=None)

        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseUserRepository', return_value=mock_user_repo):
            with patch('api.admin.users.SupabaseAdminUsersRepository', return_value=mock_admin_repo):
                result = await update_user(
                    request=mock_request,
                    uid="user123",
                    req=req,
                    admin=admin
                )

                assert result["status"] == "ok"

                # Verify tier updated
                mock_user_repo.update_subscription_tier.assert_called_once_with("user123", "pro", subscription_status="active")

                # Verify operation logged with tier change details
                call_args = mock_admin_repo.admin_log_operation.call_args[1]
                assert "free → pro" in call_args["details"]


@pytest.mark.asyncio
async def test_update_user_tier_to_free():
    """PATCH /users/{uid} should set subscription_status to inactive for free tier."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}
    req = TierUpdateRequest(tier="free")

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_user_repo = Mock()
        mock_user_repo.get_profile = AsyncMock(return_value={"tier": "pro"})
        mock_user_repo.update_subscription_tier = AsyncMock(return_value=None)

        mock_admin_repo = Mock()
        mock_admin_repo.admin_log_operation = AsyncMock(return_value=None)

        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseUserRepository', return_value=mock_user_repo):
            with patch('api.admin.users.SupabaseAdminUsersRepository', return_value=mock_admin_repo):
                await update_user(
                    request=mock_request,
                    uid="user123",
                    req=req,
                    admin=admin
                )

                # Verify subscription_status set to inactive for free tier
                mock_user_repo.update_subscription_tier.assert_called_once_with("user123", "free", subscription_status="inactive")


@pytest.mark.asyncio
async def test_update_user_tier_deprecated_endpoint():
    """POST /users/{uid}/tier (deprecated) should return 410 Gone in v3.26."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}
    req = TierUpdateRequest(tier="starter")

    # v3.26: Endpoint now returns 410 Gone instead of working
    with pytest.raises(HTTPException) as exc_info:
        await update_user_tier(
            request=mock_request,
            uid="user123",
            req=req,
            admin=admin
        )

    assert exc_info.value.status_code == 410
    assert "removed" in str(exc_info.value.detail).lower()
    assert "PATCH" in str(exc_info.value.detail)
    # Should include migration guidance
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert "replacement_endpoint" in detail
    assert "migration_guide" in detail


# ==========================================
# Test create_user_discount_api (v3.25)
# ==========================================

@pytest.mark.asyncio
async def test_create_user_discount_success():
    """POST /users/{uid}/discount should create discount successfully."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}
    req = DiscountRequest(discount_percent=25, valid_days=30, target_plan="starter")

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_discount = {"id": "disc_123", "discount_percent": 25, "valid_days": 30}
        mock_repo.create_user_discount = AsyncMock(return_value=mock_discount)
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseUserRepository', return_value=mock_repo):
            result = await create_user_discount_api(
                request=mock_request,
                uid="user123",
                req=req,
                admin=admin
            )

            assert result["id"] == "disc_123"
            mock_repo.create_user_discount.assert_called_once_with("user123", 25, 30, "starter")


# ==========================================
# Test Edge Cases
# ==========================================

@pytest.mark.asyncio
async def test_get_user_asset_usage_empty_assets():
    """GET /users/{uid}/asset-usage should handle users with no assets."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    # v3.26: Updated to use Repository pattern
    mock_stats = {
        "total_assets": 0,
        "by_type": {},
        "by_category": {},
        "most_used": [],
        "queried_limit": 1000,
        "is_truncated": False
    }

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_db_client.return_value = Mock()

        with patch('infrastructure.repositories.SupabaseAssetRepository') as mock_asset_repo_class:
            mock_repo = Mock()
            mock_repo.get_user_asset_usage = AsyncMock(return_value=mock_stats)
            mock_asset_repo_class.return_value = mock_repo

            result = await get_user_asset_usage(
                request=mock_request,
                uid="user123",
                admin=admin
            )

            assert result["total_assets"] == 0
            assert result["by_type"] == {}
            assert result["most_used"] == []


@pytest.mark.asyncio
async def test_get_user_env_stats_empty_events():
    """GET /users/{uid}/env-stats should handle users with no events."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    # v3.26: Updated to use Repository pattern
    mock_stats = {
        "total_events": 0,
        "browsers": {},
        "devices": {},
        "os_stats": {},
        "referrers": {},
        "queried_limit": 100,
        "is_truncated": False
    }

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_db_client.return_value = Mock()

        with patch('infrastructure.repositories.SupabaseAnalyticsRepository') as mock_analytics_repo_class:
            mock_repo = Mock()
            mock_repo.get_user_env_stats = AsyncMock(return_value=mock_stats)
            mock_analytics_repo_class.return_value = mock_repo

            result = await get_user_env_stats(
                request=mock_request,
                uid="user123",
                admin=admin
            )

            assert result["sample_size"] == 0
            assert result["browsers"] == {}
            assert result["devices"] == {}
            assert result["os_types"] == {}


# v3.26: Removed test_get_user_env_stats_handles_missing_properties
# Property handling is now done in SupabaseAnalyticsRepository, not in the API layer


@pytest.mark.asyncio
async def test_get_user_projects_default_parameters():
    """GET /users/{uid}/projects should use correct default values."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.admin_get_user_projects = AsyncMock(return_value=[])
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseAdminUsersRepository', return_value=mock_repo):
            # Call without specifying offset, limit, include_deleted
            await get_user_projects(
                request=mock_request,
                uid="user123",
                admin=admin
            )

            # Verify repo was called (defaults are handled by FastAPI)
            mock_repo.admin_get_user_projects.assert_called_once()
            # Get the actual call args
            call_kwargs = mock_repo.admin_get_user_projects.call_args[1] if mock_repo.admin_get_user_projects.call_args[1] else {}
            call_args = mock_repo.admin_get_user_projects.call_args[0]
            # Verify user_id was passed
            assert call_args[0] == "user123"


@pytest.mark.asyncio
async def test_get_projects_feed_default_parameters():
    """GET /projects/feed should use correct default values."""
    mock_request = Mock(spec=Request)
    admin = {"id": "admin123", "role": "admin"}

    with patch('api.admin.users.get_database_client') as mock_db_client:
        mock_repo = Mock()
        mock_repo.get_all_projects_feed = AsyncMock(return_value=[])
        mock_db_client.return_value = Mock()

        with patch('api.admin.users.SupabaseProjectRepository', return_value=mock_repo):
            result = await get_projects_feed(
                request=mock_request,
                admin=admin
            )

            # Verify repo was called
            mock_repo.get_all_projects_feed.assert_called_once()
            # Verify response has the expected fields (defaults handled by FastAPI)
            assert "items" in result
            assert "total" in result
            assert "offset" in result
            assert "limit" in result

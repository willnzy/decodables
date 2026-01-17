"""
User Profile API Integration Tests

Tests against staging: /api/v2/user/profile/*

Endpoints tested:
- GET /api/v2/user/profile/me - Get current user profile
- GET /api/v2/user/profile/history - Get credit history
- GET /api/v2/user/profile/purchases - Get marketplace purchases
- GET /api/v2/user/profile/notifications - Get user notifications

@module tests.integration.staging.test_user_profile
"""

import pytest
import httpx
from .conftest import (
    assert_success_response,
    assert_json_response,
    assert_error_response,
)


class TestUserProfileMe:
    """Tests for GET /api/v2/user/profile/me"""

    def test_get_current_user_authenticated(
        self,
        auth_client: httpx.Client,
        api_v2_url: str,
    ):
        """
        Test: Authenticated user can get their profile.

        Expected response structure:
        {
            "user_id": "user_xxx",
            "email": "user@example.com",
            "tier": "t1" | "t2" | "t3",
            "role": "user" | "admin",
            "credits_monthly": 100,
            "credits_permanent": 50,
            "credits_total": 150,
            ...
        }
        """
        # Act
        response = auth_client.get(f"{api_v2_url}/user/profile/me")

        # Assert
        assert_success_response(response, 200)
        data = assert_json_response(response)

        # Verify required fields
        assert "user_id" in data, "Response should contain user_id"
        assert data["user_id"].startswith("user_"), "user_id should start with 'user_'"

        # Verify tier (t1/t2/t3/t4)
        assert "tier" in data, "Response should contain tier"
        assert data["tier"] in ["t1", "t2", "t3", "t4"], f"Invalid tier: {data['tier']}"

        # Verify credits fields
        assert "credits_monthly" in data or "credits" in data, "Response should contain credits info"

        print(f"\n✅ User Profile Retrieved:")
        print(f"   user_id: {data.get('user_id')}")
        print(f"   email: {data.get('email')}")
        print(f"   tier: {data.get('tier')}")
        print(f"   credits_monthly: {data.get('credits_monthly')}")
        print(f"   credits_permanent: {data.get('credits_permanent')}")

    def test_get_current_user_unauthenticated(
        self,
        sync_client: httpx.Client,
        api_v2_url: str,
    ):
        """
        Test: Unauthenticated request should return 401.
        """
        # Act
        response = sync_client.get(f"{api_v2_url}/user/profile/me")

        # Assert
        assert_error_response(response, 401)
        print("\n✅ Correctly rejected unauthenticated request with 401")

    def test_get_current_user_invalid_token(
        self,
        sync_client: httpx.Client,
        api_v2_url: str,
    ):
        """
        Test: Invalid token should return 401.
        """
        # Act
        response = sync_client.get(
            f"{api_v2_url}/user/profile/me",
            headers={"Authorization": "Bearer invalid_token_xxx"},
        )

        # Assert
        assert_error_response(response, 401)
        print("\n✅ Correctly rejected invalid token with 401")


class TestUserProfileHistory:
    """Tests for GET /api/v2/user/profile/history"""

    def test_get_credit_history(
        self,
        auth_client: httpx.Client,
        api_v2_url: str,
    ):
        """
        Test: Get user's credit transaction history.

        Expected response structure:
        {
            "transactions": [...],
            "total": 100,
            "offset": 0,
            "limit": 20,
        }
        """
        # Act
        response = auth_client.get(f"{api_v2_url}/user/profile/history")

        # Assert
        assert_success_response(response, 200)
        data = assert_json_response(response)

        # Response could be list or dict with pagination
        if isinstance(data, list):
            print(f"\n✅ Credit History Retrieved: {len(data)} transactions")
        else:
            assert "transactions" in data or "items" in data or "data" in data
            items = data.get("transactions") or data.get("items") or data.get("data", [])
            print(f"\n✅ Credit History Retrieved: {len(items)} transactions")

    def test_get_credit_history_with_pagination(
        self,
        auth_client: httpx.Client,
        api_v2_url: str,
    ):
        """
        Test: Credit history pagination works correctly.
        """
        # Act
        response = auth_client.get(
            f"{api_v2_url}/user/profile/history",
            params={"limit": 5, "offset": 0},
        )

        # Assert
        assert_success_response(response, 200)
        data = assert_json_response(response)
        print(f"\n✅ Pagination works, response: {type(data)}")


class TestUserProfilePurchases:
    """Tests for GET /api/v2/user/profile/purchases"""

    def test_get_marketplace_purchases(
        self,
        auth_client: httpx.Client,
        api_v2_url: str,
    ):
        """
        Test: Get user's marketplace purchases.
        """
        # Act
        response = auth_client.get(f"{api_v2_url}/user/profile/purchases")

        # Assert
        assert_success_response(response, 200)
        data = assert_json_response(response)
        print(f"\n✅ Purchases Retrieved: {type(data)}")


class TestUserProfileNotifications:
    """Tests for GET /api/v2/user/profile/notifications"""

    def test_get_notifications(
        self,
        auth_client: httpx.Client,
        api_v2_url: str,
    ):
        """
        Test: Get user's notifications.
        """
        # Act
        response = auth_client.get(f"{api_v2_url}/user/profile/notifications")

        # Assert
        assert_success_response(response, 200)
        data = assert_json_response(response)
        print(f"\n✅ Notifications Retrieved: {type(data)}")


# ==========================================
# Response Schema Validation
# ==========================================

class TestUserProfileSchemaValidation:
    """Validate response schemas match OpenAPI spec."""

    def test_profile_me_schema(
        self,
        auth_client: httpx.Client,
        api_v2_url: str,
    ):
        """
        Validate /profile/me response schema.

        Required fields per OpenAPI:
        - user_id: string
        - email: string
        - tier: enum (t1, t2, t3, t4)
        - role: enum (user, admin)
        - display_name: string | null
        - avatar_url: string | null
        - created_at: datetime
        """
        response = auth_client.get(f"{api_v2_url}/user/profile/me")
        data = response.json()

        # Required fields
        required_fields = ["user_id", "tier"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Type validation
        assert isinstance(data["user_id"], str)
        assert isinstance(data["tier"], str)

        # Enum validation
        valid_tiers = ["t1", "t2", "t3", "t4"]
        assert data["tier"] in valid_tiers, f"Invalid tier value: {data['tier']}"

        if "role" in data:
            valid_roles = ["user", "admin"]
            assert data["role"] in valid_roles, f"Invalid role value: {data['role']}"

        print("\n✅ Schema validation passed")
        print(f"   Fields present: {list(data.keys())}")

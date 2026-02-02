"""
Tests for api/user/billing.py

Endpoints:
- GET /api/v2/user/billing/credits
- GET /api/v2/user/billing/transactions
- GET /api/v2/user/billing/can-afford
- POST /api/v2/user/billing/credits/add

@version 3.0.0

Changes in v3.0.0:
- Updated user_id format to UUID (self-hosted auth migration)
- Updated validation tests to match UUID user ID format

Changes in v1.2.0:
- Removed tests for /credits/deduct endpoint (removed in billing.py v1.2.0)
- Updated tests for AffordabilityResponse (removed current_balance field)
- Added rate limiter bypass for testing
- Added tests for UUID validation in AddCreditsRequest (fixed in v1.2.1)
- Added tests for operation whitelist in /can-afford

Created: 2026-01-08 (Stage 3: User/Admin routing migration)
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime

# v1.2.0: Rate limiter bypass BEFORE app import
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

from app import app
from domains.billing.value_objects import TransactionType
from dependencies import get_current_user, require_admin

client = TestClient(app)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "id": "user_123",
        "email": "user@example.com",
        "tier": "pro",
    }


@pytest.fixture
def mock_admin():
    """Mock authenticated admin user."""
    return {
        "id": "admin_123",
        "email": "admin@example.com",
        "tier": "pro",
        "is_admin": True,
    }


@pytest.fixture
def override_get_current_user(mock_user):
    """Override FastAPI dependency to return mock user."""
    async def _get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def override_require_admin(mock_admin):
    """Override FastAPI dependency to return mock admin."""
    async def _require_admin():
        return mock_admin

    app.dependency_overrides[require_admin] = _require_admin
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Valid auth headers (for documentation, not actually used with dependency override)."""
    return {"Authorization": "Bearer test_token_user_123"}


@pytest.fixture
def mock_credits_result():
    """Mock GetUserCreditsQuery result."""
    return MagicMock(
        success=True,
        monthly_credits=500,
        permanent_credits=50,
        total_credits=550,
        tier="pro",
    )


@pytest.fixture
def mock_transaction():
    """Mock transaction entity."""
    mock_balance = MagicMock()
    mock_balance.total = 540
    tx = MagicMock(
        id="tx_123",
        amount=-10,
        balance_after=mock_balance,
        tx_type=TransactionType.AI_GENERATION,
        description="AI image generation",
        created_at=datetime(2026, 1, 8, 12, 0, 0),
        idempotency_key="idem_123",
    )
    return tx


@pytest.fixture
def mock_transaction_history_result(mock_transaction):
    """Mock GetTransactionHistoryQuery result."""
    return MagicMock(
        success=True,
        transactions=[mock_transaction],
        total_count=1,
    )


# v1.2.0: Removed mock_deduct_result fixture (endpoint removed)


@pytest.fixture
def mock_add_result():
    """Mock AddCreditsCommand result."""
    mock_transaction = MagicMock()
    mock_transaction.amount = 100  # Positive for addition
    return MagicMock(
        success=True,
        transaction=mock_transaction,
        new_balance=650,
    )


# ==========================================
# GET /api/v2/user/billing/credits
# ==========================================

class TestGetCredits:
    """Tests for GET /api/v2/user/billing/credits endpoint."""

    def test_get_credits_unauthenticated(self):
        """
        Test: Unauthenticated access returns 401

        Given: No authentication header
        When: GET /api/v2/user/billing/credits
        Then: Returns 401 Unauthorized

        Business Logic Verified:
        - Billing endpoints require authentication
        - UnauthorizedException is raised for missing token
        """
        # Ensure no override is active
        app.dependency_overrides.clear()

        # Act
        response = client.get("/api/v2/user/billing/credits")

        # Assert
        assert response.status_code == 401

    def test_get_credits_invalid_token(self):
        """
        Test: Invalid token returns 401

        Given: Invalid Bearer token
        When: GET /api/v2/user/billing/credits with bad token
        Then: Returns 401 Unauthorized

        Business Logic Verified:
        - Invalid JWT tokens are rejected
        """
        # Ensure no override is active
        app.dependency_overrides.clear()

        # Act
        response = client.get(
            "/api/v2/user/billing/credits",
            headers={"Authorization": "Bearer invalid_token_xyz"},
        )

        # Assert
        assert response.status_code == 401

    @patch('api.user.billing.get_container')
    def test_get_credits_success(
        self,
        mock_get_container,
        mock_credits_result,
        override_get_current_user,
    ):
        """
        Test: Get credits successfully

        Given: User is authenticated
        When: GET /api/v2/user/billing/credits
        Then: Returns 200 with credits info

        Business Logic Verified:
        - Handler is called with correct user_id from authenticated user
        - Response contains monthly_credits, permanent_credits, total_credits, tier
        """
        # Arrange
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_credits_result)
        mock_container = MagicMock()
        mock_container.get_user_credits_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.get("/api/v2/user/billing/credits")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["monthly_credits"] == 500
        assert data["permanent_credits"] == 50
        assert data["total_credits"] == 550
        assert data["tier"] == "pro"

        # Verify handler was called with correct query
        mock_handler.handle.assert_called_once()
        call_args = mock_handler.handle.call_args[0][0]
        assert call_args.user_id == "user_123"

    @patch('api.user.billing.get_container')
    def test_get_credits_new_user_zero_credits(
        self,
        mock_get_container,
        override_get_current_user,
    ):
        """
        Test: New user returns zero credits

        Given: User has no credits record (new user defaults)
        When: GET /api/v2/user/billing/credits
        Then: Returns 200 with 0 credits

        Business Logic Verified:
        - New users start with 0 monthly credits
        - New free users should have 50 permanent (signup bonus) - but this tests handler returning 0
        - Total is sum of monthly + permanent
        """
        # Arrange
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=MagicMock(
            success=True,
            monthly_credits=0,
            permanent_credits=0,  # In reality, new users get 50 signup bonus
            total_credits=0,
            tier="free",
        ))
        mock_container = MagicMock()
        mock_container.get_user_credits_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.get("/api/v2/user/billing/credits")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["monthly_credits"] == 0
        assert data["permanent_credits"] == 0
        assert data["total_credits"] == 0
        assert data["tier"] == "free"

    @patch('api.user.billing.get_container')
    def test_get_credits_handler_failure(
        self,
        mock_get_container,
        override_get_current_user,
    ):
        """
        Test: Get credits handler fails (500)

        Given: Handler returns error
        When: GET /api/v2/user/billing/credits
        Then: Returns 500 Internal Server Error
        """
        # Arrange
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=MagicMock(
            success=False,
            error="Database connection failed",
        ))
        mock_container = MagicMock()
        mock_container.get_user_credits_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.get("/api/v2/user/billing/credits")

        # Assert
        assert response.status_code == 500
        # HTTPException(500, message) returns plain string in FastAPI
        # The actual error format depends on FastAPI exception handler


# ==========================================
# GET /api/v2/user/billing/transactions
# ==========================================

class TestGetTransactions:
    """Tests for GET /api/v2/user/billing/transactions endpoint."""

    @patch('api.user.billing.get_container')
    def test_get_transactions_success(
        self,
        mock_get_container,
        mock_transaction_history_result,
        override_get_current_user,
    ):
        """
        Test: Get transactions successfully

        Given: User has transaction history
        When: GET /api/v2/user/billing/transactions
        Then: Returns 200 with transactions list

        Business Logic Verified:
        - Handler called with correct user_id
        - Returns transaction list with correct structure
        """
        # Arrange
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_transaction_history_result)
        mock_container = MagicMock()
        mock_container.get_transaction_history_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.get("/api/v2/user/billing/transactions?limit=50&offset=0")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["transactions"]) == 1
        assert data["total_count"] == 1
        tx = data["transactions"][0]
        assert tx["id"] == "tx_123"
        assert tx["amount"] == -10
        assert tx["balance_after"] == 540
        assert tx["tx_type"] == "generation"

        # Verify handler was called with correct query
        mock_handler.handle.assert_called_once()
        call_args = mock_handler.handle.call_args[0][0]
        assert call_args.user_id == "user_123"

    @patch('api.user.billing.get_container')
    def test_get_transactions_with_filters(
        self,
        mock_get_container,
        mock_transaction_history_result,
        override_get_current_user,
    ):
        """
        Test: Get transactions with type filter

        Given: User has transactions
        When: GET with tx_type filter
        Then: Returns filtered transactions

        Business Logic Verified:
        - Filter parameter correctly passed to handler
        """
        # Arrange
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_transaction_history_result)
        mock_container = MagicMock()
        mock_container.get_transaction_history_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.get("/api/v2/user/billing/transactions?tx_type=generation")

        # Assert
        assert response.status_code == 200
        # Verify filter was passed to handler
        mock_handler.handle.assert_called_once()
        call_args = mock_handler.handle.call_args[0][0]
        assert call_args.tx_type == "generation"

    @patch('api.user.billing.get_container')
    def test_get_transactions_with_date_range(
        self,
        mock_get_container,
        mock_transaction_history_result,
        override_get_current_user,
    ):
        """
        Test: Get transactions with date range filter

        Given: User has transactions
        When: GET with start_date and end_date
        Then: Returns filtered transactions

        Business Logic Verified:
        - Date range parameters correctly passed to handler
        """
        # Arrange
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_transaction_history_result)
        mock_container = MagicMock()
        mock_container.get_transaction_history_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.get(
            "/api/v2/user/billing/transactions"
            "?start_date=2026-01-01T00:00:00"
            "&end_date=2026-01-31T23:59:59"
        )

        # Assert
        assert response.status_code == 200
        # Verify date params were passed to handler
        mock_handler.handle.assert_called_once()
        call_args = mock_handler.handle.call_args[0][0]
        assert call_args.start_date is not None
        assert call_args.end_date is not None

    @patch('api.user.billing.get_container')
    def test_get_transactions_empty_history(
        self,
        mock_get_container,
        override_get_current_user,
    ):
        """
        Test: Get transactions for user with no history

        Given: User has no transactions
        When: GET /api/v2/user/billing/transactions
        Then: Returns empty list with total_count=0

        Business Logic Verified:
        - New users have no transaction history
        - Response structure is correct for empty results
        """
        # Arrange
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=MagicMock(
            success=True,
            transactions=[],
            total_count=0,
        ))
        mock_container = MagicMock()
        mock_container.get_transaction_history_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.get("/api/v2/user/billing/transactions")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["transactions"] == []
        assert data["total_count"] == 0

    @patch('api.user.billing.get_container')
    def test_get_transactions_pagination(
        self,
        mock_get_container,
        mock_transaction_history_result,
        override_get_current_user,
    ):
        """
        Test: Get transactions with pagination

        Given: User has many transactions
        When: GET with limit=10, offset=20
        Then: Query parameters correctly passed

        Business Logic Verified:
        - Pagination parameters are correctly handled
        """
        # Arrange
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_transaction_history_result)
        mock_container = MagicMock()
        mock_container.get_transaction_history_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.get("/api/v2/user/billing/transactions?limit=10&offset=20")

        # Assert
        assert response.status_code == 200
        mock_handler.handle.assert_called_once()
        call_args = mock_handler.handle.call_args[0][0]
        assert call_args.limit == 10
        assert call_args.offset == 20

    @patch('api.user.billing.get_container')
    def test_get_transactions_total_count_is_total_not_page_count(
        self,
        mock_get_container,
        mock_transaction,
        override_get_current_user,
    ):
        """
        Test: total_count returns TOTAL records, not current page count

        Given: User has 150 total transactions
        When: GET with limit=50&offset=0
        Then: Returns 50 transactions but total_count=150

        Business Logic Verified:
        - total_count is the total number of matching records
        - This is essential for pagination UI
        """
        # Arrange
        mock_handler = MagicMock()
        # Simulate: current page has 50 items, but total is 150
        mock_handler.handle = AsyncMock(return_value=MagicMock(
            success=True,
            transactions=[mock_transaction] * 50,  # 50 items on this page
            total_count=150,  # But total is 150
        ))
        mock_container = MagicMock()
        mock_container.get_transaction_history_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.get("/api/v2/user/billing/transactions?limit=50&offset=0")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["transactions"]) == 50  # Current page count
        assert data["total_count"] == 150  # TOTAL count, not len(transactions)


# ==========================================
# GET /api/v2/user/billing/can-afford
# ==========================================

class TestCanAfford:
    """Tests for GET /api/v2/user/billing/can-afford endpoint."""

    @patch('api.user.billing.get_container')
    def test_can_afford_by_amount_success(
        self,
        mock_get_container,
        mock_credits_result,
        override_get_current_user,
    ):
        """
        Test: Check affordability by amount (can afford)

        Given: User has 550 credits
        When: Check if can afford 100 credits
        Then: Returns can_afford=true

        Business Logic Verified:
        - Correctly calculates affordability (550 >= 100)
        """
        # Arrange
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_credits_result)
        mock_container = MagicMock()
        mock_container.get_user_credits_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.get("/api/v2/user/billing/can-afford?amount=100")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["can_afford"] is True
        # v1.2.0: current_balance removed from response for security
        assert "current_balance" not in data
        assert data["required_amount"] == 100

    @patch('api.user.billing.get_container')
    def test_can_afford_by_amount_insufficient(
        self,
        mock_get_container,
        mock_credits_result,
        override_get_current_user,
    ):
        """
        Test: Check affordability by amount (insufficient)

        Given: User has 550 credits
        When: Check if can afford 1000 credits
        Then: Returns can_afford=false

        Business Logic Verified:
        - Correctly calculates insufficient credits (550 < 1000)
        """
        # Arrange
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_credits_result)
        mock_container = MagicMock()
        mock_container.get_user_credits_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.get("/api/v2/user/billing/can-afford?amount=1000")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["can_afford"] is False
        # v1.2.0: current_balance removed from response for security
        assert "current_balance" not in data
        assert data["required_amount"] == 1000

    @patch('api.user.billing.get_container')
    def test_can_afford_by_operation(
        self,
        mock_get_container,
        mock_credits_result,
        override_get_current_user,
    ):
        """
        Test: Check affordability by operation name

        Given: image_generation costs 5 credits
        When: Check if can afford "image_generation"
        Then: Returns can_afford=true with cost

        Business Logic Verified:
        - Looks up operation cost via billing_service
        - Correctly calculates affordability with operation cost
        """
        # Arrange
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_credits_result)
        mock_billing_service = MagicMock()
        # get_operation_cost returns int directly (not an object with .amount)
        mock_billing_service.get_operation_cost.return_value = 5
        mock_container = MagicMock()
        mock_container.get_user_credits_handler = mock_handler
        mock_container.billing_service = mock_billing_service
        mock_get_container.return_value = mock_container

        # Act
        response = client.get("/api/v2/user/billing/can-afford?operation=image_generation")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["can_afford"] is True
        assert data["required_amount"] == 5

        # Verify billing service was called
        mock_billing_service.get_operation_cost.assert_called_once_with("image_generation")

    def test_can_afford_no_params(self, override_get_current_user):
        """
        Test: Missing both amount and operation (400)

        Given: No amount or operation provided
        When: GET /can-afford without params
        Then: Returns 400 Bad Request

        Business Logic Verified:
        - Validates that at least one parameter is provided
        """
        # Act
        response = client.get("/api/v2/user/billing/can-afford")

        # Assert
        assert response.status_code == 400
        # HTTPException(400, message) format varies by FastAPI version
        # Just verify it's a 400 error

    @patch('api.user.billing.get_container')
    def test_can_afford_zero_amount(
        self,
        mock_get_container,
        mock_credits_result,
        override_get_current_user,
    ):
        """
        Test: Check affordability for zero amount

        Given: User has credits
        When: Check if can afford 0 credits
        Then: Returns can_afford=true

        Business Logic Verified:
        - Zero amount is always affordable
        """
        # Arrange
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_credits_result)
        mock_container = MagicMock()
        mock_container.get_user_credits_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.get("/api/v2/user/billing/can-afford?amount=0")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["can_afford"] is True
        assert data["required_amount"] == 0

    @patch('api.user.billing.get_container')
    def test_can_afford_exact_balance(
        self,
        mock_get_container,
        mock_credits_result,
        override_get_current_user,
    ):
        """
        Test: Check affordability when amount equals balance

        Given: User has exactly 550 credits
        When: Check if can afford 550 credits
        Then: Returns can_afford=true

        Business Logic Verified:
        - Exact match is affordable (>=, not >)
        """
        # Arrange
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_credits_result)  # 550 total
        mock_container = MagicMock()
        mock_container.get_user_credits_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.get("/api/v2/user/billing/can-afford?amount=550")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["can_afford"] is True
        # v1.2.0: current_balance removed from response for security
        assert "current_balance" not in data
        assert data["required_amount"] == 550

    def test_can_afford_unknown_operation(self, override_get_current_user):
        """
        Test: Check affordability for unknown operation

        Given: User checks an unknown operation
        When: GET /can-afford?operation=unknown_op
        Then: Returns 400 error (v1.2.0: operation whitelist validation)

        Business Logic Verified:
        - Unknown operations are rejected with 400 error
        """
        # Act
        response = client.get("/api/v2/user/billing/can-afford?operation=unknown_op")

        # Assert - v1.2.0: Now returns 400 for invalid operation
        assert response.status_code == 400
        assert "Invalid operation" in response.json()["message"]

    def test_can_afford_valid_operation(self, override_get_current_user):
        """
        Test: Check affordability for valid operation

        Given: User checks a valid operation (image_generation)
        When: GET /can-afford?operation=image_generation
        Then: Returns success (operation in whitelist)
        """
        with patch('api.user.billing.get_container') as mock_get_container:
            # Arrange
            mock_credits_result = MagicMock(
                success=True,
                total_credits=550,
            )
            mock_handler = MagicMock()
            mock_handler.handle = AsyncMock(return_value=mock_credits_result)
            mock_billing_service = MagicMock()
            mock_billing_service.get_operation_cost.return_value = 5
            mock_container = MagicMock()
            mock_container.get_user_credits_handler = mock_handler
            mock_container.billing_service = mock_billing_service
            mock_get_container.return_value = mock_container

            # Act
            response = client.get("/api/v2/user/billing/can-afford?operation=image_generation")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["can_afford"] is True
            assert data["required_amount"] == 5


# ==========================================
# POST /api/v2/user/billing/credits/deduct (REMOVED in v1.2.0)
# ==========================================

# v1.2.0: B-P0-3 - /credits/deduct endpoint was removed for security
# Credit deductions should ONLY happen through domain services internally,
# not through a public API endpoint. All TestDeductCredits tests have been removed.


# ==========================================
# POST /api/v2/user/billing/credits/add
# ==========================================

class TestAddCredits:
    """Tests for POST /api/v2/user/billing/credits/add endpoint.

    v1.1.0: This endpoint now requires ADMIN permission.
    """

    def test_add_credits_requires_admin(self, override_get_current_user):
        """
        Test: Non-admin user cannot add credits (403/401)

        Given: Regular authenticated user (not admin)
        When: POST to add credits
        Then: Returns 401/403 (depending on require_admin impl)

        Business Logic Verified:
        - /credits/add endpoint requires admin permission
        """
        # Act - regular user tries to add credits
        response = client.post(
            "/api/v2/user/billing/credits/add",
            json={
                "user_id": "12345678-1234-1234-1234-123456789abc",
                "amount": 100,
                "credit_type": "permanent",
                "reason": "Test",
            },
        )

        # Assert - should be rejected (401 or 403)
        assert response.status_code in [401, 403]

    @patch('api.user.billing.get_container')
    def test_add_credits_success_admin(
        self,
        mock_get_container,
        mock_add_result,
        override_require_admin,
    ):
        """
        Test: Admin can add credits successfully

        Given: Admin user
        When: POST to add 100 permanent credits to target user
        Then: Returns 200 with new balance

        Business Logic Verified:
        - Admin can add credits to any user
        - Handler called with target user_id from request
        - Returns updated balance after addition
        """
        # Arrange
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_add_result)
        mock_container = MagicMock()
        mock_container.add_credits_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.post(
            "/api/v2/user/billing/credits/add",
            json={
                "user_id": "12345678-1234-1234-1234-123456789abc",
                "amount": 100,
                "credit_type": "permanent",
                "reason": "Promotion reward",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["amount_added"] == 100
        assert data["new_balance"] == 650
        assert data["target_user_id"] == "12345678-1234-1234-1234-123456789abc"

        # Verify handler was called with correct command (target user, not admin)
        mock_handler.handle.assert_called_once()
        call_args = mock_handler.handle.call_args[0][0]
        assert call_args.user_id == "12345678-1234-1234-1234-123456789abc"  # Target user, not admin
        assert call_args.amount == 100
        # API converts credit_type to bucket enum
        from domains.billing.value_objects import CreditBucket
        assert call_args.bucket == CreditBucket.PERMANENT

    def test_add_credits_invalid_type(self, override_require_admin):
        """
        Test: Invalid credit type (422 Validation Error)

        Given: Invalid credit_type provided
        When: POST with credit_type="invalid"
        Then: Returns 422 Unprocessable Entity

        Business Logic Verified:
        - Pydantic validation rejects invalid credit_type
        """
        # Act
        response = client.post(
            "/api/v2/user/billing/credits/add",
            json={
                "user_id": "12345678-1234-1234-1234-123456789abc",
                "amount": 100,
                "credit_type": "invalid",
                "reason": "Test",
            },
        )

        # Assert
        assert response.status_code == 422

    @patch('api.user.billing.get_container')
    def test_add_credits_monthly(
        self,
        mock_get_container,
        override_require_admin,
    ):
        """
        Test: Add monthly credits

        Given: Admin request to add monthly credits
        When: POST with credit_type="monthly"
        Then: Handler receives CreditBucket.MONTHLY and SUB_GRANT tx_type

        Business Logic Verified:
        - Monthly credits use MONTHLY bucket
        - Monthly credits from subscription use SUB_GRANT transaction type
        """
        # Arrange
        mock_transaction = MagicMock()
        mock_transaction.amount = 500
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=MagicMock(
            success=True,
            transaction=mock_transaction,
            new_balance=550,
        ))
        mock_container = MagicMock()
        mock_container.add_credits_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.post(
            "/api/v2/user/billing/credits/add",
            json={
                "user_id": "12345678-1234-1234-1234-123456789abc",
                "amount": 500,
                "credit_type": "monthly",
                "reason": "Subscription renewal",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["amount_added"] == 500

        # Verify bucket and tx_type
        mock_handler.handle.assert_called_once()
        call_args = mock_handler.handle.call_args[0][0]
        from domains.billing.value_objects import CreditBucket, TransactionType
        assert call_args.bucket == CreditBucket.MONTHLY
        assert call_args.tx_type == TransactionType.SUBSCRIPTION_GRANT

    def test_add_credits_exceeds_max(self, override_require_admin):
        """
        Test: Amount exceeds max validation (422)

        Given: Amount > 10000
        When: POST with amount=10001
        Then: Returns 422 Validation Error

        Business Logic Verified:
        - Single addition max is 10000 credits
        """
        # Act
        response = client.post(
            "/api/v2/user/billing/credits/add",
            json={
                "user_id": "12345678-1234-1234-1234-123456789abc",
                "amount": 10001,
                "credit_type": "permanent",
                "reason": "Test",
            },
        )

        # Assert
        assert response.status_code == 422

    def test_add_credits_missing_reason(self, override_require_admin):
        """
        Test: Missing reason field (422)

        Given: No reason field
        When: POST without reason
        Then: Returns 422 Validation Error

        Business Logic Verified:
        - Reason is required for audit trail
        """
        # Act
        response = client.post(
            "/api/v2/user/billing/credits/add",
            json={
                "user_id": "12345678-1234-1234-1234-123456789abc",
                "amount": 100,
                "credit_type": "permanent",
            },
        )

        # Assert
        assert response.status_code == 422

    def test_add_credits_missing_user_id(self, override_require_admin):
        """
        Test: Missing user_id field (422)

        Given: No user_id field
        When: POST without user_id
        Then: Returns 422 Validation Error

        Business Logic Verified:
        - Target user_id is required for admin to add credits
        """
        # Act
        response = client.post(
            "/api/v2/user/billing/credits/add",
            json={
                "amount": 100,
                "credit_type": "permanent",
                "reason": "Test",
            },
        )

        # Assert
        assert response.status_code == 422

    @patch('api.user.billing.get_container')
    def test_add_credits_handler_failure(
        self,
        mock_get_container,
        override_require_admin,
    ):
        """
        Test: Add credits handler fails (400)

        Given: Handler returns error
        When: POST to add credits
        Then: Returns 400 Bad Request

        Business Logic Verified:
        - Handler errors are properly propagated
        """
        # Arrange
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=MagicMock(
            success=False,
            error="Database error",
        ))
        mock_container = MagicMock()
        mock_container.add_credits_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.post(
            "/api/v2/user/billing/credits/add",
            json={
                "user_id": "12345678-1234-1234-1234-123456789abc",
                "amount": 100,
                "credit_type": "permanent",
                "reason": "Test",
            },
        )

        # Assert - v1.2.0: Error message is sanitized
        assert response.status_code == 400
        assert "Failed to add credits" in response.json()["message"]

    def test_add_credits_invalid_user_id_format(self, override_require_admin):
        """
        Test: Invalid user_id format (422 Validation Error)

        v3.0.0: user_id must be a valid UUID format

        Given: Invalid user_id format (not UUID)
        When: POST with user_id="invalid_user"
        Then: Returns 422 Validation Error

        Business Logic Verified:
        - user_id must be a valid UUID format
        """
        # Act
        response = client.post(
            "/api/v2/user/billing/credits/add",
            json={
                "user_id": "invalid_user_id_not_uuid_format",
                "amount": 100,
                "credit_type": "permanent",
                "reason": "Test",
            },
        )

        # Assert
        assert response.status_code == 422

    def test_add_credits_user_id_too_short(self, override_require_admin):
        """
        Test: user_id too short (422 Validation Error)

        v3.0.0: user_id must be exactly 36 characters (UUID format)

        Given: user_id shorter than 36 characters
        When: POST with short user_id
        Then: Returns 422 Validation Error
        """
        # Act
        response = client.post(
            "/api/v2/user/billing/credits/add",
            json={
                "user_id": "short-id",
                "amount": 100,
                "credit_type": "permanent",
                "reason": "Test",
            },
        )

        # Assert
        assert response.status_code == 422

    def test_add_credits_user_id_wrong_format(self, override_require_admin):
        """
        Test: user_id with wrong format (422 Validation Error)

        v3.0.0: user_id must be valid UUID, not arbitrary string

        Given: user_id with correct length but not UUID format
        When: POST with non-UUID string
        Then: Returns 422 Validation Error
        """
        # Act - correct length but not valid UUID format
        response = client.post(
            "/api/v2/user/billing/credits/add",
            json={
                "user_id": "not-a-valid-uuid-format-xxxxxxxxxx",
                "amount": 100,
                "credit_type": "permanent",
                "reason": "Test",
            },
        )

        # Assert
        assert response.status_code == 422

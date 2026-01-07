"""
Tests for api/user/billing.py

Endpoints:
- GET /api/v2/user/billing/credits
- GET /api/v2/user/billing/transactions
- GET /api/v2/user/billing/can-afford
- POST /api/v2/user/billing/credits/deduct
- POST /api/v2/user/billing/credits/add

Created: 2026-01-08 (Stage 3: User/Admin routing migration)
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime

from app import app
from domains.billing.value_objects import TransactionType
from dependencies import get_current_user

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
def override_get_current_user(mock_user):
    """Override FastAPI dependency to return mock user."""
    async def _get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = _get_current_user
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
    return MagicMock(
        id="tx_123",
        amount=-10,
        balance_after=540,
        tx_type=TransactionType.GENERATION,
        description="AI image generation",
        created_at=datetime(2026, 1, 8, 12, 0, 0),
    )


@pytest.fixture
def mock_transaction_history_result(mock_transaction):
    """Mock GetTransactionHistoryQuery result."""
    return MagicMock(
        success=True,
        transactions=[mock_transaction],
        total_count=1,
    )


@pytest.fixture
def mock_deduct_result():
    """Mock DeductCreditsCommand result."""
    return MagicMock(
        success=True,
        amount_deducted=10,
        new_balance=540,
    )


@pytest.fixture
def mock_add_result():
    """Mock AddCreditsCommand result."""
    return MagicMock(
        success=True,
        amount_added=100,
        new_balance=650,
    )


# ==========================================
# GET /api/v2/user/billing/credits
# ==========================================

class TestGetCredits:
    """Tests for GET /api/v2/user/billing/credits endpoint."""

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
        assert data["current_balance"] == 550
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
        assert data["current_balance"] == 550
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
        mock_billing_service.get_operation_cost.return_value = MagicMock(amount=5)
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


# ==========================================
# POST /api/v2/user/billing/credits/deduct
# ==========================================

class TestDeductCredits:
    """Tests for POST /api/v2/user/billing/credits/deduct endpoint."""

    @patch('api.user.billing.get_container')
    def test_deduct_credits_success(
        self,
        mock_get_container,
        mock_deduct_result,
        override_get_current_user,
    ):
        """
        Test: Deduct credits successfully

        Given: User has sufficient credits
        When: POST to deduct 10 credits
        Then: Returns 200 with new balance

        Business Logic Verified:
        - Handler called with correct user_id and amount
        - Returns updated balance after deduction
        """
        # Arrange
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=mock_deduct_result)
        mock_container = MagicMock()
        mock_container.deduct_credits_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.post(
            "/api/v2/user/billing/credits/deduct",
            json={
                "amount": 10,
                "operation": "image_generation",
                "description": "AI image created",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["amount_deducted"] == 10
        assert data["new_balance"] == 540

        # Verify handler was called with correct command
        mock_handler.handle.assert_called_once()
        call_args = mock_handler.handle.call_args[0][0]
        assert call_args.user_id == "user_123"
        assert call_args.amount == 10

    @patch('api.user.billing.get_container')
    def test_deduct_credits_insufficient(
        self,
        mock_get_container,
        override_get_current_user,
    ):
        """
        Test: Insufficient credits (402 Payment Required)

        Given: User has insufficient credits
        When: POST to deduct credits
        Then: Returns 402 Payment Required

        Business Logic Verified:
        - Correctly rejects deduction when insufficient credits
        - Returns 402 status code for payment required
        """
        # Arrange
        mock_handler = MagicMock()
        mock_handler.handle = AsyncMock(return_value=MagicMock(
            success=False,
            error="Insufficient credits",
        ))
        mock_container = MagicMock()
        mock_container.deduct_credits_handler = mock_handler
        mock_get_container.return_value = mock_container

        # Act
        response = client.post(
            "/api/v2/user/billing/credits/deduct",
            json={
                "amount": 1000,
                "operation": "image_generation",
            },
        )

        # Assert
        assert response.status_code == 402
        # HTTPException returns plain text for 402


# ==========================================
# POST /api/v2/user/billing/credits/add
# ==========================================

class TestAddCredits:
    """Tests for POST /api/v2/user/billing/credits/add endpoint."""

    @patch('api.user.billing.get_container')
    def test_add_credits_success(
        self,
        mock_get_container,
        mock_add_result,
        override_get_current_user,
    ):
        """
        Test: Add credits successfully

        Given: Admin/internal request
        When: POST to add 100 permanent credits
        Then: Returns 200 with new balance

        Business Logic Verified:
        - Handler called with correct user_id, amount, and credit_type
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

        # Verify handler was called with correct command
        mock_handler.handle.assert_called_once()
        call_args = mock_handler.handle.call_args[0][0]
        assert call_args.user_id == "user_123"
        assert call_args.amount == 100
        # API converts credit_type to bucket enum
        from domains.billing.value_objects import CreditBucket
        assert call_args.bucket == CreditBucket.PERMANENT

    def test_add_credits_invalid_type(self, override_get_current_user):
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
                "amount": 100,
                "credit_type": "invalid",
                "reason": "Test",
            },
        )

        # Assert
        assert response.status_code == 422

"""
Generation Images API Tests - v2 DDD Architecture (v3.25)

Tests for api/user/generation_images.py

Endpoints:
- POST /api/v2/user/generate/images - Sync image generation
- POST /api/v2/user/generate/images/async - Async image generation

Updated: 2026-01-08
- v3.25: Updated to use DDD BillingService instead of SupabaseCreditRepository
         Tests now mock container.billing_service
         Added tests for generation failure refund

Coverage Target: 100% (2/2 endpoints)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any

from domains.billing.value_objects import Credits, TransactionType, CreditBucket
from domains.billing.aggregates.user_credits import UserCredits, CreditTransaction
from domains.billing.exceptions import InsufficientCreditsException

# Rate limiter bypass BEFORE app import
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

from app import app
from dependencies import get_current_user

client = TestClient(app)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_free_user() -> Dict[str, Any]:
    """Mock free tier user."""
    return {
        "id": "user_free_123",
        "email": "free@example.com",
        "tier": "free",
    }


@pytest.fixture
def mock_pro_user() -> Dict[str, Any]:
    """Mock pro tier user."""
    return {
        "id": "user_pro_456",
        "email": "pro@example.com",
        "tier": "pro",
    }


@pytest.fixture
def mock_user_no_credits() -> Dict[str, Any]:
    """Mock user without sufficient credits."""
    return {
        "id": "user_no_credits",
        "email": "nocredits@example.com",
        "tier": "free",
    }


@pytest.fixture
def override_free_user(mock_free_user):
    """Override dependency to return free user."""
    async def _get_user():
        return mock_free_user
    app.dependency_overrides[get_current_user] = _get_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def override_pro_user(mock_pro_user):
    """Override dependency to return pro user."""
    async def _get_user():
        return mock_pro_user
    app.dependency_overrides[get_current_user] = _get_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def valid_request() -> Dict[str, Any]:
    """Valid image generation request."""
    return {
        "prompts": ["A cute cartoon cat playing with yarn"],
        "num_images": 1,
        "image_size": "landscape_4_3",
    }


@pytest.fixture
def request_with_reference() -> Dict[str, Any]:
    """Request with reference image."""
    return {
        "prompts": ["A character in this style"],
        "num_images": 1,
        "reference_image": "https://example.com/ref.png",
        "reference_strength": 0.7,
    }


@pytest.fixture
def mock_user_credits():
    """Mock UserCredits aggregate for DDD billing."""
    user_credits = MagicMock(spec=UserCredits)
    user_credits.monthly_credits = 95
    user_credits.permanent_credits = 50
    user_credits.total_credits = 145
    user_credits.can_afford.return_value = True
    return user_credits


@pytest.fixture
def mock_credit_transaction():
    """Mock CreditTransaction for DDD billing."""
    tx = MagicMock(spec=CreditTransaction)
    tx.amount = -5
    tx.bucket = CreditBucket.MONTHLY
    tx.tx_type = TransactionType.GENERATION
    tx.balance_after = Credits(monthly=95, permanent=50)
    return tx


@pytest.fixture
def mock_generated_urls():
    """Mock generated image URLs."""
    return ["https://cdn.example.com/gen1.png"]


# ==========================================
# POST /api/v2/user/generate/images Tests (Sync)
# ==========================================

class TestGenImages:
    """Tests for POST /api/v2/user/generate/images endpoint."""

    @patch('api.user.generation_images.track_ai_generation')
    @patch('api.user.generation_images.get_supabase_client')
    @patch('api.user.generation_images.SupabaseAssetRepository')
    @patch('api.user.generation_images.generate_8_images')
    @patch('api.user.generation_images.get_container')
    @patch('application.services.generation_helpers.get_config')
    def test_gen_images_success_free_user(
        self,
        mock_get_config,
        mock_container,
        mock_gen_images,
        mock_asset_repo_class,
        mock_supabase,
        mock_track,
        mock_free_user,
        override_free_user,
        valid_request,
        mock_user_credits,
        mock_credit_transaction,
        mock_generated_urls,
    ):
        """
        Test: Successful image generation for free user.

        Given: Free tier user with sufficient credits
        When: POST /api/v2/user/generate/images with valid prompt
        Then: Returns generated image URLs and uses standard model (flux-schnell)

        Business Logic Verified:
        - Credits deducted via BillingService (5 per image)
        - Standard model used for free tier
        - Balance returned in response
        """
        # Arrange - Config returns cost
        mock_get_config.return_value = 5  # Base cost

        # Arrange - BillingService mock
        mock_billing = MagicMock()
        mock_billing.deduct_credits = AsyncMock(return_value=mock_credit_transaction)
        mock_billing.get_user_credits = AsyncMock(return_value=mock_user_credits)
        mock_container.return_value.billing_service = mock_billing

        mock_gen_images.return_value = (mock_generated_urls, "task_123")

        mock_asset_repo = MagicMock()
        mock_asset_repo.save_asset = AsyncMock()
        mock_asset_repo_class.return_value = mock_asset_repo

        mock_supabase_client = MagicMock()
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = MagicMock()
        mock_supabase.return_value = mock_supabase_client

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images",
            json=valid_request,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "image_urls" in data
        assert len(data["image_urls"]) == 1
        assert data["model_used"] == "flux-schnell"  # Free tier uses standard model
        assert data["balance"] == 145
        assert data["balance_monthly"] == 95
        assert data["balance_permanent"] == 50

        # Verify credit deduction via BillingService
        mock_billing.deduct_credits.assert_called_once()
        call_kwargs = mock_billing.deduct_credits.call_args.kwargs
        assert call_kwargs["amount"] == 5  # Config-driven cost
        assert call_kwargs["tx_type"] == TransactionType.GENERATION

    @patch('api.user.generation_images.track_ai_generation')
    @patch('api.user.generation_images.get_supabase_client')
    @patch('api.user.generation_images.SupabaseAssetRepository')
    @patch('api.user.generation_images.generate_8_images')
    @patch('api.user.generation_images.get_container')
    @patch('application.services.generation_helpers.get_config')
    def test_gen_images_pro_user_uses_dev_model(
        self,
        mock_get_config,
        mock_container,
        mock_gen_images,
        mock_asset_repo_class,
        mock_supabase,
        mock_track,
        mock_pro_user,
        override_pro_user,
        valid_request,
        mock_user_credits,
        mock_credit_transaction,
        mock_generated_urls,
    ):
        """
        Test: Pro user gets high-quality model.

        Given: Pro tier user
        When: POST /api/v2/user/generate/images
        Then: Uses flux-dev model (high quality)

        Business Logic Verified:
        - Pro tier users get flux-dev model
        """
        # Arrange
        mock_get_config.return_value = 5

        mock_billing = MagicMock()
        mock_billing.deduct_credits = AsyncMock(return_value=mock_credit_transaction)
        mock_billing.get_user_credits = AsyncMock(return_value=mock_user_credits)
        mock_container.return_value.billing_service = mock_billing

        mock_gen_images.return_value = (mock_generated_urls, "task_123")

        mock_asset_repo = MagicMock()
        mock_asset_repo.save_asset = AsyncMock()
        mock_asset_repo_class.return_value = mock_asset_repo

        mock_supabase_client = MagicMock()
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = MagicMock()
        mock_supabase.return_value = mock_supabase_client

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images",
            json=valid_request,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["model_used"] == "flux-dev"  # Pro tier uses high-quality model

    @patch('api.user.generation_images.get_container')
    @patch('application.services.generation_helpers.get_config')
    def test_gen_images_insufficient_credits(
        self,
        mock_get_config,
        mock_container,
        override_free_user,
        valid_request,
    ):
        """
        Test: Insufficient credits returns 402.

        Given: User without enough credits
        When: POST /api/v2/user/generate/images
        Then: Returns 402 Payment Required

        Business Logic Verified:
        - Credits checked before generation
        - 402 status for insufficient credits
        """
        # Arrange
        mock_get_config.return_value = 5

        mock_billing = MagicMock()
        mock_billing.deduct_credits = AsyncMock(
            side_effect=InsufficientCreditsException(required=5, available=0)
        )
        mock_container.return_value.billing_service = mock_billing

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images",
            json=valid_request,
        )

        # Assert
        assert response.status_code == 402
        assert "Insufficient" in response.json().get("detail", "")

    @patch('api.user.generation_images.track_ai_generation')
    @patch('api.user.generation_images.get_supabase_client')
    @patch('api.user.generation_images.SupabaseAssetRepository')
    @patch('api.user.generation_images.generate_8_images')
    @patch('api.user.generation_images.get_container')
    @patch('application.services.generation_helpers.get_config')
    def test_gen_images_reference_costs_more(
        self,
        mock_get_config,
        mock_container,
        mock_gen_images,
        mock_asset_repo_class,
        mock_supabase,
        mock_track,
        override_free_user,
        request_with_reference,
        mock_user_credits,
        mock_credit_transaction,
    ):
        """
        Test: Reference image costs 7 credits instead of 5.

        Given: Request with reference image
        When: POST /api/v2/user/generate/images
        Then: Charges 7 credits (config-driven)

        Business Logic Verified:
        - Reference image uses different config key
        - Cost loaded from credits.cost.image_generation_reference
        """
        # Arrange - Return different costs based on config key
        def config_side_effect(key, use_cache=True):
            if "reference" in key:
                return 7
            return 5
        mock_get_config.side_effect = config_side_effect

        mock_billing = MagicMock()
        mock_billing.deduct_credits = AsyncMock(return_value=mock_credit_transaction)
        mock_billing.get_user_credits = AsyncMock(return_value=mock_user_credits)
        mock_container.return_value.billing_service = mock_billing

        mock_gen_images.return_value = (["https://example.com/gen.png"], "task_123")

        mock_asset_repo = MagicMock()
        mock_asset_repo.save_asset = AsyncMock()
        mock_asset_repo_class.return_value = mock_asset_repo

        mock_supabase_client = MagicMock()
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = MagicMock()
        mock_supabase.return_value = mock_supabase_client

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images",
            json=request_with_reference,
        )

        # Assert
        assert response.status_code == 200

        # Verify credit deduction was 7 (not 5)
        call_kwargs = mock_billing.deduct_credits.call_args.kwargs
        assert call_kwargs["amount"] == 7  # 7 credits for reference image

    def test_gen_images_safety_violation(self, override_free_user):
        """
        Test: NSFW content blocked.

        Given: Prompt with blacklisted words
        When: POST /api/v2/user/generate/images
        Then: Returns 400 Safety Violation

        Business Logic Verified:
        - Safety filter blocks inappropriate content
        """
        # Act
        response = client.post(
            "/api/v2/user/generate/images/images",
            json={"prompts": ["nsfw content here"], "num_images": 1},
        )

        # Assert
        assert response.status_code == 400
        assert "Safety" in response.json().get("detail", "")

    def test_gen_images_unauthorized(self):
        """
        Test: Unauthenticated request returns 401.

        Given: No authentication
        When: POST /api/v2/user/generate/images
        Then: Returns 401 Unauthorized
        """
        # Act
        response = client.post(
            "/api/v2/user/generate/images/images",
            json={"prompts": ["test"], "num_images": 1},
        )

        # Assert
        assert response.status_code == 401

    @patch('api.user.generation_images.track_ai_generation')
    @patch('api.user.generation_images.get_supabase_client')
    @patch('api.user.generation_images.SupabaseAssetRepository')
    @patch('api.user.generation_images.generate_8_images')
    @patch('api.user.generation_images.get_container')
    @patch('application.services.generation_helpers.get_config')
    def test_gen_images_multiple_images(
        self,
        mock_get_config,
        mock_container,
        mock_gen_images,
        mock_asset_repo_class,
        mock_supabase,
        mock_track,
        override_free_user,
        mock_user_credits,
        mock_credit_transaction,
    ):
        """
        Test: Multiple images cost more credits.

        Given: Request for 4 images
        When: POST /api/v2/user/generate/images
        Then: Charges 5 * 4 = 20 credits

        Business Logic Verified:
        - Credit cost scales with num_images
        """
        # Arrange
        mock_get_config.return_value = 5

        mock_billing = MagicMock()
        mock_billing.deduct_credits = AsyncMock(return_value=mock_credit_transaction)
        mock_billing.get_user_credits = AsyncMock(return_value=mock_user_credits)
        mock_container.return_value.billing_service = mock_billing

        mock_gen_images.return_value = (
            ["https://example.com/1.png", "https://example.com/2.png",
             "https://example.com/3.png", "https://example.com/4.png"],
            "task_123"
        )

        mock_asset_repo = MagicMock()
        mock_asset_repo.save_asset = AsyncMock()
        mock_asset_repo_class.return_value = mock_asset_repo

        mock_supabase_client = MagicMock()
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = MagicMock()
        mock_supabase.return_value = mock_supabase_client

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images",
            json={"prompts": ["A cat"], "num_images": 4},
        )

        # Assert
        assert response.status_code == 200

        # Verify credit deduction was 20 (5 * 4)
        call_kwargs = mock_billing.deduct_credits.call_args.kwargs
        assert call_kwargs["amount"] == 20

    @patch('api.user.generation_images.get_container')
    @patch('application.services.generation_helpers.get_config')
    def test_gen_images_num_images_clamped(
        self,
        mock_get_config,
        mock_container,
        override_free_user,
    ):
        """
        Test: num_images is clamped to 1-4 range.

        Given: Request with num_images > 4
        When: Processing the request
        Then: num_images is clamped to 4
        """
        # Arrange
        mock_get_config.return_value = 5

        mock_billing = MagicMock()
        mock_billing.deduct_credits = AsyncMock(
            side_effect=InsufficientCreditsException(required=20, available=0)
        )
        mock_container.return_value.billing_service = mock_billing

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images",
            json={"prompts": ["test"], "num_images": 10},  # Will be clamped to 4
        )

        # Should calculate cost for 4 images (clamped from 10)
        call_kwargs = mock_billing.deduct_credits.call_args.kwargs
        assert call_kwargs["amount"] == 20  # 5 * 4 (clamped)

    @patch('api.user.generation_images.get_supabase_client')
    @patch('api.user.generation_images.SupabaseAssetRepository')
    @patch('api.user.generation_images.generate_8_images')
    @patch('api.user.generation_images.get_container')
    @patch('application.services.generation_helpers.get_config')
    def test_gen_images_generation_failure_refunds(
        self,
        mock_get_config,
        mock_container,
        mock_gen_images,
        mock_asset_repo_class,
        mock_supabase,
        override_free_user,
        valid_request,
        mock_user_credits,
        mock_credit_transaction,
    ):
        """
        Test: Generation failure triggers automatic refund.

        Given: Image generation fails after credit deduction
        When: POST /api/v2/user/generate/images
        Then: Credits refunded and returns 500

        Business Logic Verified:
        - Generation failure triggers refund via BillingService
        - Uses TransactionType.REFUND
        - Returns appropriate error message
        """
        # Arrange
        mock_get_config.return_value = 5

        mock_billing = MagicMock()
        mock_billing.deduct_credits = AsyncMock(return_value=mock_credit_transaction)
        mock_billing.get_user_credits = AsyncMock(return_value=mock_user_credits)
        mock_billing.add_credits = AsyncMock()  # Refund method
        mock_container.return_value.billing_service = mock_billing

        # Generation fails
        mock_gen_images.side_effect = Exception("AI API Error")

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images",
            json=valid_request,
        )

        # Assert
        assert response.status_code == 500
        assert "refunded" in response.json().get("detail", "").lower()

        # Verify refund was called via BillingService
        mock_billing.add_credits.assert_called_once()
        refund_kwargs = mock_billing.add_credits.call_args.kwargs
        assert refund_kwargs["amount"] == 5
        assert refund_kwargs["tx_type"] == TransactionType.REFUND
        assert refund_kwargs["bucket"] == CreditBucket.PERMANENT

    @patch('api.user.generation_images.get_supabase_client')
    @patch('api.user.generation_images.SupabaseAssetRepository')
    @patch('api.user.generation_images.generate_8_images')
    @patch('api.user.generation_images.get_container')
    @patch('application.services.generation_helpers.get_config')
    def test_gen_images_empty_result_refunds(
        self,
        mock_get_config,
        mock_container,
        mock_gen_images,
        mock_asset_repo_class,
        mock_supabase,
        override_free_user,
        valid_request,
        mock_user_credits,
        mock_credit_transaction,
    ):
        """
        Test: Empty generation result triggers refund.

        Given: Image generation returns no images
        When: POST /api/v2/user/generate/images
        Then: Credits refunded and returns 500

        Business Logic Verified:
        - Empty result triggers refund
        """
        # Arrange
        mock_get_config.return_value = 5

        mock_billing = MagicMock()
        mock_billing.deduct_credits = AsyncMock(return_value=mock_credit_transaction)
        mock_billing.get_user_credits = AsyncMock(return_value=mock_user_credits)
        mock_billing.add_credits = AsyncMock()
        mock_container.return_value.billing_service = mock_billing

        # Generation returns empty/None URLs
        mock_gen_images.return_value = ([None, None], "task_123")

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images",
            json=valid_request,
        )

        # Assert
        assert response.status_code == 500
        assert "refunded" in response.json().get("detail", "").lower()

        # Verify refund was called
        mock_billing.add_credits.assert_called_once()


# ==========================================
# POST /api/v2/user/generate/images/async Tests
# ==========================================

class TestGenImagesAsync:
    """Tests for POST /api/v2/user/generate/images/async endpoint."""

    @patch('api.user.generation_images.track_ai_generation')
    @patch('api.user.generation_images.task_queue')
    @patch('api.user.generation_images.get_supabase_client')
    @patch('api.user.generation_images.get_container')
    @patch('application.services.generation_helpers.get_config')
    def test_gen_images_async_success(
        self,
        mock_get_config,
        mock_container,
        mock_supabase,
        mock_task_queue,
        mock_track,
        override_free_user,
        valid_request,
        mock_user_credits,
        mock_credit_transaction,
    ):
        """
        Test: Async generation returns task_id immediately.

        Given: Valid request and sufficient credits
        When: POST /api/v2/user/generate/images/async
        Then: Returns task_id and queues the task

        Business Logic Verified:
        - Credits deducted immediately via BillingService
        - Task queued for processing
        - Returns WebSocket and poll URLs
        """
        # Arrange
        mock_get_config.return_value = 5

        mock_billing = MagicMock()
        mock_billing.deduct_credits = AsyncMock(return_value=mock_credit_transaction)
        mock_billing.get_user_credits = AsyncMock(return_value=mock_user_credits)
        mock_container.return_value.billing_service = mock_billing

        mock_supabase_client = MagicMock()
        mock_supabase_client.rpc.return_value.execute.return_value = MagicMock()
        mock_supabase.return_value = mock_supabase_client

        mock_task_queue.enqueue_image_generation.return_value = "task_gen_123"

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images/async",
            json=valid_request,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "queued"
        assert "websocket_url" in data
        assert "poll_url" in data
        assert data["credits_charged"] == 5
        assert data["balance"] == 145

    @patch('api.user.generation_images.get_container')
    @patch('application.services.generation_helpers.get_config')
    def test_gen_images_async_insufficient_credits(
        self,
        mock_get_config,
        mock_container,
        override_free_user,
        valid_request,
    ):
        """
        Test: Async with insufficient credits returns 402.

        Given: User without enough credits
        When: POST /api/v2/user/generate/images/async
        Then: Returns 402 Payment Required

        Business Logic Verified:
        - Credits checked before queueing
        """
        # Arrange
        mock_get_config.return_value = 5

        mock_billing = MagicMock()
        mock_billing.deduct_credits = AsyncMock(
            side_effect=InsufficientCreditsException(required=5, available=0)
        )
        mock_container.return_value.billing_service = mock_billing

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images/async",
            json=valid_request,
        )

        # Assert
        assert response.status_code == 402

    @patch('api.user.generation_images.track_ai_generation')
    @patch('api.user.generation_images.task_queue')
    @patch('api.user.generation_images.get_supabase_client')
    @patch('api.user.generation_images.get_container')
    @patch('application.services.generation_helpers.get_config')
    def test_gen_images_async_queue_failure_refunds(
        self,
        mock_get_config,
        mock_container,
        mock_supabase,
        mock_task_queue,
        mock_track,
        override_free_user,
        valid_request,
        mock_user_credits,
        mock_credit_transaction,
    ):
        """
        Test: Queue failure triggers refund.

        Given: Task queue fails to enqueue
        When: POST /api/v2/user/generate/images/async
        Then: Credits refunded and returns 503

        Business Logic Verified:
        - Failed queue triggers credit refund via BillingService
        - 503 returned for service unavailable
        """
        # Arrange
        mock_get_config.return_value = 5

        mock_billing = MagicMock()
        mock_billing.deduct_credits = AsyncMock(return_value=mock_credit_transaction)
        mock_billing.get_user_credits = AsyncMock(return_value=mock_user_credits)
        mock_billing.add_credits = AsyncMock()  # Refund
        mock_container.return_value.billing_service = mock_billing

        mock_supabase_client = MagicMock()
        mock_supabase_client.rpc.return_value.execute.return_value = MagicMock()
        mock_supabase.return_value = mock_supabase_client

        # Queue failure
        mock_task_queue.enqueue_image_generation.return_value = None

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images/async",
            json=valid_request,
        )

        # Assert
        assert response.status_code == 503
        assert "refunded" in response.json().get("detail", "").lower()

        # Verify refund via BillingService
        mock_billing.add_credits.assert_called_once()
        refund_kwargs = mock_billing.add_credits.call_args.kwargs
        assert refund_kwargs["tx_type"] == TransactionType.REFUND

    def test_gen_images_async_safety_violation(self, override_free_user):
        """
        Test: Async also blocks NSFW content.

        Given: Prompt with blacklisted words
        When: POST /api/v2/user/generate/images/async
        Then: Returns 400 Safety Violation
        """
        # Act
        response = client.post(
            "/api/v2/user/generate/images/images/async",
            json={"prompts": ["nude content"], "num_images": 1},
        )

        # Assert
        assert response.status_code == 400

    def test_gen_images_async_unauthorized(self):
        """
        Test: Unauthenticated request returns 401.

        Given: No authentication
        When: POST /api/v2/user/generate/images/async
        Then: Returns 401 Unauthorized
        """
        # Act
        response = client.post(
            "/api/v2/user/generate/images/images/async",
            json={"prompts": ["test"], "num_images": 1},
        )

        # Assert
        assert response.status_code == 401

    @patch('api.user.generation_images.track_ai_generation')
    @patch('api.user.generation_images.task_queue')
    @patch('api.user.generation_images.get_supabase_client')
    @patch('api.user.generation_images.get_container')
    @patch('application.services.generation_helpers.get_config')
    def test_gen_images_async_pro_high_priority(
        self,
        mock_get_config,
        mock_container,
        mock_supabase,
        mock_task_queue,
        mock_track,
        override_pro_user,
        valid_request,
        mock_user_credits,
        mock_credit_transaction,
    ):
        """
        Test: Pro users get high priority queue.

        Given: Pro tier user
        When: POST /api/v2/user/generate/images/async
        Then: Priority is 'high'

        Business Logic Verified:
        - Pro users get priority queue processing
        """
        # Arrange
        mock_get_config.return_value = 5

        mock_billing = MagicMock()
        mock_billing.deduct_credits = AsyncMock(return_value=mock_credit_transaction)
        mock_billing.get_user_credits = AsyncMock(return_value=mock_user_credits)
        mock_container.return_value.billing_service = mock_billing

        mock_supabase_client = MagicMock()
        mock_supabase_client.rpc.return_value.execute.return_value = MagicMock()
        mock_supabase.return_value = mock_supabase_client

        mock_task_queue.enqueue_image_generation.return_value = "task_gen_123"

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images/async",
            json=valid_request,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "high"


# ==========================================
# Coverage Summary
# ==========================================

"""
Test Coverage Summary:

POST /api/v2/user/generate/images (Sync):
- Success free user (flux-schnell model) with DDD BillingService
- Success pro user (flux-dev model)
- Insufficient credits (402) via InsufficientCreditsException
- Reference image costs more (config-driven: 7 vs 5)
- Safety violation (400)
- Unauthorized (401)
- Multiple images cost calculation
- num_images clamping (1-4)
- Generation failure triggers refund
- Empty result triggers refund

POST /api/v2/user/generate/images/async:
- Success returns task_id with BillingService
- Insufficient credits (402)
- Queue failure triggers refund (503)
- Safety violation (400)
- Unauthorized (401)
- Pro user high priority

Total Tests: 16
Coverage: 100% (2/2 endpoints)

Business Logic Tested:
- Credit deduction via DDD BillingService (config-driven costs)
- Model selection by tier (flux-schnell vs flux-dev)
- Safety filter for NSFW content
- num_images clamping (1-4)
- Async queue with refund on failure
- Priority queue for pro users
- Automatic refund on generation failure (NEW)
- Empty result refund handling (NEW)

v3.25 Changes:
- Migrated from SupabaseCreditRepository to DDD BillingService
- Tests now mock container.billing_service
- Added tests for generation failure refund
- Added tests for empty result refund
- Cost now loaded from config service

Not Tested (Requires Integration/E2E):
- Actual image generation
- Task queue processing
- WebSocket updates
- Database transaction consistency
"""

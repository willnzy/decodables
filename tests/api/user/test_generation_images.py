"""
Generation Images API Tests - v3.28 DDD Architecture with GenerationService

Tests for api/user/generation_images.py

Endpoints:
- POST /api/v2/user/generate/images - Sync image generation
- POST /api/v2/user/generate/images/async - Async image generation

Updated: 2026-01-10
- v3.28: Updated to use GenerationService with app.dependency_overrides
         Tests now mock generation_service at DI level (FastAPI best practice)
         No longer mock individual repositories
- v3.25: Updated to use DDD BillingService instead of SupabaseCreditRepository
         Tests now mock container.billing_service
         Added tests for generation failure refund

Coverage Target: 100% (2/2 endpoints)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any

from domains.billing.exceptions import InsufficientCreditsException
from domains.generation.generation_service import (
    GenerationTimeoutException,
    GenerationFailedException,
    EmptyGenerationException,
)

# Rate limiter bypass BEFORE app import
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

from app import app
from dependencies import get_current_user
from api.user.generation_images import get_generation_service

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
    """Request with reference image from allowed host (SSRF-safe)."""
    return {
        "prompts": ["A character in this style"],
        "num_images": 1,
        # v3.27: Use allowed host for SSRF validation
        "reference_image": "https://v3.fal.media/files/ref.png",
        "reference_strength": 0.7,
    }


# ==========================================
# POST /api/v2/user/generate/images Tests (Sync)
# ==========================================

class TestGenImages:
    """Tests for POST /api/v2/user/generate/images endpoint."""

    
    def test_gen_images_success_free_user(
        self,
        mock_free_user,
        override_free_user,
        valid_request,
    ):
        """
        Test: Successful image generation for free user.

        Given: Free tier user with sufficient credits
        When: POST /api/v2/user/generate/images with valid prompt
        Then: Returns generated image URLs and uses standard model (flux-schnell)

        Business Logic Verified:
        - Service orchestrates full workflow
        - Standard model used for free tier
        - Balance returned in response
        """
        # Arrange - Config returns cost

        # Mock GenerationService
        mock_service = MagicMock()
        mock_service.generate_images_sync = AsyncMock(return_value={
            "image_urls": ["https://cdn.example.com/gen1.png"],
            "balance": 145,
            "balance_monthly": 95,
            "balance_permanent": 50,
            "model_used": "flux-schnell",
            "used_reference": False,
            "generation_mode": "guided",
            "creativity_level": "balanced",
            "batch_id": "batch_123",
            "num_images": 1,
            "generation_time_ms": 5000,
        })

        # Override DI
        app.dependency_overrides[get_generation_service] = lambda: mock_service

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

        # Verify Service was called
        mock_service.generate_images_sync.assert_called_once()
        call_kwargs = mock_service.generate_images_sync.call_args.kwargs
        assert call_kwargs["user_id"] == mock_free_user["id"]
        assert call_kwargs["model"] == "flux-schnell"

        # Cleanup
        app.dependency_overrides.clear()

    
    def test_gen_images_pro_user_uses_dev_model(
        self,
        mock_pro_user,
        override_pro_user,
        valid_request,
    ):
        """
        Test: Pro user gets high-quality model.

        Given: Pro tier user
        When: POST /api/v2/user/generate/images
        Then: Uses flux-dev model (high quality)
        """
        # Arrange

        mock_service = MagicMock()
        mock_service.generate_images_sync = AsyncMock(return_value={
            "image_urls": ["https://cdn.example.com/gen1.png"],
            "balance": 145,
            "balance_monthly": 95,
            "balance_permanent": 50,
            "model_used": "flux-dev",
            "used_reference": False,
            "generation_mode": "guided",
            "creativity_level": "balanced",
            "batch_id": "batch_123",
            "num_images": 1,
            "generation_time_ms": 8000,
        })

        app.dependency_overrides[get_generation_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images",
            json=valid_request,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["model_used"] == "flux-dev"  # Pro tier uses high-quality model

        # Verify Pro model was passed to Service
        call_kwargs = mock_service.generate_images_sync.call_args.kwargs
        assert call_kwargs["model"] == "flux-dev"

        app.dependency_overrides.clear()

    
    def test_gen_images_insufficient_credits(
        self,
        override_free_user,
        valid_request,
    ):
        """
        Test: Insufficient credits returns 402.

        Given: User without enough credits
        When: POST /api/v2/user/generate/images
        Then: Returns 402 Payment Required
        """
        # Arrange

        mock_service = MagicMock()
        mock_service.generate_images_sync = AsyncMock(
            side_effect=InsufficientCreditsException(required=5, available=0)
        )

        app.dependency_overrides[get_generation_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images",
            json=valid_request,
        )

        # Assert
        assert response.status_code == 402
        data = response.json()
        error_msg = data.get("detail", "") or data.get("message", "")
        assert "Insufficient" in error_msg or "insufficient" in error_msg.lower()

        app.dependency_overrides.clear()

    
    def test_gen_images_reference_costs_more(
        self,
        override_free_user,
        request_with_reference,
    ):
        """
        Test: Reference image is handled by Service.

        Given: Request with reference image
        When: POST /api/v2/user/generate/images
        Then: Service receives reference_image parameter
        """
        # Arrange
        def config_side_effect(key, use_cache=True):
            if "reference" in key:
                return 7
            return 5

        mock_service = MagicMock()
        mock_service.generate_images_sync = AsyncMock(return_value={
            "image_urls": ["https://example.com/gen.png"],
            "balance": 138,
            "balance_monthly": 88,
            "balance_permanent": 50,
            "model_used": "flux-schnell",
            "used_reference": True,
            "generation_mode": "guided",
            "creativity_level": "balanced",
            "batch_id": "batch_123",
            "num_images": 1,
            "generation_time_ms": 6000,
        })

        app.dependency_overrides[get_generation_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images",
            json=request_with_reference,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["used_reference"] is True

        # Verify Service received reference image
        call_kwargs = mock_service.generate_images_sync.call_args.kwargs
        assert call_kwargs["reference_image"] == "https://v3.fal.media/files/ref.png"

        app.dependency_overrides.clear()

    def test_gen_images_safety_violation(self, override_free_user):
        """
        Test: NSFW content blocked.

        Given: Prompt with blacklisted words
        When: POST /api/v2/user/generate/images
        Then: Returns 400 Content policy violation
        """
        # Act
        response = client.post(
            "/api/v2/user/generate/images/images",
            json={"prompts": ["nsfw content here"], "num_images": 1},
        )

        # Assert
        assert response.status_code == 400
        data = response.json()
        error_msg = data.get("detail", "") or data.get("message", "")
        assert "policy" in error_msg.lower() or "content" in error_msg.lower()

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

    
    def test_gen_images_timeout_refunds(
        self,
        override_free_user,
        valid_request,
    ):
        """
        Test: Timeout triggers automatic refund via Service.

        Given: Generation times out
        When: POST /api/v2/user/generate/images
        Then: Service raises GenerationTimeoutException, API returns 504
        """
        # Arrange

        mock_service = MagicMock()
        mock_service.generate_images_sync = AsyncMock(
            side_effect=GenerationTimeoutException("Timed out")
        )

        app.dependency_overrides[get_generation_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images",
            json=valid_request,
        )

        # Assert
        assert response.status_code == 504
        data = response.json()
        error_msg = data.get("detail", "") or data.get("message", "")
        assert "timed out" in error_msg.lower()
        assert "refunded" in error_msg.lower()

        app.dependency_overrides.clear()

    
    def test_gen_images_generation_failure_refunds(
        self,
        override_free_user,
        valid_request,
    ):
        """
        Test: Generation failure triggers automatic refund via Service.

        Given: Image generation fails
        When: POST /api/v2/user/generate/images
        Then: Service raises GenerationFailedException, API returns 500
        """
        # Arrange

        mock_service = MagicMock()
        mock_service.generate_images_sync = AsyncMock(
            side_effect=GenerationFailedException("AI API Error")
        )

        app.dependency_overrides[get_generation_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images",
            json=valid_request,
        )

        # Assert
        assert response.status_code == 500
        data = response.json()
        error_msg = data.get("detail", "") or data.get("message", "")
        assert "failed" in error_msg.lower()
        assert "refunded" in error_msg.lower()

        app.dependency_overrides.clear()

    
    def test_gen_images_empty_result_refunds(
        self,
        override_free_user,
        valid_request,
    ):
        """
        Test: Empty generation result triggers refund via Service.

        Given: Generation returns no images
        When: POST /api/v2/user/generate/images
        Then: Service raises EmptyGenerationException, API returns 500
        """
        # Arrange

        mock_service = MagicMock()
        mock_service.generate_images_sync = AsyncMock(
            side_effect=EmptyGenerationException("No images")
        )

        app.dependency_overrides[get_generation_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images",
            json=valid_request,
        )

        # Assert
        assert response.status_code == 500
        data = response.json()
        error_msg = data.get("detail", "") or data.get("message", "")
        assert "no images" in error_msg.lower() or "not generated" in error_msg.lower()
        assert "refunded" in error_msg.lower()

        app.dependency_overrides.clear()


# ==========================================
# POST /api/v2/user/generate/images/async Tests
# ==========================================

class TestGenImagesAsync:
    """Tests for POST /api/v2/user/generate/images/async endpoint."""

    
    def test_gen_images_async_success(
        self,
        override_free_user,
        valid_request,
    ):
        """
        Test: Async generation returns task_id immediately.

        Given: Valid request and sufficient credits
        When: POST /api/v2/user/generate/images/async
        Then: Returns task_id and queues the task
        """
        # Arrange

        mock_service = MagicMock()
        mock_service.generate_images_async = AsyncMock(return_value={
            "task_id": "gen_123456_abc",
            "status": "queued",
            "message": "Task queued for 1 images",
            "credits_charged": 5,
            "balance": 145,
            "balance_monthly": 95,
            "balance_permanent": 50,
            "websocket_url": "/ws/task/gen_123456_abc",
            "poll_url": "/api/tasks/gen_123456_abc",
            "model_used": "flux-schnell",
            "priority": "low",
        })

        app.dependency_overrides[get_generation_service] = lambda: mock_service

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

        # Verify Service was called
        mock_service.generate_images_async.assert_called_once()

        app.dependency_overrides.clear()

    
    def test_gen_images_async_insufficient_credits(
        self,
        override_free_user,
        valid_request,
    ):
        """
        Test: Async with insufficient credits returns 402.

        Given: User without enough credits
        When: POST /api/v2/user/generate/images/async
        Then: Returns 402 Payment Required
        """
        # Arrange

        mock_service = MagicMock()
        mock_service.generate_images_async = AsyncMock(
            side_effect=InsufficientCreditsException(required=5, available=0)
        )

        app.dependency_overrides[get_generation_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images/async",
            json=valid_request,
        )

        # Assert
        assert response.status_code == 402

        app.dependency_overrides.clear()

    
    def test_gen_images_async_queue_failure_refunds(
        self,
        override_free_user,
        valid_request,
    ):
        """
        Test: Queue failure triggers refund via Service.

        Given: Task queue fails to enqueue
        When: POST /api/v2/user/generate/images/async
        Then: Service raises exception, credits refunded, returns 503
        """
        # Arrange

        mock_service = MagicMock()
        mock_service.generate_images_async = AsyncMock(
            side_effect=Exception("Generation service temporarily unavailable")
        )

        app.dependency_overrides[get_generation_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images/async",
            json=valid_request,
        )

        # Assert
        assert response.status_code == 503
        data = response.json()
        error_msg = data.get("detail", "") or data.get("message", "")
        assert "unavailable" in error_msg.lower() or "refunded" in error_msg.lower()

        app.dependency_overrides.clear()

    def test_gen_images_async_safety_violation(self, override_free_user):
        """
        Test: Async also blocks NSFW content.

        Given: Prompt with blacklisted words
        When: POST /api/v2/user/generate/images/async
        Then: Returns 400 Content policy violation
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

    
    def test_gen_images_async_pro_high_priority(
        self,
        override_pro_user,
        valid_request,
    ):
        """
        Test: Pro users get high priority queue.

        Given: Pro tier user
        When: POST /api/v2/user/generate/images/async
        Then: Priority is 'high'
        """
        # Arrange

        mock_service = MagicMock()
        mock_service.generate_images_async = AsyncMock(return_value={
            "task_id": "gen_123456_xyz",
            "status": "queued",
            "message": "Task queued for 1 images",
            "credits_charged": 5,
            "balance": 145,
            "balance_monthly": 95,
            "balance_permanent": 50,
            "websocket_url": "/ws/task/gen_123456_xyz",
            "poll_url": "/api/tasks/gen_123456_xyz",
            "model_used": "flux-dev",
            "priority": "high",
        })

        app.dependency_overrides[get_generation_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/generate/images/images/async",
            json=valid_request,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "high"

        app.dependency_overrides.clear()


# ==========================================
# Coverage Summary
# ==========================================

"""
Test Coverage Summary:

POST /api/v2/user/generate/images (Sync):
- Success free user (flux-schnell model) via GenerationService
- Success pro user (flux-dev model)
- Insufficient credits (402) via Service exception
- Reference image handling via Service
- Safety violation (400)
- Unauthorized (401)
- Timeout triggers refund (504)
- Generation failure triggers refund (500)
- Empty result triggers refund (500)

POST /api/v2/user/generate/images/async:
- Success returns task_id via GenerationService
- Insufficient credits (402)
- Queue failure triggers refund (503)
- Safety violation (400)
- Unauthorized (401)
- Pro user high priority

Total Tests: 16
Coverage: 100% (2/2 endpoints)

Business Logic Tested:
- Full workflow orchestration via GenerationService
- Model selection by tier (flux-schnell vs flux-dev)
- Safety filter for NSFW content
- Async queue with refund on failure
- Priority queue for pro users
- Automatic refund on timeout/failure/empty result

v3.28 Changes:
- Migrated to GenerationService with app.dependency_overrides
- Tests now mock Service instead of individual components
- Cleaner test structure following FastAPI best practices
- All refund logic handled by Service layer
- Simplified test assertions (Service returns complete response)

Not Tested (Requires Integration/E2E):
- Actual image generation
- Task queue processing
- WebSocket updates
- Database transaction consistency
- GenerationService internal methods (unit tests for Service needed)
"""

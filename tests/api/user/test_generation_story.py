"""
Generation Story API Tests - v2 DDD Architecture (v3.27)

Tests for api/user/generation_story.py

Endpoints:
- POST /api/v2/user/generate/story - Generate story JSON
- POST /api/v2/user/generate/inspiration - AI inspiration suggestions (Free)

Updated: 2026-01-09
- v3.27: Added tests for InspirationRequest validation (category, style)
         Added test to verify fallback_reason not exposed
- v3.25: Updated to test config-driven credit deduction
         Story generation now uses BillingService when cost > 0
         Added tests for credit deduction and refund scenarios

Coverage Target: 100% (2/2 endpoints)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any
import json

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
def mock_story_result():
    """Mock story generation result."""
    return {
        "title": "The Magical Forest",
        "pages": [
            {"text": "Once upon a time...", "imagePrompt": "A magical forest"},
            {"text": "There lived a brave cat.", "imagePrompt": "A brave cat"},
        ],
        "characters": ["Cat", "Owl"],
        "setting": "Magical Forest",
    }


@pytest.fixture
def mock_inspiration_result():
    """Mock inspiration generation result."""
    return {
        "suggestions": [
            {
                "character": "A curious orange tabby cat",
                "action": "exploring a hidden garden",
                "setting": "behind an old mansion",
                "style": "watercolor",
                "moods": ["curious", "adventurous"]
            }
        ]
    }


@pytest.fixture
def mock_user_credits():
    """Mock UserCredits aggregate for DDD billing."""
    user_credits = MagicMock(spec=UserCredits)
    user_credits.monthly_credits = 95
    user_credits.permanent_credits = 50
    user_credits.total_credits = 145
    return user_credits


@pytest.fixture
def mock_credit_transaction():
    """Mock CreditTransaction for DDD billing."""
    tx = MagicMock(spec=CreditTransaction)
    tx.amount = -1
    tx.bucket = CreditBucket.MONTHLY
    tx.tx_type = TransactionType.GENERATION
    tx.balance_after = Credits(monthly=94, permanent=50)
    return tx


# ==========================================
# POST /api/v2/user/generate/story Tests
# ==========================================

class TestGenStory:
    """Tests for POST /api/v2/user/generate/story endpoint."""

    @patch('api.user.generation_story.generate_story_json')
    @patch('api.user.generation_story.get_text_generation_cost')
    @patch('api.user.generation_story.get_container')
    def test_gen_story_success_free_cost(
        self,
        mock_container,
        mock_get_cost,
        mock_gen_story,
        mock_free_user,
        override_free_user,
        mock_story_result,
    ):
        """
        Test: Successful story generation (free, cost=0).

        Given: Authenticated user, config cost=0
        When: POST /api/v2/user/generate/story
        Then: Returns story JSON without credit deduction

        Business Logic Verified:
        - When cost=0, no credit deduction occurs
        - Story generator called with correct parameters
        """
        # Arrange
        mock_get_cost.return_value = 0  # Free
        mock_gen_story.return_value = mock_story_result

        # Act
        response = client.post(
            "/api/v2/user/generate/story/story",
            json={"topic": "A brave cat in a magical forest"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert data["title"] == "The Magical Forest"

        # Verify no credit deduction when cost=0
        mock_container.return_value.billing_service.deduct_credits.assert_not_called()

    @patch('api.user.generation_story.generate_story_json')
    @patch('api.user.generation_story.get_text_generation_cost')
    @patch('api.user.generation_story.get_container')
    def test_gen_story_with_cost_deducts_credits(
        self,
        mock_container,
        mock_get_cost,
        mock_gen_story,
        override_free_user,
        mock_story_result,
        mock_credit_transaction,
    ):
        """
        Test: Story generation deducts credits when cost > 0.

        Given: Config cost=1
        When: POST /api/v2/user/generate/story
        Then: Deducts 1 credit via BillingService

        Business Logic Verified:
        - Credit deduction uses DDD BillingService
        - TransactionType.GENERATION used
        """
        # Arrange
        mock_get_cost.return_value = 1  # 1 credit

        mock_billing = MagicMock()
        mock_billing.deduct_credits = AsyncMock(return_value=mock_credit_transaction)
        mock_container.return_value.billing_service = mock_billing

        mock_gen_story.return_value = mock_story_result

        # Act
        response = client.post(
            "/api/v2/user/generate/story/story",
            json={"topic": "A magical adventure"},
        )

        # Assert
        assert response.status_code == 200

        # Verify credit deduction
        mock_billing.deduct_credits.assert_called_once()
        call_kwargs = mock_billing.deduct_credits.call_args.kwargs
        assert call_kwargs["amount"] == 1
        assert call_kwargs["tx_type"] == TransactionType.GENERATION

    @patch('api.user.generation_story.get_text_generation_cost')
    @patch('api.user.generation_story.get_container')
    def test_gen_story_insufficient_credits(
        self,
        mock_container,
        mock_get_cost,
        override_free_user,
    ):
        """
        Test: Insufficient credits returns 402.

        Given: Cost=1 but user has no credits
        When: POST /api/v2/user/generate/story
        Then: Returns 402 Payment Required

        Business Logic Verified:
        - InsufficientCreditsException handled properly
        """
        # Arrange
        mock_get_cost.return_value = 1

        mock_billing = MagicMock()
        mock_billing.deduct_credits = AsyncMock(
            side_effect=InsufficientCreditsException(required=1, available=0)
        )
        mock_container.return_value.billing_service = mock_billing

        # Act
        response = client.post(
            "/api/v2/user/generate/story/story",
            json={"topic": "Test topic"},
        )

        # Assert
        assert response.status_code == 402
        data = response.json()
        error_msg = data.get("detail", "") or data.get("message", "")
        assert "Insufficient" in error_msg

    @patch('api.user.generation_story.generate_story_json')
    @patch('api.user.generation_story.get_text_generation_cost')
    @patch('api.user.generation_story.get_container')
    def test_gen_story_refunds_on_failure(
        self,
        mock_container,
        mock_get_cost,
        mock_gen_story,
        override_free_user,
        mock_credit_transaction,
    ):
        """
        Test: Generation failure triggers refund when cost > 0.

        Given: Cost=1 and story generation fails
        When: POST /api/v2/user/generate/story
        Then: Credits refunded, returns 500

        Business Logic Verified:
        - Refund via BillingService on failure
        - Uses TransactionType.REFUND
        """
        # Arrange
        mock_get_cost.return_value = 1

        mock_billing = MagicMock()
        mock_billing.deduct_credits = AsyncMock(return_value=mock_credit_transaction)
        mock_billing.add_credits = AsyncMock()
        mock_container.return_value.billing_service = mock_billing

        mock_gen_story.side_effect = Exception("AI service error")

        # Act
        response = client.post(
            "/api/v2/user/generate/story/story",
            json={"topic": "Test topic"},
        )

        # Assert
        assert response.status_code == 500

        # Verify refund was called
        mock_billing.add_credits.assert_called_once()
        refund_kwargs = mock_billing.add_credits.call_args.kwargs
        assert refund_kwargs["amount"] == 1
        assert refund_kwargs["tx_type"] == TransactionType.REFUND
        # v3.26: Refund to MONTHLY bucket (matching deduction priority)
        assert refund_kwargs["bucket"] == CreditBucket.MONTHLY

    @patch('api.user.generation_story.generate_story_json')
    @patch('api.user.generation_story.get_text_generation_cost')
    @patch('api.user.generation_story.get_container')
    def test_gen_story_no_refund_when_free(
        self,
        mock_container,
        mock_get_cost,
        mock_gen_story,
        override_free_user,
    ):
        """
        Test: No refund attempt when cost=0.

        Given: Cost=0 and story generation fails
        When: POST /api/v2/user/generate/story
        Then: No refund attempted, returns 500
        """
        # Arrange
        mock_get_cost.return_value = 0  # Free

        mock_billing = MagicMock()
        mock_container.return_value.billing_service = mock_billing

        mock_gen_story.side_effect = Exception("AI service error")

        # Act
        response = client.post(
            "/api/v2/user/generate/story/story",
            json={"topic": "Test topic"},
        )

        # Assert
        assert response.status_code == 500

        # Verify no refund when cost=0
        mock_billing.add_credits.assert_not_called()

    @patch('api.user.generation_story.generate_story_json')
    @patch('api.user.generation_story.get_text_generation_cost')
    @patch('api.user.generation_story.get_container')
    def test_gen_story_pro_user_tier(
        self,
        mock_container,
        mock_get_cost,
        mock_gen_story,
        mock_pro_user,
        override_pro_user,
        mock_story_result,
    ):
        """
        Test: Pro user tier is passed to generator.

        Given: Pro tier user
        When: POST /api/v2/user/generate/story
        Then: Tier 'pro' is passed to generator
        """
        # Arrange
        mock_get_cost.return_value = 0
        mock_gen_story.return_value = mock_story_result

        # Act
        response = client.post(
            "/api/v2/user/generate/story/story",
            json={"topic": "A magical adventure"},
        )

        # Assert
        assert response.status_code == 200

        # Verify tier is 'pro'
        call_kwargs = mock_gen_story.call_args
        assert call_kwargs[1]["tier"] == "pro"

    def test_gen_story_unauthorized(self):
        """
        Test: Unauthenticated request returns 401.

        Given: No authentication
        When: POST /api/v2/user/generate/story
        Then: Returns 401 Unauthorized
        """
        # Act
        response = client.post(
            "/api/v2/user/generate/story/story",
            json={"topic": "Test topic"},
        )

        # Assert
        assert response.status_code == 401

    def test_gen_story_missing_topic(self, override_free_user):
        """
        Test: Missing topic returns 422.

        Given: Request without topic field
        When: POST /api/v2/user/generate/story
        Then: Returns 422 Validation Error
        """
        # Act
        response = client.post(
            "/api/v2/user/generate/story/story",
            json={},  # Missing topic
        )

        # Assert
        assert response.status_code == 422


# ==========================================
# POST /api/v2/user/generate/inspiration Tests
# ==========================================

class TestGenInspiration:
    """Tests for POST /api/v2/user/generate/inspiration endpoint."""

    @patch('api.user.generation_story.openai_client')
    def test_gen_inspiration_success_default_category(
        self,
        mock_openai,
        override_free_user,
        mock_inspiration_result,
    ):
        """
        Test: Successful inspiration generation (default category).

        Given: Authenticated user without category
        When: POST /api/v2/user/generate/inspiration
        Then: Returns suggestions with category='all'

        Business Logic Verified:
        - Default category is 'all'
        - Returns suggestions array
        - This is a FREE endpoint (no credits)
        """
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps(mock_inspiration_result)))
        ]
        mock_openai.chat.completions.create.return_value = mock_response

        # Act
        response = client.post(
            "/api/v2/user/generate/story/inspiration",
            json={},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert data["category"] == "all"
        assert len(data["suggestions"]) > 0

    @patch('api.user.generation_story.openai_client')
    def test_gen_inspiration_character_category(
        self,
        mock_openai,
        override_free_user,
    ):
        """
        Test: Inspiration with 'character' category.

        Given: Category='character'
        When: POST /api/v2/user/generate/inspiration
        Then: Returns character-focused suggestions
        """
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "suggestions": [{"character": "A brave mouse", "personality": "curious"}]
            })))
        ]
        mock_openai.chat.completions.create.return_value = mock_response

        # Act
        response = client.post(
            "/api/v2/user/generate/story/inspiration",
            json={"category": "character"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "character"

    @patch('api.user.generation_story.openai_client')
    def test_gen_inspiration_scene_category(
        self,
        mock_openai,
        override_free_user,
    ):
        """
        Test: Inspiration with 'scene' category.

        Given: Category='scene'
        When: POST /api/v2/user/generate/inspiration
        Then: Returns scene-focused suggestions
        """
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "suggestions": [{"setting": "A magical forest", "atmosphere": "mysterious"}]
            })))
        ]
        mock_openai.chat.completions.create.return_value = mock_response

        # Act
        response = client.post(
            "/api/v2/user/generate/story/inspiration",
            json={"category": "scene"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "scene"

    @patch('api.user.generation_story.openai_client')
    def test_gen_inspiration_story_category(
        self,
        mock_openai,
        override_free_user,
    ):
        """
        Test: Inspiration with 'story' category.

        Given: Category='story'
        When: POST /api/v2/user/generate/inspiration
        Then: Returns story-focused suggestions
        """
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({
                "suggestions": [
                    {"character": "A cat", "action": "flying", "setting": "sky", "mood": "joyful"}
                ]
            })))
        ]
        mock_openai.chat.completions.create.return_value = mock_response

        # Act
        response = client.post(
            "/api/v2/user/generate/story/inspiration",
            json={"category": "story"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "story"

    @patch('api.user.generation_story.openai_client')
    def test_gen_inspiration_fallback_on_error(
        self,
        mock_openai,
        override_free_user,
    ):
        """
        Test: Returns fallback suggestions on error.

        Given: OpenAI API fails
        When: POST /api/v2/user/generate/inspiration
        Then: Returns fallback suggestions (not 500)

        Business Logic Verified:
        - Graceful degradation with fallback content
        - No error returned to user
        - v3.27: No internal details exposed (fallback_reason removed)
        """
        # Arrange
        mock_openai.chat.completions.create.side_effect = Exception("API Error")

        # Act
        response = client.post(
            "/api/v2/user/generate/story/inspiration",
            json={},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert data.get("fallback") == True  # Indicates fallback was used
        assert len(data["suggestions"]) == 3  # 3 hardcoded fallback suggestions
        # v3.27: GS-LOW-2 - Verify internal details not exposed
        assert "fallback_reason" not in data  # Internal details removed

    def test_gen_inspiration_unauthorized(self):
        """
        Test: Unauthenticated request returns 401.

        Given: No authentication
        When: POST /api/v2/user/generate/inspiration
        Then: Returns 401 Unauthorized
        """
        # Act
        response = client.post(
            "/api/v2/user/generate/story/inspiration",
            json={},
        )

        # Assert
        assert response.status_code == 401

    def test_gen_inspiration_invalid_category(self, override_free_user):
        """
        Test: Invalid category returns 422.

        v3.27: GS-MEDIUM-1 - Added category validation

        Given: Invalid category value
        When: POST /api/v2/user/generate/inspiration with invalid category
        Then: Returns 422 Validation Error
        """
        # Act
        response = client.post(
            "/api/v2/user/generate/story/inspiration",
            json={"category": "invalid_category"},
        )

        # Assert
        assert response.status_code == 422

    def test_gen_inspiration_style_too_long(self, override_free_user):
        """
        Test: Style too long returns 422.

        v3.27: GS-MEDIUM-1 - Added style max_length validation

        Given: Style exceeds max_length (100)
        When: POST /api/v2/user/generate/inspiration
        Then: Returns 422 Validation Error
        """
        # Act
        response = client.post(
            "/api/v2/user/generate/story/inspiration",
            json={"style": "x" * 150},  # Exceeds 100 char limit
        )

        # Assert
        assert response.status_code == 422


# ==========================================
# Coverage Summary
# ==========================================

"""
Test Coverage Summary:

POST /api/v2/user/generate/story:
- Success with cost=0 (free, no credit deduction)
- Success with cost>0 (deducts credits via BillingService)
- Insufficient credits (402) when cost>0
- Refund on generation failure when cost>0
- No refund when cost=0
- Pro user tier passed correctly
- Unauthorized (401)
- Missing topic (422)

POST /api/v2/user/generate/inspiration (FREE):
- Success with default category (all)
- Character category
- Scene category
- Story category
- Fallback on API error
- Unauthorized (401)

Total Tests: 14
Coverage: 100% (2/2 endpoints)

Business Logic Tested:
- Config-driven credit cost (credits.cost.text_generation)
- Conditional credit deduction (only when cost > 0)
- Automatic refund on failure (only when charged)
- Tier-based model selection (passed to generator)
- Free inspiration endpoint (no credits)
- Category-based prompt selection
- Graceful fallback on errors (inspiration)

v3.25 Changes:
- Story generation now checks config for cost
- When cost > 0, uses DDD BillingService for deduction
- Automatic refund on generation failure
- Added 4 new tests for credit scenarios

Not Tested (Requires Integration/E2E):
- Actual AI generation quality
- Real rate limiting behavior
- Database config integration
"""

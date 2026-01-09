"""
Generation Story API Tests - v3.28 (DDD + FastAPI Best Practice)

Tests for api/user/generation_story.py v3.28

Changes:
- v3.28: Completely rewritten using app.dependency_overrides
         Mock StoryGenerationService and InspirationService
         Aligned with Generation Images/PDF testing patterns
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

# Rate limiter bypass BEFORE app import
@patch("infrastructure.rate_limiter.limiter.enabled", False)
def noop_decorator(*args, **kwargs):
    return lambda f: f
patch("infrastructure.rate_limiter.limiter.limit", noop_decorator).start()

from app import app
from dependencies import get_current_user
from api.user.generation_story import get_story_service, get_inspiration_service
from domains.generation.story_service import StoryGenerationException
from domains.billing.exceptions import InsufficientCreditsException

client = TestClient(app)


# ==========================================
# Test Fixtures
# ==========================================

@pytest.fixture
def mock_free_user():
    return {"id": "user_free_123", "email": "free@example.com", "tier": "free"}


@pytest.fixture
def override_free_user(mock_free_user):
    app.dependency_overrides[get_current_user] = lambda: mock_free_user
    yield
    app.dependency_overrides.clear()


# ==========================================
# POST /api/v2/user/generate/story Tests
# ==========================================

class TestGenStory:
    """Tests for POST /api/v2/user/generate/story endpoint."""

    def test_gen_story_success(self, override_free_user):
        """Test: Successful story generation via Service."""
        # Arrange
        mock_service = MagicMock()
        mock_service.generate_story = AsyncMock(return_value={
            "title": "The Magical Forest",
            "pages": [{"text": "Once upon a time...", "imagePrompt": "A magical forest"}],
            "characters": ["Cat", "Owl"],
            "setting": "Magical Forest",
        })

        app.dependency_overrides[get_story_service] = lambda: mock_service

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

        mock_service.generate_story.assert_called_once()
        call_kwargs = mock_service.generate_story.call_args.kwargs
        assert call_kwargs["topic"] == "A brave cat in a magical forest"

        app.dependency_overrides.clear()

    def test_gen_story_insufficient_credits(self, override_free_user):
        """Test: Insufficient credits returns 402."""
        # Arrange
        mock_service = MagicMock()
        mock_service.generate_story = AsyncMock(
            side_effect=InsufficientCreditsException(required=1, available=0)
        )

        app.dependency_overrides[get_story_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/generate/story/story",
            json={"topic": "Test"},
        )

        # Assert
        assert response.status_code == 402
        data = response.json()
        error_msg = data.get("detail", "") or data.get("message", "")
        assert "Insufficient" in error_msg

        app.dependency_overrides.clear()

    def test_gen_story_generation_failure(self, override_free_user):
        """Test: Generation failure returns 500."""
        # Arrange
        mock_service = MagicMock()
        mock_service.generate_story = AsyncMock(
            side_effect=StoryGenerationException("AI Error")
        )

        app.dependency_overrides[get_story_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/generate/story/story",
            json={"topic": "Test"},
        )

        # Assert
        assert response.status_code == 500
        data = response.json()
        error_msg = data.get("detail", "") or data.get("message", "")
        assert "refunded" in error_msg.lower()

        app.dependency_overrides.clear()

    def test_gen_story_unauthorized(self):
        """Test: Unauthenticated request returns 401."""
        # Act
        response = client.post(
            "/api/v2/user/generate/story/story",
            json={"topic": "Test"},
        )

        # Assert
        assert response.status_code == 401


# ==========================================
# POST /api/v2/user/generate/inspiration Tests
# ==========================================

class TestGenInspiration:
    """Tests for POST /api/v2/user/generate/inspiration endpoint."""

    def test_gen_inspiration_success(self, override_free_user):
        """Test: Successful inspiration generation."""
        # Arrange
        mock_service = MagicMock()
        mock_service.generate_inspiration = AsyncMock(return_value={
            "suggestions": [
                {"character": "A curious cat", "action": "exploring", "setting": "garden", "style": "watercolor"}
            ],
            "category": "all",
        })

        app.dependency_overrides[get_inspiration_service] = lambda: mock_service

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

        mock_service.generate_inspiration.assert_called_once()

        app.dependency_overrides.clear()

    def test_gen_inspiration_fallback(self, override_free_user):
        """Test: Returns fallback on error (handled by Service)."""
        # Arrange
        mock_service = MagicMock()
        mock_service.generate_inspiration = AsyncMock(return_value={
            "suggestions": [{"character": "Robot", "action": "dancing"}],
            "category": "all",
            "fallback": True,
        })

        app.dependency_overrides[get_inspiration_service] = lambda: mock_service

        # Act
        response = client.post(
            "/api/v2/user/generate/story/inspiration",
            json={},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert data.get("fallback") == True

        app.dependency_overrides.clear()

    def test_gen_inspiration_unauthorized(self):
        """Test: Unauthenticated request returns 401."""
        # Act
        response = client.post(
            "/api/v2/user/generate/story/inspiration",
            json={},
        )

        # Assert
        assert response.status_code == 401

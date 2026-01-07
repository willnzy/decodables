"""
Tests for api/user/generation.py

Endpoints:
- POST /api/v2/user/generate/images
- POST /api/v2/user/generate/images/async
- POST /api/v2/user/generate/story
- POST /api/v2/user/generate/inspiration
- POST /api/v2/user/generate/pdf

Created: 2026-01-08 (Stage 3: Week 1 Day 2)
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from io import BytesIO

from app import app

client = TestClient(app)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def auth_headers():
    """Valid auth headers."""
    return {"Authorization": "Bearer test_token_user_123"}


@pytest.fixture
def mock_free_user():
    """Mock free tier user."""
    return {
        "id": "user_free",
        "email": "free@example.com",
        "tier": "free",
    }


@pytest.fixture
def mock_pro_user():
    """Mock pro tier user."""
    return {
        "id": "user_pro",
        "email": "pro@example.com",
        "tier": "pro",
    }


@pytest.fixture
def mock_credit_deduct_result():
    """Mock credit_deduct result."""
    return {
        "total": 540,
        "balance_monthly": 500,
        "balance_permanent": 40,
    }


# ==========================================
# POST /api/v2/user/generate/images
# ==========================================

class TestGenerateImages:
    """Tests for POST /api/v2/user/generate/images endpoint."""

    @patch('dependencies.get_current_user')
    @patch('services.db_service.credit_deduct')
    @patch('services.ai.image_generator.generate_8_images')
    @patch('services.db_service.save_asset')
    @patch('services.analytics_service.track_ai_generation')
    @patch('timezone_utils.get_request_timezone')
    def test_generate_images_success(
        self,
        mock_get_tz,
        mock_track,
        mock_save_asset,
        mock_generate,
        mock_credit_deduct,
        mock_get_user,
        mock_free_user,
        mock_credit_deduct_result,
        auth_headers,
    ):
        """
        Test: Generate images successfully (free user)

        Given: Free user with sufficient credits
        When: POST to generate 1 image
        Then: Returns 200 with image URLs
        """
        # Arrange
        mock_get_user.return_value = mock_free_user
        mock_credit_deduct.return_value = mock_credit_deduct_result
        mock_generate.return_value = (["http://example.com/image1.jpg"], "task_123")
        mock_get_tz.return_value = "UTC"

        # Act
        response = client.post(
            "/api/v2/user/generate/images",
            json={
                "prompts": ["A cute robot"],
                "num_images": 1,
                "image_size": "landscape_4_3",
                "generation_mode": "guided",
                "creativity_level": 0.3,
            },
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["image_urls"]) == 1
        assert data["image_urls"][0] == "http://example.com/image1.jpg"
        assert data["model_used"] == "flux-schnell"  # Free user gets standard model
        assert data["balance"] == 540
        assert data["generation_mode"] == "guided"
        assert data["used_reference"] is False

        # Verify credit deduction (5 credits for non-reference image)
        mock_credit_deduct.assert_called_once()
        call_args = mock_credit_deduct.call_args[0]
        assert call_args[0] == "user_free"
        assert call_args[1] == 5  # 1 prompt * 5 credits * 1 image

    @patch('dependencies.get_current_user')
    @patch('services.db_service.credit_deduct')
    @patch('services.ai.image_generator.generate_8_images')
    @patch('services.db_service.save_asset')
    @patch('services.analytics_service.track_ai_generation')
    @patch('timezone_utils.get_request_timezone')
    def test_generate_images_pro_user(
        self,
        mock_get_tz,
        mock_track,
        mock_save_asset,
        mock_generate,
        mock_credit_deduct,
        mock_get_user,
        mock_pro_user,
        mock_credit_deduct_result,
        auth_headers,
    ):
        """
        Test: Pro user gets high-quality model

        Given: Pro user
        When: POST to generate images
        Then: Uses flux-dev model
        """
        # Arrange
        mock_get_user.return_value = mock_pro_user
        mock_credit_deduct.return_value = mock_credit_deduct_result
        mock_generate.return_value = (["http://example.com/image_pro.jpg"], "task_456")
        mock_get_tz.return_value = "UTC"

        # Act
        response = client.post(
            "/api/v2/user/generate/images",
            json={"prompts": ["High quality art"], "num_images": 1},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["model_used"] == "flux-dev"  # Pro user gets premium model

    @patch('dependencies.get_current_user')
    @patch('services.db_service.credit_deduct')
    def test_generate_images_insufficient_credits(
        self,
        mock_credit_deduct,
        mock_get_user,
        mock_free_user,
        auth_headers,
    ):
        """
        Test: Insufficient credits (402)

        Given: User has insufficient credits
        When: POST to generate images
        Then: Returns 402 Payment Required
        """
        # Arrange
        mock_get_user.return_value = mock_free_user
        mock_credit_deduct.side_effect = Exception("INSUFFICIENT credits")

        # Act
        response = client.post(
            "/api/v2/user/generate/images",
            json={"prompts": ["Test"], "num_images": 1},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 402
        data = response.json()
        assert "Insufficient" in data["detail"]

    @patch('dependencies.get_current_user')
    def test_generate_images_safety_violation(
        self,
        mock_get_user,
        mock_free_user,
        auth_headers,
    ):
        """
        Test: Safety violation (400)

        Given: Prompt contains blacklisted words
        When: POST with NSFW content
        Then: Returns 400 Bad Request
        """
        # Arrange
        mock_get_user.return_value = mock_free_user

        # Act
        response = client.post(
            "/api/v2/user/generate/images",
            json={"prompts": ["nsfw content"], "num_images": 1},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "Safety" in data["detail"]

    @patch('dependencies.get_current_user')
    @patch('services.db_service.credit_deduct')
    @patch('services.ai.image_generator.generate_8_images')
    @patch('services.db_service.save_asset')
    @patch('services.analytics_service.track_ai_generation')
    @patch('timezone_utils.get_request_timezone')
    def test_generate_images_with_reference(
        self,
        mock_get_tz,
        mock_track,
        mock_save_asset,
        mock_generate,
        mock_credit_deduct,
        mock_get_user,
        mock_free_user,
        mock_credit_deduct_result,
        auth_headers,
    ):
        """
        Test: Generate with reference image (higher cost)

        Given: Request includes reference image
        When: POST with reference_image URL
        Then: Charges 7 credits instead of 5
        """
        # Arrange
        mock_get_user.return_value = mock_free_user
        mock_credit_deduct.return_value = mock_credit_deduct_result
        mock_generate.return_value = (["http://example.com/ref_image.jpg"], "task_789")
        mock_get_tz.return_value = "UTC"

        # Act
        response = client.post(
            "/api/v2/user/generate/images",
            json={
                "prompts": ["Style transfer"],
                "num_images": 1,
                "reference_image": "http://example.com/ref.jpg",
                "reference_strength": 0.8,
            },
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["used_reference"] is True

        # Verify higher credit cost for reference image
        call_args = mock_credit_deduct.call_args[0]
        assert call_args[1] == 7  # 1 prompt * 7 credits * 1 image


# ==========================================
# POST /api/v2/user/generate/images/async
# ==========================================

class TestGenerateImagesAsync:
    """Tests for POST /api/v2/user/generate/images/async endpoint."""

    @patch('dependencies.get_current_user')
    @patch('services.db_service.credit_deduct')
    @patch('services.task_queue.task_queue.enqueue_image_generation')
    def test_generate_images_async_success(
        self,
        mock_enqueue,
        mock_credit_deduct,
        mock_get_user,
        mock_free_user,
        mock_credit_deduct_result,
        auth_headers,
    ):
        """
        Test: Async image generation queued successfully

        Given: Free user with sufficient credits
        When: POST to async endpoint
        Then: Returns task_id with queued status
        """
        # Arrange
        mock_get_user.return_value = mock_free_user
        mock_credit_deduct.return_value = mock_credit_deduct_result
        mock_enqueue.return_value = "gen_1234567890_abc12345"

        # Act
        response = client.post(
            "/api/v2/user/generate/images/async",
            json={"prompts": ["Async test"], "num_images": 1},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert "task_id" in data
        assert data["credits_charged"] == 5
        assert data["balance"] == 540
        assert data["priority"] == "low"  # Free user gets low priority
        assert data["websocket_url"].startswith("/ws/task/")
        assert data["poll_url"].startswith("/api/v2/tasks/")

    @patch('dependencies.get_current_user')
    @patch('services.db_service.credit_deduct')
    @patch('services.task_queue.task_queue.enqueue_image_generation')
    def test_generate_images_async_pro_priority(
        self,
        mock_enqueue,
        mock_credit_deduct,
        mock_get_user,
        mock_pro_user,
        mock_credit_deduct_result,
        auth_headers,
    ):
        """
        Test: Pro user gets high priority

        Given: Pro user
        When: POST async generation
        Then: Gets "high" priority
        """
        # Arrange
        mock_get_user.return_value = mock_pro_user
        mock_credit_deduct.return_value = mock_credit_deduct_result
        mock_enqueue.return_value = "gen_task_pro"

        # Act
        response = client.post(
            "/api/v2/user/generate/images/async",
            json={"prompts": ["Pro async"], "num_images": 1},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "high"

    @patch('dependencies.get_current_user')
    @patch('services.db_service.credit_deduct')
    @patch('services.task_queue.task_queue.enqueue_image_generation')
    @patch('services.db_service.add_credits')
    def test_generate_images_async_queue_failure(
        self,
        mock_add_credits,
        mock_enqueue,
        mock_credit_deduct,
        mock_get_user,
        mock_free_user,
        mock_credit_deduct_result,
        auth_headers,
    ):
        """
        Test: Task queue failure triggers refund

        Given: Task queue is unavailable
        When: Enqueue fails
        Then: Returns 503 and refunds credits
        """
        # Arrange
        mock_get_user.return_value = mock_free_user
        mock_credit_deduct.return_value = mock_credit_deduct_result
        mock_enqueue.return_value = None  # Enqueue failed

        # Act
        response = client.post(
            "/api/v2/user/generate/images/async",
            json={"prompts": ["Queue test"], "num_images": 1},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 503
        data = response.json()
        assert "unavailable" in data["detail"].lower()
        assert "refunded" in data["detail"].lower()

        # Verify refund was attempted
        mock_add_credits.assert_called_once()


# ==========================================
# POST /api/v2/user/generate/story
# ==========================================

class TestGenerateStory:
    """Tests for POST /api/v2/user/generate/story endpoint."""

    @patch('dependencies.get_current_user')
    @patch('services.ai.story_generator.generate_story_json')
    def test_generate_story_success(
        self,
        mock_generate_story,
        mock_get_user,
        mock_free_user,
        auth_headers,
    ):
        """
        Test: Generate story successfully

        Given: User requests story
        When: POST with topic
        Then: Returns 8-page story JSON
        """
        # Arrange
        mock_get_user.return_value = mock_free_user
        mock_story = {
            "pages": [{"text": "Once upon a time..."} for _ in range(8)],
            "topic": "Friendly Robot",
        }
        mock_generate_story.return_value = mock_story

        # Act
        response = client.post(
            "/api/v2/user/generate/story",
            json={"topic": "Friendly Robot"},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "pages" in data
        assert len(data["pages"]) == 8

    @patch('dependencies.get_current_user')
    @patch('services.ai.story_generator.generate_story_json')
    def test_generate_story_failure(
        self,
        mock_generate_story,
        mock_get_user,
        mock_free_user,
        auth_headers,
    ):
        """
        Test: Story generation failure (500)

        Given: Story generator throws error
        When: POST story request
        Then: Returns 500 Internal Server Error
        """
        # Arrange
        mock_get_user.return_value = mock_free_user
        mock_generate_story.side_effect = Exception("OpenAI API error")

        # Act
        response = client.post(
            "/api/v2/user/generate/story",
            json={"topic": "Test topic"},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 500


# ==========================================
# POST /api/v2/user/generate/inspiration
# ==========================================

class TestGenerateInspiration:
    """Tests for POST /api/v2/user/generate/inspiration endpoint."""

    @patch('dependencies.get_current_user')
    @patch('services.ai.story_generator.client')
    def test_generate_inspiration_success(
        self,
        mock_openai_client,
        mock_get_user,
        mock_free_user,
        auth_headers,
    ):
        """
        Test: Generate inspiration successfully

        Given: User requests inspiration
        When: POST with category
        Then: Returns 3 suggestions
        """
        # Arrange
        mock_get_user.return_value = mock_free_user
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"suggestions": [{"character": "Robot"}, {"character": "Mouse"}, {"character": "Owl"}]}'
        mock_openai_client.chat.completions.create.return_value = mock_response

        # Act
        response = client.post(
            "/api/v2/user/generate/inspiration",
            json={"category": "character"},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert len(data["suggestions"]) == 3
        assert data["category"] == "character"
        assert data["fallback"] is False

    @patch('dependencies.get_current_user')
    @patch('services.ai.story_generator.client')
    def test_generate_inspiration_fallback(
        self,
        mock_openai_client,
        mock_get_user,
        mock_free_user,
        auth_headers,
    ):
        """
        Test: Inspiration fallback on error

        Given: OpenAI API fails
        When: POST inspiration request
        Then: Returns hardcoded fallback suggestions
        """
        # Arrange
        mock_get_user.return_value = mock_free_user
        mock_openai_client.chat.completions.create.side_effect = Exception("API error")

        # Act
        response = client.post(
            "/api/v2/user/generate/inspiration",
            json={"category": "all"},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert len(data["suggestions"]) == 3
        assert data["fallback"] is True


# ==========================================
# POST /api/v2/user/generate/pdf
# ==========================================

class TestGeneratePdf:
    """Tests for POST /api/v2/user/generate/pdf endpoint."""

    @patch('dependencies.get_current_user')
    @patch('services.db_service.get_project_detail')
    @patch('services.db_service.update_project_hash')
    @patch('services.ai.zine_generator.create_foldable_book')
    @patch('services.db_service.log_activity')
    def test_generate_pdf_success(
        self,
        mock_log_activity,
        mock_create_book,
        mock_update_hash,
        mock_get_project,
        mock_get_user,
        mock_free_user,
        auth_headers,
    ):
        """
        Test: Generate PDF successfully

        Given: User has project with images and text
        When: POST to generate PDF
        Then: Returns PDF file
        """
        # Arrange
        mock_get_user.return_value = mock_free_user
        mock_get_project.return_value = {
            "id": "proj_123",
            "last_downloaded_hash": "old_hash",
        }

        def write_pdf(image_urls, texts, buf):
            buf.write(b"PDF_CONTENT")

        mock_create_book.side_effect = write_pdf

        # Act
        response = client.post(
            "/api/v2/user/generate/pdf",
            json={
                "project_id": "proj_123",
                "image_urls": ["url1", "url2"],
                "texts": ["Page 1", "Page 2"],
                "current_hash": "new_hash",
            },
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]

        # Verify hash was updated
        mock_update_hash.assert_called_once_with("proj_123", "new_hash")

        # Verify activity logged
        mock_log_activity.assert_called_once()

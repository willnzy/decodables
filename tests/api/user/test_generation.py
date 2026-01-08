"""
Test api/user/generation.py - AI Generation API

Endpoints:
- POST /api/v2/user/generate/images - Sync image generation
- POST /api/v2/user/generate/images/async - Async image generation
- POST /api/v2/user/generate/story - Story generation
- POST /api/v2/user/generate/inspiration - AI inspiration
- POST /api/v2/user/generate/pdf - PDF generation

Created: 2026-01-08
Updated: 2026-01-08 (Complete rewrite with proper mocking)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from io import BytesIO

# Rate limiter bypass BEFORE app import
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

from app import app
from dependencies import get_current_user
from core.database import get_database_client

client = TestClient(app)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_user_free():
    """Mock free tier user."""
    return {
        "id": "user_free_123",
        "email": "free@example.com",
        "tier": "free",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def mock_user_pro():
    """Mock pro tier user."""
    return {
        "id": "user_pro_456",
        "email": "pro@example.com",
        "tier": "pro",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def override_get_current_user_free(mock_user_free):
    """Override get_current_user with free user."""
    async def _get_current_user():
        return mock_user_free
    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def override_get_current_user_pro(mock_user_pro):
    """Override get_current_user with pro user."""
    async def _get_current_user():
        return mock_user_pro
    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()


# ==========================================
# Tests - POST /api/v2/user/generate/images
# ==========================================

class TestGenerateImages:
    """Test POST /api/v2/user/generate/images endpoint."""

    @patch('api.user.generation.track_ai_generation')
    @patch('api.user.generation.get_request_timezone')
    @patch('api.user.generation.SupabaseAssetRepository')
    @patch('api.user.generation.generate_8_images')
    @patch('api.user.generation.SupabaseCreditRepository')
    def test_generate_images_success(
        self,
        mock_credit_repo_class,
        mock_generate,
        mock_asset_repo_class,
        mock_get_tz,
        mock_track,
        override_get_current_user_free,
    ):
        """Test successful image generation (free user)."""
        # Mock credit repository
        mock_credit_repo = AsyncMock()
        mock_credit_repo.deduct_credits.return_value = {
            "success": True,
            "total": 540,
            "balance_monthly": 500,
            "balance_permanent": 40,
        }
        mock_credit_repo_class.return_value = mock_credit_repo

        # Mock image generation
        mock_generate.return_value = (["http://example.com/image1.jpg"], "task_123")

        # Mock asset repository
        mock_asset_repo = AsyncMock()
        mock_asset_repo_class.return_value = mock_asset_repo

        # Mock timezone
        mock_get_tz.return_value = "UTC"

        response = client.post(
            "/api/v2/user/generate/images",
            json={
                "prompts": ["A cute robot"],
                "num_images": 1,
                "image_size": "landscape_4_3",
                "generation_mode": "guided",
                "creativity_level": 0.3,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["image_urls"]) == 1
        assert data["image_urls"][0] == "http://example.com/image1.jpg"
        assert data["model_used"] == "flux-schnell"  # Free user gets standard model
        assert data["balance"] == 540
        assert data["used_reference"] is False

    @patch('api.user.generation.track_ai_generation')
    @patch('api.user.generation.get_request_timezone')
    @patch('api.user.generation.SupabaseAssetRepository')
    @patch('api.user.generation.generate_8_images')
    @patch('api.user.generation.SupabaseCreditRepository')
    def test_generate_images_pro_user(
        self,
        mock_credit_repo_class,
        mock_generate,
        mock_asset_repo_class,
        mock_get_tz,
        mock_track,
        override_get_current_user_pro,
    ):
        """Test pro user gets high-quality model."""
        mock_credit_repo = AsyncMock()
        mock_credit_repo.deduct_credits.return_value = {
            "success": True,
            "total": 995,
            "balance_monthly": 1000,
            "balance_permanent": -5,
        }
        mock_credit_repo_class.return_value = mock_credit_repo

        mock_generate.return_value = (["http://example.com/image_pro.jpg"], "task_456")
        mock_asset_repo = AsyncMock()
        mock_asset_repo_class.return_value = mock_asset_repo
        mock_get_tz.return_value = "UTC"

        response = client.post(
            "/api/v2/user/generate/images",
            json={"prompts": ["High quality art"], "num_images": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["model_used"] == "flux-dev"  # Pro user gets premium model

    @patch('api.user.generation.SupabaseCreditRepository')
    def test_generate_images_insufficient_credits(
        self,
        mock_credit_repo_class,
        override_get_current_user_free,
    ):
        """Test insufficient credits returns 402."""
        mock_credit_repo = AsyncMock()
        mock_credit_repo.deduct_credits.return_value = {
            "success": False,
            "error": "INSUFFICIENT credits",
        }
        mock_credit_repo_class.return_value = mock_credit_repo

        response = client.post(
            "/api/v2/user/generate/images",
            json={"prompts": ["Test"], "num_images": 1},
        )

        assert response.status_code == 402
        assert "Insufficient" in response.json()["message"]

    def test_generate_images_requires_auth(self):
        """Test image generation requires authentication."""
        response = client.post(
            "/api/v2/user/generate/images",
            json={"prompts": ["Test"], "num_images": 1},
        )
        assert response.status_code == 401


# ==========================================
# Tests - POST /api/v2/user/generate/images/async
# ==========================================

class TestGenerateImagesAsync:
    """Test POST /api/v2/user/generate/images/async endpoint."""

    @patch('api.user.generation.task_queue')
    @patch('api.user.generation.SupabaseCreditRepository')
    def test_generate_images_async_success(
        self,
        mock_credit_repo_class,
        mock_task_queue,
        override_get_current_user_free,
    ):
        """Test async image generation queued successfully."""
        mock_credit_repo = AsyncMock()
        mock_credit_repo.deduct_credits.return_value = {
            "success": True,
            "total": 540,
            "balance_monthly": 500,
            "balance_permanent": 40,
        }
        mock_credit_repo_class.return_value = mock_credit_repo

        mock_task_queue.enqueue_image_generation.return_value = "gen_1234567890_abc12345"

        response = client.post(
            "/api/v2/user/generate/images/async",
            json={"prompts": ["Async test"], "num_images": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert "task_id" in data
        assert data["credits_charged"] == 5
        assert data["balance"] == 540
        assert data["priority"] == "low"  # Free user gets low priority

    @patch('api.user.generation.task_queue')
    @patch('api.user.generation.SupabaseCreditRepository')
    def test_generate_images_async_pro_priority(
        self,
        mock_credit_repo_class,
        mock_task_queue,
        override_get_current_user_pro,
    ):
        """Test pro user gets high priority."""
        mock_credit_repo = AsyncMock()
        mock_credit_repo.deduct_credits.return_value = {
            "success": True,
            "total": 995,
            "balance_monthly": 1000,
            "balance_permanent": -5,
        }
        mock_credit_repo_class.return_value = mock_credit_repo

        mock_task_queue.enqueue_image_generation.return_value = "gen_task_pro"

        response = client.post(
            "/api/v2/user/generate/images/async",
            json={"prompts": ["Pro async"], "num_images": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "high"

    @patch('api.user.generation.task_queue')
    @patch('api.user.generation.SupabaseCreditRepository')
    def test_generate_images_async_queue_failure(
        self,
        mock_credit_repo_class,
        mock_task_queue,
        override_get_current_user_free,
    ):
        """Test task queue failure triggers refund."""
        mock_credit_repo = AsyncMock()
        mock_credit_repo.deduct_credits.return_value = {
            "success": True,
            "total": 540,
            "balance_monthly": 500,
            "balance_permanent": 40,
        }
        mock_credit_repo.add_credits = AsyncMock()
        mock_credit_repo_class.return_value = mock_credit_repo

        mock_task_queue.enqueue_image_generation.return_value = None  # Failed

        response = client.post(
            "/api/v2/user/generate/images/async",
            json={"prompts": ["Queue test"], "num_images": 1},
        )

        assert response.status_code == 503
        assert "unavailable" in response.json()["message"].lower()


# ==========================================
# Tests - POST /api/v2/user/generate/story
# ==========================================

class TestGenerateStory:
    """Test POST /api/v2/user/generate/story endpoint."""

    @patch('api.user.generation.generate_story_json')
    def test_generate_story_success(
        self,
        mock_generate_story,
        override_get_current_user_free,
    ):
        """Test successful story generation."""
        mock_story = {
            "pages": [{"text": f"Page {i}"} for i in range(1, 9)],
            "topic": "Friendly Robot",
        }
        mock_generate_story.return_value = mock_story

        response = client.post(
            "/api/v2/user/generate/story",
            json={"topic": "Friendly Robot"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "pages" in data
        assert len(data["pages"]) == 8

    @patch('api.user.generation.generate_story_json')
    def test_generate_story_failure(
        self,
        mock_generate_story,
        override_get_current_user_free,
    ):
        """Test story generation failure returns 500."""
        mock_generate_story.side_effect = Exception("OpenAI API error")

        response = client.post(
            "/api/v2/user/generate/story",
            json={"topic": "Test topic"},
        )

        assert response.status_code == 500


# ==========================================
# Tests - POST /api/v2/user/generate/inspiration
# ==========================================

class TestGenerateInspiration:
    """Test POST /api/v2/user/generate/inspiration endpoint."""

    @patch('api.user.generation.openai_client')
    def test_generate_inspiration_success(
        self,
        mock_openai_client,
        override_get_current_user_free,
    ):
        """Test successful inspiration generation."""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"suggestions": [{"character": "Robot"}, {"character": "Mouse"}, {"character": "Owl"}]}'
        mock_openai_client.chat.completions.create.return_value = mock_response

        response = client.post(
            "/api/v2/user/generate/inspiration",
            json={"category": "character"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert len(data["suggestions"]) == 3
        assert data["fallback"] is False

    @patch('api.user.generation.openai_client')
    def test_generate_inspiration_fallback(
        self,
        mock_openai_client,
        override_get_current_user_free,
    ):
        """Test inspiration fallback on error."""
        mock_openai_client.chat.completions.create.side_effect = Exception("API error")

        response = client.post(
            "/api/v2/user/generate/inspiration",
            json={"category": "all"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert data["fallback"] is True


# ==========================================
# Tests - POST /api/v2/user/generate/pdf
# ==========================================

class TestGeneratePdf:
    """Test POST /api/v2/user/generate/pdf endpoint."""

    @patch('api.user.generation.SupabaseProjectRepository')
    @patch('api.user.generation.create_foldable_book')
    def test_generate_pdf_success(
        self,
        mock_create_book,
        mock_project_repo_class,
        override_get_current_user_free,
    ):
        """Test successful PDF generation."""
        mock_project_repo = AsyncMock()
        mock_project_repo.get_project_detail.return_value = {
            "id": "proj_123",
            "last_downloaded_hash": "old_hash",
        }
        mock_project_repo.update_project_hash = AsyncMock()
        mock_project_repo_class.return_value = mock_project_repo

        def write_pdf(image_urls, texts, buf):
            buf.write(b"PDF_CONTENT")

        mock_create_book.side_effect = write_pdf

        response = client.post(
            "/api/v2/user/generate/pdf",
            json={
                "project_id": "proj_123",
                "image_urls": ["url1", "url2"],
                "texts": ["Page 1", "Page 2"],
                "current_hash": "new_hash",
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]

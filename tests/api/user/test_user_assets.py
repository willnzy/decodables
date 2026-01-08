"""
Test api/user/user_assets.py - User Assets API

Endpoints:
- GET /api/v2/user/assets - Get user assets
- POST /api/v2/user/assets - Upload asset
- DELETE /api/v2/user/assets/{asset_id} - Delete asset
- POST /api/v2/user/assets/from-url - Add asset from URL
- GET /api/v2/user/assets/check-url - Check URL validity
- POST /api/v2/user/assets/{asset_id}/increment-usage - Increment usage
- GET /api/v2/user/assets/dashboard - Asset dashboard
- GET /api/v2/user/assets/seller-stats - Seller stats
- GET /api/v2/user/assets/deleted - Get deleted assets
- POST /api/v2/user/assets/{asset_id}/restore - Restore asset

Created: 2026-01-09
Updated: 2026-01-09 (Complete test suite with security validations)
"""

import pytest
import io
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

# Rate limiter bypass BEFORE app import
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

from app import app
from dependencies import get_current_user

client = TestClient(app)


# ==========================================
# Test Constants
# ==========================================

VALID_ASSET_ID = "12345678-1234-1234-1234-123456789abc"
VALID_PROJECT_ID = "87654321-4321-4321-4321-cba987654321"
NONEXISTENT_ASSET_ID = "00000000-0000-0000-0000-000000000000"
INVALID_UUID = "not-a-valid-uuid"


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_user_pro():
    """Mock Pro user."""
    return {
        "id": "user_pro_123",
        "email": "pro@example.com",
        "tier": "pro",
    }


@pytest.fixture
def mock_user_free():
    """Mock Free user."""
    return {
        "id": "user_free_456",
        "email": "free@example.com",
        "tier": "free",
    }


@pytest.fixture
def override_get_current_user_pro(mock_user_pro):
    """Override authentication with Pro user."""
    async def _get_current_user():
        return mock_user_pro
    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def override_get_current_user_free(mock_user_free):
    """Override authentication with Free user."""
    async def _get_current_user():
        return mock_user_free
    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_image_file():
    """Create a mock image file."""
    # 1x1 PNG image
    png_content = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return ("test.png", io.BytesIO(png_content), "image/png")


# ==========================================
# Tests - GET /api/v2/user/assets
# ==========================================

class TestMyAssets:
    """Test GET /api/v2/user/assets endpoint."""

    @patch('api.user.user_assets.SupabaseAssetRepository')
    def test_get_assets_success(self, mock_repo_class, override_get_current_user_pro):
        """Test successful asset retrieval."""
        mock_repo = AsyncMock()
        mock_repo.get_assets.return_value = [
            {"id": VALID_ASSET_ID, "url": "https://example.com/image.png"}
        ]
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v2/user/assets")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == VALID_ASSET_ID

    @patch('api.user.user_assets.SupabaseAssetRepository')
    def test_get_assets_with_valid_project_id(self, mock_repo_class, override_get_current_user_pro):
        """Test asset retrieval with valid project_id."""
        mock_repo = AsyncMock()
        mock_repo.get_assets.return_value = []
        mock_repo_class.return_value = mock_repo

        response = client.get(f"/api/v2/user/assets?project_id={VALID_PROJECT_ID}")

        assert response.status_code == 200
        mock_repo.get_assets.assert_called_once_with("user_pro_123", VALID_PROJECT_ID)

    def test_get_assets_invalid_project_id(self, override_get_current_user_pro):
        """Test asset retrieval rejects invalid project_id format (UA-MEDIUM-2)."""
        response = client.get(f"/api/v2/user/assets?project_id={INVALID_UUID}")

        assert response.status_code == 400
        assert "Invalid project ID format" in response.json()["message"]

    def test_get_assets_scope_all_requires_pro(self, override_get_current_user_free):
        """Test scope=all requires Pro tier."""
        response = client.get("/api/v2/user/assets?scope=all")

        assert response.status_code == 403
        assert "Pro required" in response.json()["message"]


# ==========================================
# Tests - POST /api/v2/user/assets (Upload)
# ==========================================

class TestUploadAsset:
    """Test POST /api/v2/user/assets endpoint."""

    @patch('shared.ai.image_generator.supabase')
    @patch('api.user.user_assets.SupabaseAssetRepository')
    def test_upload_asset_success(
        self, mock_repo_class, mock_storage, override_get_current_user_pro, mock_image_file
    ):
        """Test successful asset upload."""
        mock_repo = AsyncMock()
        mock_repo.save_asset.return_value = {"id": VALID_ASSET_ID}
        mock_repo_class.return_value = mock_repo

        mock_storage.storage.from_.return_value.upload.return_value = None
        mock_storage.storage.from_.return_value.get_public_url.return_value = "https://cdn.example.com/image.png"

        filename, content, content_type = mock_image_file
        response = client.post(
            "/api/v2/user/assets",
            files={"file": (filename, content, content_type)},
        )

        assert response.status_code == 200
        data = response.json()
        assert "url" in data

    def test_upload_asset_free_user_forbidden(self, override_get_current_user_free, mock_image_file):
        """Test upload requires Pro tier."""
        filename, content, content_type = mock_image_file
        response = client.post(
            "/api/v2/user/assets",
            files={"file": (filename, content, content_type)},
        )

        assert response.status_code == 403
        assert "Pro plan" in response.json()["message"]

    def test_upload_asset_invalid_file_type(self, override_get_current_user_pro):
        """Test upload rejects unsupported file types."""
        response = client.post(
            "/api/v2/user/assets",
            files={"file": ("test.txt", io.BytesIO(b"text"), "text/plain")},
        )

        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["message"]

    def test_upload_asset_file_too_large(self, override_get_current_user_pro):
        """Test upload rejects files over 5MB."""
        large_content = b"x" * (6 * 1024 * 1024)
        response = client.post(
            "/api/v2/user/assets",
            files={"file": ("large.png", io.BytesIO(large_content), "image/png")},
        )

        assert response.status_code == 400
        assert "too large" in response.json()["message"].lower()

    def test_upload_asset_invalid_project_id(self, override_get_current_user_pro, mock_image_file):
        """Test upload rejects invalid project_id format (UA-MEDIUM-2)."""
        filename, content, content_type = mock_image_file
        response = client.post(
            "/api/v2/user/assets",
            files={"file": (filename, content, content_type)},
            data={"project_id": INVALID_UUID},
        )

        assert response.status_code == 400
        assert "Invalid project ID format" in response.json()["message"]


# ==========================================
# Tests - DELETE /api/v2/user/assets/{asset_id}
# ==========================================

class TestDeleteAsset:
    """Test DELETE /api/v2/user/assets/{asset_id} endpoint."""

    @patch('api.user.user_assets.SupabaseAssetRepository')
    def test_delete_asset_success(self, mock_repo_class, override_get_current_user_pro):
        """Test successful soft delete."""
        mock_repo = AsyncMock()
        mock_repo.soft_delete_asset.return_value = True
        mock_repo_class.return_value = mock_repo

        response = client.delete(f"/api/v2/user/assets/{VALID_ASSET_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "trash" in data["action"]

    @patch('api.user.user_assets.SupabaseAssetRepository')
    def test_delete_asset_permanent(self, mock_repo_class, override_get_current_user_pro):
        """Test permanent delete."""
        mock_repo = AsyncMock()
        mock_repo.permanently_hide_asset.return_value = True
        mock_repo_class.return_value = mock_repo

        response = client.delete(f"/api/v2/user/assets/{VALID_ASSET_ID}?permanent=true")

        assert response.status_code == 200
        data = response.json()
        assert "permanently deleted" in data["action"]

    def test_delete_asset_invalid_id(self, override_get_current_user_pro):
        """Test delete rejects invalid asset_id format (UA-MEDIUM-1)."""
        response = client.delete(f"/api/v2/user/assets/{INVALID_UUID}")

        assert response.status_code == 400
        assert "Invalid asset ID format" in response.json()["message"]

    @patch('api.user.user_assets.SupabaseAssetRepository')
    def test_delete_asset_not_found(self, mock_repo_class, override_get_current_user_pro):
        """Test delete for non-existent asset."""
        mock_repo = AsyncMock()
        mock_repo.soft_delete_asset.return_value = False
        mock_repo_class.return_value = mock_repo

        response = client.delete(f"/api/v2/user/assets/{NONEXISTENT_ASSET_ID}")

        assert response.status_code == 404


# ==========================================
# Tests - POST /api/v2/user/assets/from-url
# ==========================================

class TestAssetFromUrl:
    """Test POST /api/v2/user/assets/from-url endpoint."""

    @patch('api.user.user_assets.is_private_ip')
    @patch('httpx.Client')
    @patch('api.user.user_assets.SupabaseAssetRepository')
    def test_add_from_url_success(
        self, mock_repo_class, mock_httpx, mock_private_ip, override_get_current_user_pro
    ):
        """Test successful asset from URL."""
        mock_private_ip.return_value = False

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'image/png'}
        mock_httpx.return_value.__enter__.return_value.head.return_value = mock_response

        mock_repo = AsyncMock()
        mock_repo.save_asset.return_value = {"id": VALID_ASSET_ID}
        mock_repo_class.return_value = mock_repo

        response = client.post(
            "/api/v2/user/assets/from-url",
            json={"url": "https://example.com/image.png"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_add_from_url_ssrf_blocked(self, override_get_current_user_pro):
        """Test SSRF protection blocks internal URLs (UA-HIGH-1)."""
        # Test localhost
        response = client.post(
            "/api/v2/user/assets/from-url",
            json={"url": "http://localhost/image.png"},
        )

        assert response.status_code == 400
        assert "internal network" in response.json()["message"]

    def test_add_from_url_private_ip_blocked(self, override_get_current_user_pro):
        """Test SSRF protection blocks private IPs (UA-HIGH-1)."""
        response = client.post(
            "/api/v2/user/assets/from-url",
            json={"url": "http://192.168.1.1/image.png"},
        )

        assert response.status_code == 400
        assert "internal network" in response.json()["message"]

    def test_add_from_url_invalid_project_id(self, override_get_current_user_pro):
        """Test from-url rejects invalid project_id format."""
        response = client.post(
            "/api/v2/user/assets/from-url",
            json={"url": "https://example.com/image.png", "project_id": INVALID_UUID},
        )

        assert response.status_code == 422  # Pydantic validation error

    def test_add_from_url_too_long(self, override_get_current_user_pro):
        """Test URL length limit (UA-LOW-2)."""
        long_url = "https://example.com/" + "a" * 3000
        response = client.post(
            "/api/v2/user/assets/from-url",
            json={"url": long_url},
        )

        assert response.status_code == 422  # Pydantic max_length validation


# ==========================================
# Tests - GET /api/v2/user/assets/check-url
# ==========================================

class TestCheckUrl:
    """Test GET /api/v2/user/assets/check-url endpoint."""

    @patch('api.user.user_assets.is_private_ip')
    @patch('httpx.Client')
    def test_check_url_valid(self, mock_httpx, mock_private_ip, override_get_current_user_pro):
        """Test valid URL check."""
        mock_private_ip.return_value = False

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'image/png'}
        mock_httpx.return_value.__enter__.return_value.head.return_value = mock_response

        response = client.get(
            "/api/v2/user/assets/check-url",
            params={"url": "https://example.com/image.png"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["content_type"] == "image/png"

    def test_check_url_invalid_format(self, override_get_current_user_pro):
        """Test invalid URL format."""
        response = client.get(
            "/api/v2/user/assets/check-url",
            params={"url": "not-a-valid-url"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "Invalid URL" in data["error"]

    def test_check_url_ssrf_blocked(self, override_get_current_user_pro):
        """Test SSRF protection in check-url (UA-HIGH-1)."""
        response = client.get(
            "/api/v2/user/assets/check-url",
            params={"url": "http://127.0.0.1/image.png"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    def test_check_url_too_long(self, override_get_current_user_pro):
        """Test URL length limit in check-url (UA-LOW-2)."""
        long_url = "https://example.com/" + "a" * 3000
        response = client.get(
            "/api/v2/user/assets/check-url",
            params={"url": long_url},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "too long" in data["error"]


# ==========================================
# Tests - POST /api/v2/user/assets/{asset_id}/increment-usage
# ==========================================

class TestIncrementUsage:
    """Test POST /api/v2/user/assets/{asset_id}/increment-usage endpoint."""

    @patch('api.user.user_assets.SupabaseAssetRepository')
    def test_increment_usage_success(self, mock_repo_class, override_get_current_user_pro):
        """Test successful usage increment."""
        mock_repo = AsyncMock()
        mock_repo.increment_asset_usage.return_value = {"usage_count": 5}
        mock_repo_class.return_value = mock_repo

        response = client.post(f"/api/v2/user/assets/{VALID_ASSET_ID}/increment-usage")

        assert response.status_code == 200
        data = response.json()
        assert data["usage_count"] == 5

    def test_increment_usage_invalid_id(self, override_get_current_user_pro):
        """Test increment rejects invalid asset_id format (UA-MEDIUM-1)."""
        response = client.post(f"/api/v2/user/assets/{INVALID_UUID}/increment-usage")

        assert response.status_code == 400
        assert "Invalid asset ID format" in response.json()["message"]

    @patch('api.user.user_assets.SupabaseAssetRepository')
    def test_increment_usage_not_found(self, mock_repo_class, override_get_current_user_pro):
        """Test increment for non-existent asset."""
        mock_repo = AsyncMock()
        mock_repo.increment_asset_usage.return_value = None
        mock_repo_class.return_value = mock_repo

        response = client.post(f"/api/v2/user/assets/{NONEXISTENT_ASSET_ID}/increment-usage")

        assert response.status_code == 404


# ==========================================
# Tests - GET /api/v2/user/assets/dashboard
# ==========================================

class TestAssetDashboard:
    """Test GET /api/v2/user/assets/dashboard endpoint."""

    @patch('api.user.user_assets.get_supabase_client')
    def test_dashboard_success(self, mock_supabase, override_get_current_user_pro):
        """Test successful dashboard retrieval."""
        mock_result = MagicMock()
        mock_result.data = [
            {"id": VALID_ASSET_ID, "source": "uploaded", "usage_count": 3},
            {"id": "asset-2", "source": "external", "usage_count": 5},
        ]
        mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

        response = client.get("/api/v2/user/assets/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert data["total_assets"] == 2
        assert data["total_usage"] == 8
        assert "by_source" in data


# ==========================================
# Tests - GET /api/v2/user/assets/seller-stats
# ==========================================

class TestSellerStats:
    """Test GET /api/v2/user/assets/seller-stats endpoint."""

    @patch('api.user.user_assets.get_supabase_client')
    def test_seller_stats_success(self, mock_supabase, override_get_current_user_pro):
        """Test successful seller stats retrieval."""
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "listing-1", "title": "Asset 1", "price": 10, "sales_count": 5},
            {"id": "listing-2", "title": "Asset 2", "price": 20, "sales_count": 3},
        ]
        mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        response = client.get("/api/v2/user/assets/seller-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_listings"] == 2
        assert data["total_sales"] == 8
        assert data["total_revenue"] == 110  # 10*5 + 20*3


# ==========================================
# Tests - GET /api/v2/user/assets/deleted
# ==========================================

class TestGetDeleted:
    """Test GET /api/v2/user/assets/deleted endpoint."""

    @patch('api.user.user_assets.SupabaseAssetRepository')
    def test_get_deleted_success(self, mock_repo_class, override_get_current_user_pro):
        """Test successful deleted assets retrieval."""
        mock_repo = AsyncMock()
        mock_repo.get_deleted_assets.return_value = [
            {"id": VALID_ASSET_ID, "deleted_at": "2026-01-09T00:00:00Z"}
        ]
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v2/user/assets/deleted")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1


# ==========================================
# Tests - POST /api/v2/user/assets/{asset_id}/restore
# ==========================================

class TestRestoreAsset:
    """Test POST /api/v2/user/assets/{asset_id}/restore endpoint."""

    @patch('api.user.user_assets.SupabaseAssetRepository')
    def test_restore_asset_success(self, mock_repo_class, override_get_current_user_pro):
        """Test successful asset restoration."""
        mock_repo = AsyncMock()
        mock_repo.restore_asset.return_value = {"id": VALID_ASSET_ID}
        mock_repo_class.return_value = mock_repo

        response = client.post(f"/api/v2/user/assets/{VALID_ASSET_ID}/restore")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_restore_asset_invalid_id(self, override_get_current_user_pro):
        """Test restore rejects invalid asset_id format (UA-MEDIUM-1)."""
        response = client.post(f"/api/v2/user/assets/{INVALID_UUID}/restore")

        assert response.status_code == 400
        assert "Invalid asset ID format" in response.json()["message"]

    @patch('api.user.user_assets.SupabaseAssetRepository')
    def test_restore_asset_not_found(self, mock_repo_class, override_get_current_user_pro):
        """Test restore for non-existent asset."""
        mock_repo = AsyncMock()
        mock_repo.restore_asset.return_value = None
        mock_repo_class.return_value = mock_repo

        response = client.post(f"/api/v2/user/assets/{NONEXISTENT_ASSET_ID}/restore")

        assert response.status_code == 404
        assert "not found in trash" in response.json()["message"]

"""
Tests for Config API endpoints (v2)

API Module: api/user/config.py
Endpoints:
- GET /api/v2/user/config - Get all configs
- GET /api/v2/user/config/{key} - Get single config
- GET /api/v2/user/config/group/{group_name} - Get config group

@module tests.api.user.test_config
@version 2.1.0

Changes in v2.1.0:
- Updated tests to use PUBLIC_CONFIG_WHITELIST keys
- Added tests for non-whitelisted configs (403)
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

# IMPORTANT: Bypass rate limiter BEFORE importing app
_rate_limiter_patcher = patch('infrastructure.rate_limiter.limiter.limit', lambda rate: lambda func: func)
_rate_limiter_patcher.start()

from app import app

client = TestClient(app)


# ==========================================
# Tests: GET /api/v2/user/config
# ==========================================

class TestListAllConfigs:
    """Test GET /api/v2/user/config"""

    @patch('api.user.config.get_database_client')
    def test_get_all_configs_success(self, mock_get_db):
        """Should return only public (whitelisted) configurations"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_repo = MagicMock()
        # v2.1.0: Only whitelisted configs are returned
        mock_repo.get_all = AsyncMock(return_value=[
            {"key": "FEATURE_AI_GENERATION", "value": True, "description": "AI generation enabled"},
            {"key": "FEATURE_MARKETPLACE", "value": True, "description": "Marketplace enabled"},
            {"key": "MAX_UPLOAD_FILE_SIZE_MB", "value": 10, "description": "Max upload size"},
            {"key": "internal_secret", "value": "secret123", "description": "Should be filtered out"},
        ])

        with patch('api.user.config.SupabaseConfigRepository', return_value=mock_repo):
            response = client.get("/api/v2/user/config")

            assert response.status_code == 200
            data = response.json()

            # Should contain whitelisted configs
            assert "FEATURE_AI_GENERATION" in data
            assert "FEATURE_MARKETPLACE" in data
            assert "MAX_UPLOAD_FILE_SIZE_MB" in data

            # Should NOT contain non-whitelisted configs
            assert "internal_secret" not in data

            # Verify values
            assert data["FEATURE_AI_GENERATION"]["value"] is True
            assert data["MAX_UPLOAD_FILE_SIZE_MB"]["value"] == 10

    @patch('api.user.config.get_database_client')
    def test_get_all_configs_empty(self, mock_get_db):
        """Should return empty dict if no configs exist"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.get_all = AsyncMock(return_value=[])

        with patch('api.user.config.SupabaseConfigRepository', return_value=mock_repo):
            response = client.get("/api/v2/user/config")

            assert response.status_code == 200
            data = response.json()

            assert data == {}


# ==========================================
# Tests: GET /api/v2/user/config/{key}
# ==========================================

class TestGetSingleConfig:
    """Test GET /api/v2/user/config/{key}"""

    @patch('api.user.config.get_database_client')
    def test_get_config_by_key_success(self, mock_get_db):
        """Should return a single whitelisted configuration by key"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.get_by_key = AsyncMock(return_value=10)

        with patch('api.user.config.SupabaseConfigRepository', return_value=mock_repo):
            # v2.1.0: Use whitelisted config key
            response = client.get("/api/v2/user/config/MAX_UPLOAD_FILE_SIZE_MB")

            assert response.status_code == 200
            data = response.json()

            assert data["key"] == "MAX_UPLOAD_FILE_SIZE_MB"
            assert data["value"] == 10

            # Verify get_by_key was called with correct key
            mock_repo.get_by_key.assert_called_once_with("MAX_UPLOAD_FILE_SIZE_MB")

    @patch('api.user.config.get_database_client')
    def test_get_config_by_key_not_found(self, mock_get_db):
        """Should return 404 if whitelisted config key doesn't exist"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.get_by_key = AsyncMock(return_value=None)

        with patch('api.user.config.SupabaseConfigRepository', return_value=mock_repo):
            # v2.1.0: Use whitelisted key that doesn't exist in database
            response = client.get("/api/v2/user/config/FEATURE_AI_GENERATION")

            assert response.status_code == 404
            data = response.json()

            # API uses custom error handler that converts 'detail' to 'message'
            error_msg = data.get("message", "") or data.get("detail", "")
            assert "not found" in error_msg.lower()

    def test_get_config_non_whitelisted_returns_403(self):
        """Should return 403 for non-whitelisted config keys (C-P0-1 fix)"""
        # v2.1.0: Non-whitelisted configs should return 403 Forbidden
        response = client.get("/api/v2/user/config/internal_secret")

        assert response.status_code == 403
        data = response.json()
        error_msg = data.get("message", "") or data.get("detail", "")
        # Check for various access denied messages
        assert any(term in error_msg.lower() for term in ["not accessible", "forbidden", "access denied", "denied"])

    @patch('api.user.config.get_database_client')
    def test_get_config_boolean_value(self, mock_get_db):
        """Should correctly handle boolean config values"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.get_by_key = AsyncMock(return_value=True)

        with patch('api.user.config.SupabaseConfigRepository', return_value=mock_repo):
            # v2.1.0: Use whitelisted config key
            response = client.get("/api/v2/user/config/FEATURE_AI_GENERATION")

            assert response.status_code == 200
            data = response.json()

            assert data["key"] == "FEATURE_AI_GENERATION"
            assert data["value"] is True

    @patch('api.user.config.get_database_client')
    def test_get_config_string_value(self, mock_get_db):
        """Should correctly handle string config values"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.get_by_key = AsyncMock(return_value="jpg,png,gif")

        with patch('api.user.config.SupabaseConfigRepository', return_value=mock_repo):
            # v2.1.0: Use whitelisted config key
            response = client.get("/api/v2/user/config/SUPPORTED_IMAGE_FORMATS")

            assert response.status_code == 200
            data = response.json()

            assert data["key"] == "SUPPORTED_IMAGE_FORMATS"
            assert data["value"] == "jpg,png,gif"

    @patch('api.user.config.get_database_client')
    def test_get_config_pattern_whitelist(self, mock_get_db):
        """Should allow configs matching whitelist patterns (e.g., FEATURE_*)"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.get_by_key = AsyncMock(return_value=True)

        with patch('api.user.config.SupabaseConfigRepository', return_value=mock_repo):
            # v2.1.0: FEATURE_ prefix matches pattern
            response = client.get("/api/v2/user/config/FEATURE_NEW_FEATURE")

            assert response.status_code == 200
            data = response.json()

            assert data["key"] == "FEATURE_NEW_FEATURE"
            assert data["value"] is True


# ==========================================
# Tests: GET /api/v2/user/config/group/{group_name}
# ==========================================

class TestGetConfigGroup:
    """Test GET /api/v2/user/config/group/{group_name}"""

    @patch('api.user.config.get_database_client')
    def test_get_config_group_success(self, mock_get_db):
        """Should return all public configs in a specific group"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_repo = MagicMock()
        # v2.1.0: Return mix of whitelisted and non-whitelisted configs
        mock_repo.get_all = AsyncMock(return_value=[
            {"key": "MAX_UPLOAD_FILE_SIZE_MB", "value": 10, "description": "Max upload size"},
            {"key": "MAX_LISTING_PRICE", "value": 1000, "description": "Max listing price"},
            {"key": "internal_limit", "value": 999, "description": "Should be filtered"},
        ])

        with patch('api.user.config.SupabaseConfigRepository', return_value=mock_repo):
            response = client.get("/api/v2/user/config/group/limits")

            assert response.status_code == 200
            data = response.json()

            assert data["group"] == "limits"
            assert "configs" in data
            # Only 2 whitelisted configs should be returned
            assert len(data["configs"]) == 2

            # Verify only whitelisted configs are included
            config_keys = [c["key"] for c in data["configs"]]
            assert "MAX_UPLOAD_FILE_SIZE_MB" in config_keys
            assert "MAX_LISTING_PRICE" in config_keys
            assert "internal_limit" not in config_keys

            # Verify get_all was called with group filter
            mock_repo.get_all.assert_called_once_with(group="limits")

    @patch('api.user.config.get_database_client')
    def test_get_config_group_empty(self, mock_get_db):
        """Should return empty configs array for non-existent group"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.get_all = AsyncMock(return_value=[])

        with patch('api.user.config.SupabaseConfigRepository', return_value=mock_repo):
            response = client.get("/api/v2/user/config/group/nonexistent")

            assert response.status_code == 200
            data = response.json()

            assert data["group"] == "nonexistent"
            assert data["configs"] == []

    @patch('api.user.config.get_database_client')
    def test_get_feature_flags_group(self, mock_get_db):
        """Should return feature flag configs (all start with FEATURE_)"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_repo = MagicMock()
        # v2.1.0: All FEATURE_ prefixed configs are whitelisted
        mock_repo.get_all = AsyncMock(return_value=[
            {"key": "FEATURE_AI_GENERATION", "value": True, "description": "AI features"},
            {"key": "FEATURE_MARKETPLACE", "value": True, "description": "Marketplace"},
            {"key": "FEATURE_OCR", "value": False, "description": "OCR"},
        ])

        with patch('api.user.config.SupabaseConfigRepository', return_value=mock_repo):
            response = client.get("/api/v2/user/config/group/features")

            assert response.status_code == 200
            data = response.json()

            assert data["group"] == "features"
            assert len(data["configs"]) == 3

            # Verify all are boolean feature flags
            for config in data["configs"]:
                assert isinstance(config["value"], bool)


# ==========================================
# Summary
# ==========================================
# Total tests: 12
# Coverage:
# - GET /api/v2/user/config (2 tests)
# - GET /api/v2/user/config/{key} (6 tests including security test)
# - GET /api/v2/user/config/group/{group_name} (3 tests)
# - Various data types (int, bool, string)
# - Error handling (403 for non-whitelisted, 404 for not found)
# - Empty results
# - Pattern-based whitelist (FEATURE_*)
#
# v2.1.0 Security:
# - Non-whitelisted configs return 403
# - Only PUBLIC_CONFIG_WHITELIST keys are accessible
# ==========================================

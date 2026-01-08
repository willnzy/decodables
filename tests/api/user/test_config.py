"""
Tests for Config API endpoints (v2)

API Module: api/user/config.py
Endpoints:
- GET /api/v2/user/config - Get all configs
- GET /api/v2/user/config/{key} - Get single config
- GET /api/v2/user/config/group/{group_name} - Get config group

@module tests.api.user.test_config
@version 2.0.0
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
        """Should return all public configurations as dict"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.get_all = AsyncMock(return_value=[
            {"key": "max_project_size", "value": 10485760, "description": "Max project size in bytes"},
            {"key": "max_uploads_per_day", "value": 100, "description": "Max uploads per day"},
            {"key": "feature_ai_enabled", "value": True, "description": "AI features enabled"},
        ])

        with patch('api.user.config.SupabaseConfigRepository', return_value=mock_repo):
            response = client.get("/api/v2/user/config")

            assert response.status_code == 200
            data = response.json()

            # Should be a dict with keys as config keys
            assert "max_project_size" in data
            assert "max_uploads_per_day" in data
            assert "feature_ai_enabled" in data

            # Verify values
            assert data["max_project_size"]["value"] == 10485760
            assert data["max_uploads_per_day"]["value"] == 100
            assert data["feature_ai_enabled"]["value"] is True

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
        """Should return a single configuration by key"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.get_by_key = AsyncMock(return_value=10485760)

        with patch('api.user.config.SupabaseConfigRepository', return_value=mock_repo):
            response = client.get("/api/v2/user/config/max_project_size")

            assert response.status_code == 200
            data = response.json()

            assert data["key"] == "max_project_size"
            assert data["value"] == 10485760

            # Verify get_by_key was called with correct key
            mock_repo.get_by_key.assert_called_once_with("max_project_size")

    @patch('api.user.config.get_database_client')
    def test_get_config_by_key_not_found(self, mock_get_db):
        """Should return 404 if config key doesn't exist"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.get_by_key = AsyncMock(return_value=None)

        with patch('api.user.config.SupabaseConfigRepository', return_value=mock_repo):
            response = client.get("/api/v2/user/config/nonexistent_key")

            assert response.status_code == 404
            data = response.json()

            # API uses custom error handler that converts 'detail' to 'message'
            assert "not found" in data["message"].lower()

    @patch('api.user.config.get_database_client')
    def test_get_config_boolean_value(self, mock_get_db):
        """Should correctly handle boolean config values"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.get_by_key = AsyncMock(return_value=True)

        with patch('api.user.config.SupabaseConfigRepository', return_value=mock_repo):
            response = client.get("/api/v2/user/config/feature_ai_enabled")

            assert response.status_code == 200
            data = response.json()

            assert data["key"] == "feature_ai_enabled"
            assert data["value"] is True

    @patch('api.user.config.get_database_client')
    def test_get_config_string_value(self, mock_get_db):
        """Should correctly handle string config values"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.get_by_key = AsyncMock(return_value="production")

        with patch('api.user.config.SupabaseConfigRepository', return_value=mock_repo):
            response = client.get("/api/v2/user/config/environment")

            assert response.status_code == 200
            data = response.json()

            assert data["key"] == "environment"
            assert data["value"] == "production"


# ==========================================
# Tests: GET /api/v2/user/config/group/{group_name}
# ==========================================

class TestGetConfigGroup:
    """Test GET /api/v2/user/config/group/{group_name}"""

    @patch('api.user.config.get_database_client')
    def test_get_config_group_success(self, mock_get_db):
        """Should return all configs in a specific group"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.get_all = AsyncMock(return_value=[
            {"key": "max_project_size", "value": 10485760, "description": "Max project size"},
            {"key": "max_uploads_per_day", "value": 100, "description": "Max uploads"},
        ])

        with patch('api.user.config.SupabaseConfigRepository', return_value=mock_repo):
            response = client.get("/api/v2/user/config/group/limits")

            assert response.status_code == 200
            data = response.json()

            assert data["group"] == "limits"
            assert "configs" in data
            assert len(data["configs"]) == 2

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
        """Should return feature flag configs"""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_repo = MagicMock()
        mock_repo.get_all = AsyncMock(return_value=[
            {"key": "feature_ai_enabled", "value": True, "description": "AI features"},
            {"key": "feature_marketplace_enabled", "value": True, "description": "Marketplace"},
            {"key": "feature_experiments_enabled", "value": False, "description": "A/B tests"},
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
# Total tests: 10
# Coverage:
# - GET /api/v2/user/config (2 tests)
# - GET /api/v2/user/config/{key} (4 tests)
# - GET /api/v2/user/config/group/{group_name} (3 tests)
# - Various data types (int, bool, string)
# - Error handling (404)
# - Empty results
# ==========================================

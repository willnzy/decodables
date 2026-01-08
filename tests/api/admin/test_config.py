"""Test admin/config API endpoints.

Tests for system configuration management endpoints.
v3.25: Added comprehensive tests including security validation.
"""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import app


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# ==========================================
# Basic Endpoint Tests (Auth)
# ==========================================

class TestConfigEndpointsAuth:
    """Basic tests for config API authentication requirements."""

    def test_get_all_configs_requires_auth(self, client):
        """Get all configs endpoint requires authentication."""
        response = client.get("/api/v2/admin/config/config")
        assert response.status_code in [401, 403]

    def test_get_config_requires_auth(self, client):
        """Get single config endpoint requires authentication."""
        response = client.get("/api/v2/admin/config/config/test.key")
        assert response.status_code in [401, 403]

    def test_update_config_requires_auth(self, client):
        """Update config endpoint requires authentication."""
        response = client.put(
            "/api/v2/admin/config/config",
            json={"config_key": "test.key", "config_value": {"value": 1}}
        )
        assert response.status_code in [401, 403]

    def test_batch_update_configs_requires_auth(self, client):
        """Batch update configs endpoint requires authentication."""
        response = client.put(
            "/api/v2/admin/config/config/batch",
            json={"updates": []}
        )
        assert response.status_code in [401, 403]

    def test_clear_config_cache_requires_auth(self, client):
        """Clear config cache endpoint requires authentication."""
        response = client.post("/api/v2/admin/config/config/cache/clear")
        assert response.status_code in [401, 403]

    def test_get_rate_limits_requires_auth(self, client):
        """Get rate limits endpoint requires authentication."""
        response = client.get("/api/v2/admin/config/rate-limits")
        assert response.status_code in [401, 403]

    def test_apply_rate_limit_preset_requires_auth(self, client):
        """Apply rate limit preset endpoint requires authentication."""
        response = client.post(
            "/api/v2/admin/config/rate-limits/preset",
            json={"preset": "normal"}
        )
        assert response.status_code in [401, 403]

    def test_get_rate_limit_presets_requires_auth(self, client):
        """Get rate limit presets endpoint requires authentication."""
        response = client.get("/api/v2/admin/config/rate-limits/presets")
        assert response.status_code in [401, 403]


# ==========================================
# Parameter Validation Tests (Unit Tests)
# ==========================================

class TestConfigParameterValidation:
    """Unit tests for parameter validation in request models."""

    def test_config_update_request_key_length(self):
        """Config key must be between 1 and 200 characters."""
        from api.admin.config import ConfigUpdateRequest

        # Valid keys
        ConfigUpdateRequest(config_key="test.key", config_value={"value": 1})
        ConfigUpdateRequest(config_key="a" * 200, config_value={"value": 1})

        # Invalid: empty key
        with pytest.raises(ValidationError):
            ConfigUpdateRequest(config_key="", config_value={"value": 1})

        # Invalid: too long
        with pytest.raises(ValidationError):
            ConfigUpdateRequest(config_key="a" * 201, config_value={"value": 1})

    def test_batch_config_update_request_max_updates(self):
        """Batch updates must not exceed 100 items."""
        from api.admin.config import BatchConfigUpdateRequest

        # Valid: within limit
        BatchConfigUpdateRequest(updates=[{"key": "test", "value": {}} for _ in range(100)])

        # Invalid: too many updates
        with pytest.raises(ValidationError):
            BatchConfigUpdateRequest(updates=[{"key": "test", "value": {}} for _ in range(101)])

    def test_rate_limit_preset_request_validation(self):
        """Preset must be a valid preset name."""
        from api.admin.config import RateLimitPresetRequest

        # Valid presets
        for preset in ["strict", "normal", "relaxed", "disabled"]:
            req = RateLimitPresetRequest(preset=preset)
            assert req.preset == preset

        # Invalid preset
        with pytest.raises(ValidationError) as exc_info:
            RateLimitPresetRequest(preset="invalid")
        assert "Invalid preset" in str(exc_info.value)


# ==========================================
# Constants Tests
# ==========================================

class TestConfigConstants:
    """Tests for config constants."""

    def test_valid_config_categories(self):
        """Valid config categories are defined."""
        from api.admin.config import VALID_CONFIG_CATEGORIES

        assert "rate_limit" in VALID_CONFIG_CATEGORIES
        assert "feature_flags" in VALID_CONFIG_CATEGORIES
        assert "system" in VALID_CONFIG_CATEGORIES
        assert "ai" in VALID_CONFIG_CATEGORIES
        assert "storage" in VALID_CONFIG_CATEGORIES
        assert "payment" in VALID_CONFIG_CATEGORIES
        assert "invalid" not in VALID_CONFIG_CATEGORIES

    def test_valid_rate_limit_presets(self):
        """Valid rate limit presets are defined."""
        from api.admin.config import VALID_RATE_LIMIT_PRESETS

        assert "strict" in VALID_RATE_LIMIT_PRESETS
        assert "normal" in VALID_RATE_LIMIT_PRESETS
        assert "relaxed" in VALID_RATE_LIMIT_PRESETS
        assert "disabled" in VALID_RATE_LIMIT_PRESETS
        assert "invalid" not in VALID_RATE_LIMIT_PRESETS

    def test_rate_limit_presets_structure(self):
        """Rate limit presets have expected structure."""
        from domains.platform.config_service import RATE_LIMIT_PRESETS

        for preset_name, preset_data in RATE_LIMIT_PRESETS.items():
            assert isinstance(preset_data, dict)
            assert "description" in preset_data


# ==========================================
# Integration-style Tests
# ==========================================

class TestConfigFieldValidation:
    """Integration tests for field validation at API level."""

    @pytest.mark.parametrize("preset", ["strict", "normal", "relaxed", "disabled"])
    def test_valid_preset_values(self, preset):
        """Valid preset values are accepted."""
        from api.admin.config import RateLimitPresetRequest

        req = RateLimitPresetRequest(preset=preset)
        assert req.preset == preset

    @pytest.mark.parametrize("key_length", [1, 10, 50, 100, 200])
    def test_valid_config_key_lengths(self, key_length):
        """Valid config key lengths are accepted."""
        from api.admin.config import ConfigUpdateRequest

        req = ConfigUpdateRequest(
            config_key="a" * key_length,
            config_value={"value": 1}
        )
        assert len(req.config_key) == key_length

    @pytest.mark.parametrize("num_updates", [1, 10, 50, 100])
    def test_valid_batch_update_sizes(self, num_updates):
        """Valid batch update sizes are accepted."""
        from api.admin.config import BatchConfigUpdateRequest

        req = BatchConfigUpdateRequest(
            updates=[{"key": f"test.{i}", "value": {}} for i in range(num_updates)]
        )
        assert len(req.updates) == num_updates


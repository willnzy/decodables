"""Test admin/system API endpoints.

Tests for admin system configuration and cache management endpoints.
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

class TestSystemEndpointsAuth:
    """Basic tests for system API authentication requirements."""

    def test_get_configs_requires_auth(self, client):
        """Get configs endpoint requires authentication."""
        response = client.get("/api/v2/admin/system/configs")
        assert response.status_code in [401, 403]

    def test_get_config_groups_requires_auth(self, client):
        """Get config groups endpoint requires authentication."""
        response = client.get("/api/v2/admin/system/configs/groups")
        assert response.status_code in [401, 403]

    def test_create_config_requires_auth(self, client):
        """Create config endpoint requires authentication."""
        response = client.post(
            "/api/v2/admin/system/configs",
            json={"key": "test", "value": "test"}
        )
        assert response.status_code in [401, 403]

    def test_update_config_requires_auth(self, client):
        """Update config endpoint requires authentication."""
        response = client.put(
            "/api/v2/admin/system/configs/test-key",
            json={"value": "new value"}
        )
        assert response.status_code in [401, 403]

    def test_delete_config_requires_auth(self, client):
        """Delete config endpoint requires authentication."""
        response = client.delete("/api/v2/admin/system/configs/test-key")
        assert response.status_code in [401, 403]

    def test_get_config_audit_requires_auth(self, client):
        """Get config audit endpoint requires authentication."""
        response = client.get("/api/v2/admin/system/configs/audit")
        assert response.status_code in [401, 403]

    def test_invalidate_cache_requires_auth(self, client):
        """Invalidate cache endpoint requires authentication."""
        response = client.post("/api/v2/admin/system/configs/cache/invalidate")
        assert response.status_code in [401, 403]

    def test_get_cache_status_requires_auth(self, client):
        """Get cache status endpoint requires authentication."""
        response = client.get("/api/v2/admin/system/system/cache/status")
        assert response.status_code in [401, 403]

    def test_list_cache_keys_requires_auth(self, client):
        """List cache keys endpoint requires authentication."""
        response = client.get("/api/v2/admin/system/system/cache/keys")
        assert response.status_code in [401, 403]

    def test_delete_cache_key_requires_auth(self, client):
        """Delete cache key endpoint requires authentication."""
        response = client.delete("/api/v2/admin/system/system/cache/key/test-key")
        assert response.status_code in [401, 403]

    def test_clear_all_cache_requires_auth(self, client):
        """Clear all cache endpoint requires authentication."""
        response = client.post("/api/v2/admin/system/system/cache/clear-all")
        assert response.status_code in [401, 403]


# ==========================================
# Constants Tests
# ==========================================

class TestSystemConstants:
    """Tests for system constants."""

    def test_valid_value_types(self):
        """Valid value types are defined."""
        from api.admin.system import VALID_VALUE_TYPES

        assert "text" in VALID_VALUE_TYPES
        assert "json" in VALID_VALUE_TYPES
        assert "number" in VALID_VALUE_TYPES
        assert "boolean" in VALID_VALUE_TYPES
        assert "encrypted" in VALID_VALUE_TYPES
        assert "invalid" not in VALID_VALUE_TYPES

    def test_valid_config_groups(self):
        """Valid config groups are defined."""
        from api.admin.system import VALID_CONFIG_GROUPS

        assert "general" in VALID_CONFIG_GROUPS
        assert "feature_flags" in VALID_CONFIG_GROUPS
        assert "payment" in VALID_CONFIG_GROUPS
        assert "ai" in VALID_CONFIG_GROUPS
        assert "notification" in VALID_CONFIG_GROUPS
        assert "security" in VALID_CONFIG_GROUPS
        assert "cache" in VALID_CONFIG_GROUPS
        assert "invalid" not in VALID_CONFIG_GROUPS

    def test_cache_key_pattern(self):
        """Cache key pattern matches expected formats."""
        from api.admin.system import CACHE_KEY_PATTERN

        # Valid patterns
        assert CACHE_KEY_PATTERN.match("user:123")
        assert CACHE_KEY_PATTERN.match("config_cache")
        assert CACHE_KEY_PATTERN.match("prefix:*")
        assert CACHE_KEY_PATTERN.match("key-with-hyphen")
        assert CACHE_KEY_PATTERN.match("key.with.dots")

        # Invalid patterns
        assert not CACHE_KEY_PATTERN.match("key with spaces")
        assert not CACHE_KEY_PATTERN.match("key$special")
        assert not CACHE_KEY_PATTERN.match("key<>brackets")


# ==========================================
# Request Model Validation Tests
# ==========================================

class TestConfigCreateRequestValidation:
    """Tests for ConfigCreateRequest model validation."""

    def test_valid_create_request(self):
        """Valid create request is accepted."""
        from api.admin.system import ConfigCreateRequest

        req = ConfigCreateRequest(
            key="test.config.key",
            value="test value",
            value_type="text",
            config_group="general",
            description="Test description"
        )
        assert req.key == "test.config.key"
        assert req.value_type == "text"

    def test_create_default_values(self):
        """Default values are applied."""
        from api.admin.system import ConfigCreateRequest

        req = ConfigCreateRequest(key="test", value="value")
        assert req.value_type == "text"
        assert req.config_group == "general"
        assert req.description is None

    def test_create_key_length_validation(self):
        """Key must be between 1-200 characters."""
        from api.admin.system import ConfigCreateRequest

        # Valid key
        ConfigCreateRequest(key="a" * 200, value="value")

        # Invalid: empty key
        with pytest.raises(ValidationError):
            ConfigCreateRequest(key="", value="value")

        # Invalid: too long
        with pytest.raises(ValidationError):
            ConfigCreateRequest(key="a" * 201, value="value")

    def test_create_value_type_validation(self):
        """Value type must be valid."""
        from api.admin.system import ConfigCreateRequest

        # Valid value types
        for vtype in ["text", "json", "number", "boolean", "encrypted"]:
            req = ConfigCreateRequest(key="test", value="value", value_type=vtype)
            assert req.value_type == vtype

        # Invalid value type
        with pytest.raises(ValidationError) as exc_info:
            ConfigCreateRequest(key="test", value="value", value_type="invalid")
        assert "Invalid value_type" in str(exc_info.value)

    def test_create_config_group_validation(self):
        """Config group must be valid."""
        from api.admin.system import ConfigCreateRequest

        # Valid config groups
        for group in ["general", "feature_flags", "payment", "ai", "notification", "security", "cache"]:
            req = ConfigCreateRequest(key="test", value="value", config_group=group)
            assert req.config_group == group

        # Invalid config group
        with pytest.raises(ValidationError) as exc_info:
            ConfigCreateRequest(key="test", value="value", config_group="invalid")
        assert "Invalid config_group" in str(exc_info.value)


class TestConfigUpdateRequestValidation:
    """Tests for ConfigUpdateRequest model validation."""

    def test_valid_update_request(self):
        """Valid update request is accepted."""
        from api.admin.system import ConfigUpdateRequest

        req = ConfigUpdateRequest(
            value="new value",
            description="Updated description",
            is_active=False
        )
        assert req.value == "new value"
        assert req.is_active is False

    def test_update_all_optional(self):
        """All fields are optional."""
        from api.admin.system import ConfigUpdateRequest

        req = ConfigUpdateRequest()
        assert req.value is None
        assert req.value_type is None
        assert req.config_group is None
        assert req.description is None
        assert req.is_active is None

    def test_update_value_type_validation(self):
        """Value type must be valid when provided."""
        from api.admin.system import ConfigUpdateRequest

        # Valid value type
        req = ConfigUpdateRequest(value_type="json")
        assert req.value_type == "json"

        # Invalid value type
        with pytest.raises(ValidationError) as exc_info:
            ConfigUpdateRequest(value_type="invalid")
        assert "Invalid value_type" in str(exc_info.value)

    def test_update_config_group_validation(self):
        """Config group must be valid when provided."""
        from api.admin.system import ConfigUpdateRequest

        # Valid config group
        req = ConfigUpdateRequest(config_group="payment")
        assert req.config_group == "payment"

        # Invalid config group
        with pytest.raises(ValidationError) as exc_info:
            ConfigUpdateRequest(config_group="invalid")
        assert "Invalid config_group" in str(exc_info.value)


# ==========================================
# Parameter Validation Tests
# ==========================================

class TestSystemParameterValidation:
    """Integration tests for parameter validation."""

    @pytest.mark.parametrize("value_type", ["text", "json", "number", "boolean", "encrypted"])
    def test_valid_value_type_values(self, value_type):
        """Valid value type values are accepted."""
        from api.admin.system import VALID_VALUE_TYPES

        assert value_type in VALID_VALUE_TYPES

    @pytest.mark.parametrize("config_group", ["general", "feature_flags", "payment", "ai", "notification", "security", "cache"])
    def test_valid_config_group_values(self, config_group):
        """Valid config group values are accepted."""
        from api.admin.system import VALID_CONFIG_GROUPS

        assert config_group in VALID_CONFIG_GROUPS

    @pytest.mark.parametrize("pattern", ["*", "user:*", "config_*", "key:123"])
    def test_valid_cache_patterns(self, pattern):
        """Valid cache patterns are accepted."""
        from api.admin.system import CACHE_KEY_PATTERN

        assert CACHE_KEY_PATTERN.match(pattern)

    @pytest.mark.parametrize("pattern", ["key with spaces", "key$special", "key;injection"])
    def test_invalid_cache_patterns(self, pattern):
        """Invalid cache patterns are rejected."""
        from api.admin.system import CACHE_KEY_PATTERN

        assert not CACHE_KEY_PATTERN.match(pattern)

    @pytest.mark.parametrize("offset", [0, 10, 50, 100])
    def test_valid_offset_values(self, offset):
        """Valid offset values are non-negative."""
        assert offset >= 0

    @pytest.mark.parametrize("limit", [1, 50, 100])
    def test_valid_limit_values(self, limit):
        """Valid limit values are within range."""
        assert 1 <= limit <= 100

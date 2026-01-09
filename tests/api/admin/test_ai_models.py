"""Test admin/ai_models API endpoints.

Tests for AI model configuration management endpoints.
v3.25: Added comprehensive tests including security validation.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app import app


# ==========================================
# Test Constants
# ==========================================

ADMIN_USER = {"id": "admin-user-id", "email": "admin@test.com", "role": "admin"}


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# ==========================================
# Basic Endpoint Tests
# ==========================================

class TestAdminAiModelsEndpoints:
    """Basic tests for admin AI models API endpoints."""

    def test_get_config_requires_auth(self, client):
        """Get config endpoint requires authentication."""
        response = client.get("/api/v2/admin/ai/models/config")
        assert response.status_code in [401, 403]

    def test_update_text_config_requires_auth(self, client):
        """Update text config endpoint requires authentication."""
        response = client.put(
            "/api/v2/admin/ai/models/config/text",
            json={"model": "gpt-4"}
        )
        assert response.status_code in [401, 403]

    def test_update_image_config_requires_auth(self, client):
        """Update image config endpoint requires authentication."""
        response = client.put(
            "/api/v2/admin/ai/models/config/image",
            json={"model": "flux"}
        )
        assert response.status_code in [401, 403]

    def test_update_admin_config_requires_auth(self, client):
        """Update admin config endpoint requires authentication."""
        response = client.put("/api/v2/admin/ai/models/config/admin")
        assert response.status_code in [401, 403]

    def test_update_canary_config_requires_auth(self, client):
        """Update canary config endpoint requires authentication."""
        response = client.put(
            "/api/v2/admin/ai/models/config/canary",
            json={"enabled": True, "percentage": 10}
        )
        assert response.status_code in [401, 403]

    def test_toggle_provider_requires_auth(self, client):
        """Toggle provider endpoint requires authentication."""
        response = client.put(
            "/api/v2/admin/ai/models/providers/toggle",
            json={"provider": "openai", "enabled": True}
        )
        assert response.status_code in [401, 403]

    def test_get_usage_requires_auth(self, client):
        """Get usage endpoint requires authentication."""
        response = client.get("/api/v2/admin/ai/models/usage")
        assert response.status_code in [401, 403]

    def test_clear_cache_requires_auth(self, client):
        """Clear cache endpoint requires authentication."""
        response = client.post("/api/v2/admin/ai/models/cache/clear")
        assert response.status_code in [401, 403]


# ==========================================
# Parameter Validation Tests (Unit Tests)
# ==========================================

class TestAiModelsParameterValidation:
    """Unit tests for parameter validation in request models."""

    def test_text_model_config_temperature_range(self):
        """Temperature must be between 0 and 2."""
        from api.admin.ai_models import TextModelConfigUpdate
        from pydantic import ValidationError

        # Valid temperatures
        TextModelConfigUpdate(temperature=0)
        TextModelConfigUpdate(temperature=1.0)
        TextModelConfigUpdate(temperature=2)

        # Invalid temperatures
        with pytest.raises(ValidationError):
            TextModelConfigUpdate(temperature=-0.1)

        with pytest.raises(ValidationError):
            TextModelConfigUpdate(temperature=2.1)

    def test_text_model_config_max_tokens_range(self):
        """Max tokens must be between 1 and 32000."""
        from api.admin.ai_models import TextModelConfigUpdate
        from pydantic import ValidationError

        # Valid max_tokens
        TextModelConfigUpdate(max_tokens=1)
        TextModelConfigUpdate(max_tokens=4096)
        TextModelConfigUpdate(max_tokens=32000)

        # Invalid max_tokens
        with pytest.raises(ValidationError):
            TextModelConfigUpdate(max_tokens=0)

        with pytest.raises(ValidationError):
            TextModelConfigUpdate(max_tokens=32001)

    def test_canary_config_percentage_range(self):
        """Canary percentage must be between 0 and 100."""
        from api.admin.ai_models import CanaryConfigUpdate
        from pydantic import ValidationError

        # Valid percentages
        CanaryConfigUpdate(enabled=True, percentage=0)
        CanaryConfigUpdate(enabled=True, percentage=50)
        CanaryConfigUpdate(enabled=True, percentage=100)

        # Invalid percentages
        with pytest.raises(ValidationError):
            CanaryConfigUpdate(enabled=True, percentage=-1)

        with pytest.raises(ValidationError):
            CanaryConfigUpdate(enabled=True, percentage=101)

    def test_provider_toggle_valid_providers(self):
        """Provider must be a valid provider name."""
        from api.admin.ai_models import ProviderToggleRequest
        from pydantic import ValidationError

        # Valid providers
        for provider in ["openai", "fal", "dashscope", "anthropic", "replicate"]:
            req = ProviderToggleRequest(provider=provider, enabled=True)
            assert req.provider == provider

        # Case insensitive
        req = ProviderToggleRequest(provider="OpenAI", enabled=True)
        assert req.provider == "openai"

        # Invalid provider
        with pytest.raises(ValidationError) as exc_info:
            ProviderToggleRequest(provider="invalid", enabled=True)
        assert "Invalid provider" in str(exc_info.value)

    def test_valid_providers_set(self):
        """Valid providers set is defined."""
        # v3.30: Updated import from Domain layer
        from domains.platform.ai.constants import VALID_PROVIDERS

        assert "openai" in VALID_PROVIDERS
        assert "fal" in VALID_PROVIDERS
        assert "dashscope" in VALID_PROVIDERS
        assert "anthropic" in VALID_PROVIDERS
        assert "replicate" in VALID_PROVIDERS
        assert "invalid" not in VALID_PROVIDERS


# ==========================================
# Service Function Tests
# ==========================================

class TestModelConfigService:
    """Tests for model_config_service functions."""

    def test_get_model_configs(self):
        """get_model_configs returns config dict with expected keys."""
        from shared.ai.model_config_service import get_model_configs

        result = get_model_configs()

        # Should return dict with expected keys
        assert isinstance(result, dict)
        assert "text" in result
        assert "image" in result
        assert "admin" in result
        assert "enabled_providers" in result

    def test_update_text_model_config(self):
        """update_text_model_config returns success response."""
        from shared.ai.model_config_service import update_text_model_config

        result = update_text_model_config(
            provider="openai",
            model="gpt-4",
            max_tokens=4096,
            temperature=0.7
        )

        assert result["success"] is True
        assert "config" in result

    def test_update_image_model_config(self):
        """update_image_model_config returns success response."""
        from shared.ai.model_config_service import update_image_model_config

        result = update_image_model_config(
            tier="pro",
            provider="fal",
            model="flux"
        )

        assert result["success"] is True
        assert "config" in result

    def test_toggle_ai_provider(self):
        """toggle_ai_provider returns success response."""
        from shared.ai.model_config_service import toggle_ai_provider

        result = toggle_ai_provider("openai", True)

        assert result["success"] is True
        assert result["provider"] == "openai"
        assert result["enabled"] is True

    def test_get_ai_usage_stats(self):
        """get_ai_usage_stats returns usage dict."""
        from shared.ai.model_config_service import get_ai_usage_stats

        result = get_ai_usage_stats()

        assert "total_requests" in result
        assert "total_tokens" in result
        assert "by_provider" in result

    def test_clear_ai_cache(self):
        """clear_ai_cache returns success response."""
        from shared.ai.model_config_service import clear_ai_cache

        result = clear_ai_cache()

        assert result["success"] is True


# ==========================================
# Integration-style Tests
# ==========================================

class TestAiModelsFieldValidation:
    """Integration tests for field validation at API level."""

    @pytest.mark.parametrize("temperature", [0, 0.5, 1.0, 1.5, 2.0])
    def test_valid_temperature_values(self, temperature):
        """Valid temperature values are accepted."""
        from api.admin.ai_models import TextModelConfigUpdate

        config = TextModelConfigUpdate(temperature=temperature)
        assert config.temperature == temperature

    @pytest.mark.parametrize("max_tokens", [1, 100, 4096, 8192, 32000])
    def test_valid_max_tokens_values(self, max_tokens):
        """Valid max_tokens values are accepted."""
        from api.admin.ai_models import TextModelConfigUpdate

        config = TextModelConfigUpdate(max_tokens=max_tokens)
        assert config.max_tokens == max_tokens

    @pytest.mark.parametrize("percentage", [0, 1, 50, 99, 100])
    def test_valid_canary_percentage_values(self, percentage):
        """Valid canary percentage values are accepted."""
        from api.admin.ai_models import CanaryConfigUpdate

        config = CanaryConfigUpdate(enabled=True, percentage=percentage)
        assert config.percentage == percentage

    @pytest.mark.parametrize("provider", ["openai", "fal", "dashscope", "anthropic", "replicate"])
    def test_valid_provider_values(self, provider):
        """Valid provider values are accepted."""
        from api.admin.ai_models import ProviderToggleRequest

        config = ProviderToggleRequest(provider=provider, enabled=True)
        assert config.provider == provider

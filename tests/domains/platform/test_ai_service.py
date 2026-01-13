"""
Unit tests for AI Models Service (Domain Layer).

Tests v3.31 enhancements:
1. Repository dependency injection

@module tests.domains.platform.test_ai_service

Note: Business logic is already thoroughly tested in tests/api/admin/test_ai_models.py (39 tests).
These tests focus specifically on the Repository DI functionality.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from domains.platform.ai.service import (
    update_text_model_config,
    update_image_model_config,
    update_canary_config,
    toggle_ai_provider,
)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_config_repo():
    """Create mock AIModelConfigRepository."""
    repo = AsyncMock()
    repo.get_by_key = AsyncMock(return_value=None)
    repo.create = AsyncMock(return_value=True)
    repo.update = AsyncMock(return_value=True)
    return repo


# ==========================================
# Repository Dependency Injection Tests
# ==========================================

class TestRepositoryDependencyInjection:
    """Tests for Repository dependency injection functionality."""

    @pytest.mark.asyncio
    async def test_update_text_config_accepts_injected_repo(self, mock_config_repo):
        """update_text_model_config accepts and uses injected Repository."""
        # Arrange
        mock_config_repo.get_by_key.return_value = None
        mock_config_repo.create.return_value = True

        # Act
        result = await update_text_model_config(
            provider="openai",
            model="gpt-4",
            admin_id="admin-123",
            config_repo=mock_config_repo,  # ← Injected
        )

        # Assert
        assert result is not None
        # Verify injected repository was used
        assert mock_config_repo.get_by_key.called
        assert mock_config_repo.create.called or mock_config_repo.update.called

    @pytest.mark.asyncio
    async def test_update_image_config_accepts_injected_repo(self, mock_config_repo):
        """update_image_model_config accepts and uses injected Repository."""
        # Arrange
        mock_config_repo.get_by_key.return_value = None
        mock_config_repo.create.return_value = True

        # Act
        result = await update_image_model_config(
            tier="free",
            provider="fal",
            model="fal-ai/flux/schnell",
            admin_id="admin-123",
            config_repo=mock_config_repo,  # ← Injected
        )

        # Assert
        assert result is not None
        # Verify injected repository was used
        assert mock_config_repo.get_by_key.called
        assert mock_config_repo.create.called or mock_config_repo.update.called

    @pytest.mark.asyncio
    async def test_update_canary_config_accepts_injected_repo(self, mock_config_repo):
        """update_canary_config accepts and uses injected Repository."""
        # Arrange
        mock_config_repo.get_by_key.return_value = None
        mock_config_repo.create.return_value = True

        # Act
        result = await update_canary_config(
            enabled=True,
            percentage=10,
            target_model="gpt-4",
            admin_id="admin-123",
            config_repo=mock_config_repo,  # ← Injected
        )

        # Assert
        assert result is not None
        # Verify injected repository was used
        assert mock_config_repo.get_by_key.called
        assert mock_config_repo.create.called or mock_config_repo.update.called

    @pytest.mark.asyncio
    async def test_toggle_provider_accepts_injected_repo(self, mock_config_repo):
        """toggle_ai_provider accepts and uses injected Repository."""
        # Arrange
        existing_providers_json = json.dumps({"openai": True, "anthropic": False})
        mock_config_repo.get_by_key.return_value = existing_providers_json
        mock_config_repo.update.return_value = True

        # Act
        result = await toggle_ai_provider(
            provider="anthropic",
            enabled=True,
            admin_id="admin-123",
            config_repo=mock_config_repo,  # ← Injected
        )

        # Assert
        assert result is not None
        # Verify injected repository was used
        assert mock_config_repo.get_by_key.called
        assert mock_config_repo.update.called

    @pytest.mark.asyncio
    async def test_update_text_config_uses_default_repo_when_none_provided(self):
        """update_text_model_config uses default Repository when none provided."""
        with patch("core.database.get_async_db_client") as mock_get_db:
            with patch("infrastructure.repositories.config_repository.SupabaseConfigRepository") as MockRepo:
                # Arrange
                mock_db = MagicMock()
                # get_async_db_client is async, so we need to make it return a coroutine
                async def mock_get_db_func(*args, **kwargs):
                    return mock_db
                mock_get_db.side_effect = mock_get_db_func

                mock_repo_instance = AsyncMock()
                mock_repo_instance.get_by_key.return_value = None
                mock_repo_instance.create.return_value = True
                MockRepo.return_value = mock_repo_instance

                # Act - No config_repo parameter
                result = await update_text_model_config(
                    provider="openai",
                    model="gpt-4",
                    admin_id="admin-123",
                    # ← No config_repo, should use factory
                )

                # Assert - Factory created default repository
                MockRepo.assert_called_once_with(mock_db)
                assert result is not None

    @pytest.mark.asyncio
    async def test_update_image_config_uses_injected_repo_over_default(self, mock_config_repo):
        """update_image_model_config uses injected Repository instead of default."""
        # Arrange
        mock_config_repo.get_by_key.return_value = None
        mock_config_repo.create.return_value = True

        with patch("infrastructure.repositories.config_repository.SupabaseConfigRepository") as MockRepo:
            # Act - Provide config_repo
            result = await update_image_model_config(
                tier="free",
                provider="fal",
                model="fal-ai/flux/schnell",
                admin_id="admin-123",
                config_repo=mock_config_repo,  # ← Injected
            )

            # Assert - Default repository was NOT created
            MockRepo.assert_not_called()
            # Injected repository was used
            assert mock_config_repo.create.called or mock_config_repo.update.called


# ==========================================
# Backward Compatibility Tests
# ==========================================

class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with existing API calls."""

    @pytest.mark.asyncio
    async def test_all_functions_accept_optional_config_repo(self):
        """All write functions accept optional config_repo parameter."""
        with patch("core.database.get_async_db_client") as mock_get_db:
            with patch("infrastructure.repositories.config_repository.SupabaseConfigRepository") as MockRepo:
                mock_db = MagicMock()
                async def mock_get_db_func(*args, **kwargs):
                    return mock_db
                mock_get_db.side_effect = mock_get_db_func

                mock_repo_instance = AsyncMock()
                mock_repo_instance.get_by_key.return_value = None
                mock_repo_instance.create.return_value = True
                mock_repo_instance.update.return_value = True
                MockRepo.return_value = mock_repo_instance

                # Act - Call all functions without config_repo (backward compatible)
                result1 = await update_text_model_config(
                    provider="openai",
                    admin_id="admin-123"
                )

                result2 = await update_image_model_config(
                    tier="free",
                    provider="fal",
                    admin_id="admin-123"
                )

                result3 = await update_canary_config(
                    enabled=True,
                    percentage=10,
                    target_model="gpt-4",
                    admin_id="admin-123"
                )

                # Mock for toggle_ai_provider
                mock_repo_instance.get_by_key.return_value = json.dumps({"openai": True})
                result4 = await toggle_ai_provider(
                    provider="anthropic",
                    enabled=True,
                    admin_id="admin-123"
                )

                # Assert - All calls should work without config_repo
                assert result1 is not None
                assert result2 is not None
                assert result3 is not None
                assert result4 is not None


# ==========================================
# Integration Tests (Factory Functions)
# ==========================================

class TestFactoryFunctions:
    """Tests for Repository factory functions."""

    @pytest.mark.asyncio
    async def test_factory_creates_repository_with_correct_client(self):
        """Factory function creates Repository with correct database client."""
        with patch("core.database.get_async_db_client") as mock_get_db:
            with patch("infrastructure.repositories.config_repository.SupabaseConfigRepository") as MockRepo:
                # Arrange
                mock_db = MagicMock()
                async def mock_get_db_func(*args, **kwargs):
                    return mock_db
                mock_get_db.side_effect = mock_get_db_func

                mock_repo_instance = AsyncMock()
                mock_repo_instance.get_by_key.return_value = None
                mock_repo_instance.create.return_value = True
                MockRepo.return_value = mock_repo_instance

                # Act - Call without config_repo to trigger factory
                result = await update_text_model_config(
                    provider="openai",
                    admin_id="admin-123"
                )

                # Assert - Factory used correct database client
                mock_get_db.assert_called()
                MockRepo.assert_called_with(mock_db)
                assert result is not None

    @pytest.mark.asyncio
    async def test_injected_repo_bypasses_factory(self, mock_config_repo):
        """Injected Repository bypasses factory function for config operations."""
        # Arrange
        mock_config_repo.get_by_key.return_value = None
        mock_config_repo.create.return_value = True

        with patch("infrastructure.repositories.config_repository.SupabaseConfigRepository") as MockRepo:
            # Act - Provide config_repo
            result = await update_text_model_config(
                provider="openai",
                admin_id="admin-123",
                config_repo=mock_config_repo,  # ← Injected
            )

            # Assert - Factory Repository was NOT created
            MockRepo.assert_not_called()
            # Injected repo was used
            assert mock_config_repo.get_by_key.called
            assert result is not None

            # Note: get_database_client() is still called for audit logging
            # This is expected behavior - audit logs use separate DB client

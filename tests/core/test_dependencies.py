"""
Tests for core/dependencies.py - UserWithWorkspace and get_current_user_with_workspace

@module tests.core.test_dependencies
@version 1.0.0 (v3.33 Workspace + Tag Phase 2.5)

Tests:
- UserWithWorkspace dataclass
- get_current_user_with_workspace dependency
- Automatic workspace creation on first access
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass


# ==========================================
# Test UserWithWorkspace dataclass
# ==========================================

class TestUserWithWorkspace:
    """Tests for UserWithWorkspace dataclass"""

    def test_user_with_workspace_creation(self):
        """Test that UserWithWorkspace can be created with user and workspace_id"""
        from dependencies import UserWithWorkspace

        # Create mock user
        mock_user = MagicMock()
        mock_user.user_id = "user_123"

        # Create UserWithWorkspace
        ctx = UserWithWorkspace(user=mock_user, workspace_id="ws_456")

        assert ctx.user == mock_user
        assert ctx.workspace_id == "ws_456"

    def test_user_id_property(self):
        """Test that user_id property returns the user's user_id"""
        from dependencies import UserWithWorkspace

        mock_user = MagicMock()
        mock_user.user_id = "user_abc123"

        ctx = UserWithWorkspace(user=mock_user, workspace_id="ws_xyz")

        assert ctx.user_id == "user_abc123"


# ==========================================
# Test get_current_user_with_workspace dependency
# ==========================================

class TestGetCurrentUserWithWorkspace:
    """Tests for get_current_user_with_workspace dependency"""

    @pytest.fixture
    def mock_user(self):
        """Create a mock UserProfile"""
        user = MagicMock()
        user.user_id = "user_test_123"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_workspace(self):
        """Create a mock Workspace"""
        workspace = MagicMock()
        workspace.id = "ws_default_456"
        workspace.name = "Default Workspace"
        workspace.owner_id = "user_test_123"
        return workspace

    @pytest.mark.asyncio
    async def test_returns_user_with_workspace(self, mock_user, mock_workspace):
        """Test that dependency returns UserWithWorkspace with correct values"""
        from dependencies import get_current_user_with_workspace, UserWithWorkspace

        # Mock container and workspace_service
        mock_workspace_service = AsyncMock()
        mock_workspace_service.get_or_create_default.return_value = mock_workspace

        mock_container = MagicMock()
        mock_container.get_workspace_service = AsyncMock(return_value=mock_workspace_service)

        # Patch container module's get_container function
        with patch('container.get_container', return_value=mock_container):
            result = await get_current_user_with_workspace(user=mock_user)

        assert isinstance(result, UserWithWorkspace)
        assert result.user == mock_user
        assert result.workspace_id == mock_workspace.id
        assert result.user_id == mock_user.user_id

    @pytest.mark.asyncio
    async def test_calls_get_or_create_default(self, mock_user, mock_workspace):
        """Test that dependency calls workspace_service.get_or_create_default"""
        from dependencies import get_current_user_with_workspace

        mock_workspace_service = AsyncMock()
        mock_workspace_service.get_or_create_default.return_value = mock_workspace

        mock_container = MagicMock()
        mock_container.get_workspace_service = AsyncMock(return_value=mock_workspace_service)

        with patch('container.get_container', return_value=mock_container):
            await get_current_user_with_workspace(user=mock_user)

        # Verify get_or_create_default was called with user_id
        mock_workspace_service.get_or_create_default.assert_called_once_with(mock_user.user_id)

    @pytest.mark.asyncio
    async def test_workspace_created_on_first_access(self, mock_user):
        """Test that workspace is created automatically on first access"""
        from dependencies import get_current_user_with_workspace

        # Mock the workspace that will be created
        new_workspace = MagicMock()
        new_workspace.id = "ws_newly_created"

        mock_workspace_service = AsyncMock()
        mock_workspace_service.get_or_create_default.return_value = new_workspace

        mock_container = MagicMock()
        mock_container.get_workspace_service = AsyncMock(return_value=mock_workspace_service)

        with patch('container.get_container', return_value=mock_container):
            result = await get_current_user_with_workspace(user=mock_user)

        assert result.workspace_id == "ws_newly_created"

    @pytest.mark.asyncio
    async def test_idempotent_workspace_creation(self, mock_user, mock_workspace):
        """Test that calling multiple times returns same workspace"""
        from dependencies import get_current_user_with_workspace

        mock_workspace_service = AsyncMock()
        mock_workspace_service.get_or_create_default.return_value = mock_workspace

        mock_container = MagicMock()
        mock_container.get_workspace_service = AsyncMock(return_value=mock_workspace_service)

        with patch('container.get_container', return_value=mock_container):
            result1 = await get_current_user_with_workspace(user=mock_user)
            result2 = await get_current_user_with_workspace(user=mock_user)

        assert result1.workspace_id == result2.workspace_id
        assert result1.workspace_id == mock_workspace.id


# ==========================================
# Integration tests with real Container (optional)
# ==========================================

class TestGetCurrentUserWithWorkspaceIntegration:
    """Integration tests that verify the full chain"""

    @pytest.mark.skip(reason="Requires database connection")
    @pytest.mark.asyncio
    async def test_full_chain_creates_workspace(self):
        """
        Integration test that verifies:
        1. get_current_user_with_workspace is called
        2. WorkspaceService.get_or_create_default is called
        3. A real workspace is created/returned
        """
        # This test would require actual database setup
        pass

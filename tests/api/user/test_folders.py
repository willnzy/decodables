"""
Tests for Folders API endpoints.

@module tests.api.user.test_folders
@version 1.0.0 (v3.33 Workspace + Tag Phase 2.6)

Tests:
- GET /api/v2/user/folders - List folders
- POST /api/v2/user/folders - Create folder
- PATCH /api/v2/user/folders/{folder_id} - Update folder
- DELETE /api/v2/user/folders/{folder_id} - Delete folder
- POST /api/v2/user/folders/reorder - Reorder folders
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException


# ==========================================
# Test List Folders
# ==========================================

class TestListFolders:
    """Tests for GET /api/v2/user/folders"""

    @pytest.mark.asyncio
    async def test_list_folders_success(self):
        """Test successful folder listing."""
        from domains.folder.entities import Folder, FolderType, FolderColor

        mock_folders = [
            Folder(id="f1", workspace_id="ws_123", folder_type=FolderType.PROJECT,
                   name="Folder A", color=FolderColor.BLUE, sort_order=0, created_by="user"),
            Folder(id="f2", workspace_id="ws_123", folder_type=FolderType.PROJECT,
                   name="Folder B", color=FolderColor.RED, sort_order=1, created_by="user"),
        ]

        mock_folder_service = AsyncMock()
        mock_folder_service.list_folders.return_value = mock_folders

        mock_container = MagicMock()
        mock_container.get_folder_service = AsyncMock(return_value=mock_folder_service)

        with patch('api.user.folders.get_container', return_value=mock_container):
            from api.user.folders import list_folders

            # Create mock request and context
            mock_request = MagicMock()
            mock_ctx = MagicMock()
            mock_ctx.workspace_id = "ws_123"

            result = await list_folders.__wrapped__(
                request=mock_request,
                folder_type="project",
                ctx=mock_ctx,
            )

        assert result["total"] == 2
        assert len(result["items"]) == 2
        mock_folder_service.list_folders.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_folders_empty(self):
        """Test listing folders when none exist."""
        mock_folder_service = AsyncMock()
        mock_folder_service.list_folders.return_value = []

        mock_container = MagicMock()
        mock_container.get_folder_service = AsyncMock(return_value=mock_folder_service)

        with patch('api.user.folders.get_container', return_value=mock_container):
            from api.user.folders import list_folders

            mock_request = MagicMock()
            mock_ctx = MagicMock()
            mock_ctx.workspace_id = "ws_123"

            result = await list_folders.__wrapped__(
                request=mock_request,
                folder_type="asset",
                ctx=mock_ctx,
            )

        assert result["total"] == 0
        assert result["items"] == []


# ==========================================
# Test Create Folder
# ==========================================

class TestCreateFolder:
    """Tests for POST /api/v2/user/folders"""

    @pytest.mark.asyncio
    async def test_create_folder_success(self):
        """Test successful folder creation."""
        from domains.folder.entities import Folder, FolderType, FolderColor

        created_folder = Folder(
            id="new_folder_id",
            workspace_id="ws_123",
            folder_type=FolderType.PROJECT,
            name="My New Folder",
            color=FolderColor.EMERALD,
            sort_order=0,
            created_by="user_456",
        )

        mock_folder_service = AsyncMock()
        mock_folder_service.create_folder.return_value = created_folder

        mock_container = MagicMock()
        mock_container.get_folder_service = AsyncMock(return_value=mock_folder_service)

        with patch('api.user.folders.get_container', return_value=mock_container):
            from api.user.folders import create_folder, CreateFolderRequest

            mock_request = MagicMock()
            mock_ctx = MagicMock()
            mock_ctx.workspace_id = "ws_123"
            mock_ctx.user_id = "user_456"

            data = CreateFolderRequest(
                folder_type="project",
                name="My New Folder",
                color="emerald",
            )

            result = await create_folder.__wrapped__(
                request=mock_request,
                data=data,
                ctx=mock_ctx,
            )

        assert result["id"] == "new_folder_id"
        assert result["name"] == "My New Folder"
        assert result["color"] == "emerald"

    @pytest.mark.asyncio
    async def test_create_folder_duplicate_name(self):
        """Test creating folder with duplicate name fails."""
        mock_folder_service = AsyncMock()
        mock_folder_service.create_folder.side_effect = ValueError("Folder already exists")

        mock_container = MagicMock()
        mock_container.get_folder_service = AsyncMock(return_value=mock_folder_service)

        with patch('api.user.folders.get_container', return_value=mock_container):
            from api.user.folders import create_folder, CreateFolderRequest

            mock_request = MagicMock()
            mock_ctx = MagicMock()
            mock_ctx.workspace_id = "ws_123"
            mock_ctx.user_id = "user_456"

            data = CreateFolderRequest(
                folder_type="project",
                name="Existing Folder",
                color="slate",
            )

            with pytest.raises(HTTPException) as exc_info:
                await create_folder.__wrapped__(
                    request=mock_request,
                    data=data,
                    ctx=mock_ctx,
                )

            assert exc_info.value.status_code == 400


# ==========================================
# Test Update Folder
# ==========================================

class TestUpdateFolder:
    """Tests for PATCH /api/v2/user/folders/{folder_id}"""

    @pytest.mark.asyncio
    async def test_update_folder_success(self):
        """Test successful folder update."""
        from domains.folder.entities import Folder, FolderType, FolderColor

        updated_folder = Folder(
            id="folder_id",
            workspace_id="ws_123",
            folder_type=FolderType.PROJECT,
            name="Updated Name",
            color=FolderColor.VIOLET,
            sort_order=0,
            created_by="user",
        )

        mock_folder_service = AsyncMock()
        mock_folder_service.validate_folder_access.return_value = True
        mock_folder_service.update_folder.return_value = updated_folder

        mock_container = MagicMock()
        mock_container.get_folder_service = AsyncMock(return_value=mock_folder_service)

        with patch('api.user.folders.get_container', return_value=mock_container):
            from api.user.folders import update_folder, UpdateFolderRequest

            mock_request = MagicMock()
            mock_ctx = MagicMock()
            mock_ctx.workspace_id = "ws_123"
            mock_ctx.user_id = "user_456"

            data = UpdateFolderRequest(
                name="Updated Name",
                color="violet",
            )

            result = await update_folder.__wrapped__(
                request=mock_request,
                folder_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                data=data,
                ctx=mock_ctx,
            )

        assert result["name"] == "Updated Name"
        assert result["color"] == "violet"

    @pytest.mark.asyncio
    async def test_update_folder_not_found(self):
        """Test updating non-existent folder."""
        mock_folder_service = AsyncMock()
        mock_folder_service.validate_folder_access.return_value = False

        mock_container = MagicMock()
        mock_container.get_folder_service = AsyncMock(return_value=mock_folder_service)

        with patch('api.user.folders.get_container', return_value=mock_container):
            from api.user.folders import update_folder, UpdateFolderRequest

            mock_request = MagicMock()
            mock_ctx = MagicMock()
            mock_ctx.workspace_id = "ws_123"
            mock_ctx.user_id = "user_456"

            data = UpdateFolderRequest(name="New Name")

            with pytest.raises(HTTPException) as exc_info:
                await update_folder.__wrapped__(
                    request=mock_request,
                    folder_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    data=data,
                    ctx=mock_ctx,
                )

            assert exc_info.value.status_code == 404


# ==========================================
# Test Delete Folder
# ==========================================

class TestDeleteFolder:
    """Tests for DELETE /api/v2/user/folders/{folder_id}"""

    @pytest.mark.asyncio
    async def test_delete_folder_success(self):
        """Test successful folder deletion."""
        from domains.folder.entities import Folder, FolderType, FolderColor

        mock_folder = Folder(
            id="folder_id",
            workspace_id="ws_123",
            folder_type=FolderType.PROJECT,
            name="To Delete",
            color=FolderColor.SLATE,
            sort_order=0,
            created_by="user",
        )

        mock_folder_service = AsyncMock()
        mock_folder_service.validate_folder_access.return_value = True
        mock_folder_service.get_folder.return_value = mock_folder
        mock_folder_service.delete_folder.return_value = True

        mock_container = MagicMock()
        mock_container.get_folder_service = AsyncMock(return_value=mock_folder_service)

        with patch('api.user.folders.get_container', return_value=mock_container):
            from api.user.folders import delete_folder

            mock_request = MagicMock()
            mock_ctx = MagicMock()
            mock_ctx.workspace_id = "ws_123"
            mock_ctx.user_id = "user_456"

            result = await delete_folder.__wrapped__(
                request=mock_request,
                folder_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                ctx=mock_ctx,
            )

        assert result["success"] is True
        mock_folder_service.delete_folder.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_folder_not_found(self):
        """Test deleting non-existent folder."""
        mock_folder_service = AsyncMock()
        mock_folder_service.validate_folder_access.return_value = False

        mock_container = MagicMock()
        mock_container.get_folder_service = AsyncMock(return_value=mock_folder_service)

        with patch('api.user.folders.get_container', return_value=mock_container):
            from api.user.folders import delete_folder

            mock_request = MagicMock()
            mock_ctx = MagicMock()
            mock_ctx.workspace_id = "ws_123"
            mock_ctx.user_id = "user_456"

            with pytest.raises(HTTPException) as exc_info:
                await delete_folder.__wrapped__(
                    request=mock_request,
                    folder_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    ctx=mock_ctx,
                )

            assert exc_info.value.status_code == 404


# ==========================================
# Test Reorder Folders
# ==========================================

class TestReorderFolders:
    """Tests for POST /api/v2/user/folders/reorder"""

    @pytest.mark.asyncio
    async def test_reorder_folders_success(self):
        """Test successful folder reordering."""
        mock_folder_service = AsyncMock()
        mock_folder_service.validate_folder_access.return_value = True
        mock_folder_service.reorder_folders.return_value = True

        mock_container = MagicMock()
        mock_container.get_folder_service = AsyncMock(return_value=mock_folder_service)

        with patch('api.user.folders.get_container', return_value=mock_container):
            from api.user.folders import reorder_folders, ReorderFoldersRequest

            mock_request = MagicMock()
            mock_ctx = MagicMock()
            mock_ctx.workspace_id = "ws_123"
            mock_ctx.user_id = "user_456"

            data = ReorderFoldersRequest(
                folder_type="project",
                folder_ids=[
                    "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                ],
            )

            result = await reorder_folders.__wrapped__(
                request=mock_request,
                data=data,
                ctx=mock_ctx,
            )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_reorder_folders_invalid_folder(self):
        """Test reordering with invalid folder ID."""
        mock_folder_service = AsyncMock()
        mock_folder_service.validate_folder_access.side_effect = [True, False]  # First OK, second invalid

        mock_container = MagicMock()
        mock_container.get_folder_service = AsyncMock(return_value=mock_folder_service)

        with patch('api.user.folders.get_container', return_value=mock_container):
            from api.user.folders import reorder_folders, ReorderFoldersRequest

            mock_request = MagicMock()
            mock_ctx = MagicMock()
            mock_ctx.workspace_id = "ws_123"
            mock_ctx.user_id = "user_456"

            data = ReorderFoldersRequest(
                folder_type="project",
                folder_ids=[
                    "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                ],
            )

            with pytest.raises(HTTPException) as exc_info:
                await reorder_folders.__wrapped__(
                    request=mock_request,
                    data=data,
                    ctx=mock_ctx,
                )

            assert exc_info.value.status_code == 400


# ==========================================
# Test Request Validation
# ==========================================

class TestRequestValidation:
    """Tests for request model validation"""

    def test_create_folder_request_valid_types(self):
        """Test CreateFolderRequest accepts valid folder types."""
        from api.user.folders import CreateFolderRequest

        req = CreateFolderRequest(
            folder_type="project",
            name="Test",
        )
        assert req.folder_type == "project"

        req = CreateFolderRequest(
            folder_type="asset",
            name="Test",
        )
        assert req.folder_type == "asset"

    def test_create_folder_request_valid_colors(self):
        """Test CreateFolderRequest accepts valid colors."""
        from api.user.folders import CreateFolderRequest

        colors = ["slate", "red", "orange", "amber", "emerald", "cyan", "blue", "violet"]
        for color in colors:
            req = CreateFolderRequest(
                folder_type="project",
                name="Test",
                color=color,
            )
            assert req.color == color

    def test_create_folder_request_name_length(self):
        """Test CreateFolderRequest name length validation."""
        from api.user.folders import CreateFolderRequest
        from pydantic import ValidationError

        # Valid: 1-100 characters
        req = CreateFolderRequest(
            folder_type="project",
            name="A",  # 1 char
        )
        assert req.name == "A"

        req = CreateFolderRequest(
            folder_type="project",
            name="A" * 100,  # 100 chars
        )
        assert len(req.name) == 100

        # Invalid: empty
        with pytest.raises(ValidationError):
            CreateFolderRequest(
                folder_type="project",
                name="",
            )

        # Invalid: too long
        with pytest.raises(ValidationError):
            CreateFolderRequest(
                folder_type="project",
                name="A" * 101,
            )

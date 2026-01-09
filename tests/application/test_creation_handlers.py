"""
Creation Handler Tests - Command and Query handlers for projects.

@module tests.application.test_creation_handlers
@version 1.0.0

Tests cover:
- CreateProjectHandler
- UpdateProjectHandler
- DeleteProjectHandler
- GetProjectHandler
- GetUserProjectsHandler
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone

from domains.creation import (
    Project,
    ProjectStatus,
    CreationService,
)


class TestCreateProjectHandler:
    """Tests for CreateProjectHandler."""

    @pytest.fixture
    def mock_creation_service(self):
        """Create mock creation service."""
        service = MagicMock(spec=CreationService)
        service.create_project = AsyncMock()
        return service

    @pytest.fixture
    def handler(self, mock_creation_service):
        """Create handler with mock service."""
        from application.commands.creation import CreateProjectHandler
        return CreateProjectHandler(mock_creation_service)

    @pytest.mark.asyncio
    async def test_create_project_success(self, handler, mock_creation_service):
        """Test successful project creation."""
        from application.commands.creation import CreateProjectCommand
        from domains.creation import ProjectMetadata, CanvasSize, ProjectStatus

        # Mock Project entity with new DDD structure
        mock_project = MagicMock(spec=Project)
        mock_project.project_id = "proj_new"
        mock_project.owner_id = "user_123"
        mock_project.metadata = ProjectMetadata(title="New Project")
        mock_project.canvas_size = CanvasSize(1080, 1080)
        mock_project.status = ProjectStatus.DRAFT
        mock_project.to_dict.return_value = {
            "project_id": "proj_new",
            "owner_id": "user_123",
            "title": "New Project",
        }

        mock_creation_service.create_project.return_value = mock_project

        command = CreateProjectCommand(
            user_id="user_123",
            title="New Project",
            tier="starter",
        )

        result = await handler.handle(command)

        assert result.success is True
        assert result.project == mock_project
        assert result.project_dict["title"] == "New Project"
        mock_creation_service.create_project.assert_called_once_with(
            owner_id="user_123",
            title="New Project",
            canvas_size=None,
            user_tier="starter",
        )

    @pytest.mark.asyncio
    async def test_create_project_limit_exceeded(self, handler, mock_creation_service):
        """Test project creation when limit exceeded."""
        from application.commands.creation import CreateProjectCommand
        from domains.creation import ProjectLimitExceededException

        mock_creation_service.create_project.side_effect = ProjectLimitExceededException(
            owner_id="user_123",
            limit=5,
        )

        command = CreateProjectCommand(
            user_id="user_123",
            title="Another Project",
            tier="free",
        )

        result = await handler.handle(command)

        assert result.success is False
        assert "limit" in result.error.lower() or "exceeded" in result.error.lower()


class TestUpdateProjectHandler:
    """Tests for UpdateProjectHandler."""

    @pytest.fixture
    def mock_creation_service(self):
        """Create mock creation service."""
        service = MagicMock(spec=CreationService)
        service.get_project_with_access = AsyncMock()
        service._repository = MagicMock()
        service._repository.update = AsyncMock()
        return service

    @pytest.fixture
    def handler(self, mock_creation_service):
        """Create handler with mock service."""
        from application.commands.creation import UpdateProjectHandler
        return UpdateProjectHandler(mock_creation_service)

    @pytest.mark.asyncio
    async def test_update_project_success(self, handler, mock_creation_service):
        """Test successful project update."""
        from application.commands.creation import UpdateProjectCommand
        from domains.creation import ProjectMetadata, CanvasSize

        # Mock existing project
        mock_project = MagicMock(spec=Project)
        mock_project.project_id = "proj_123"
        mock_project.owner_id = "user_456"
        mock_project.metadata = ProjectMetadata(title="Old Title")
        mock_project.canvas_size = CanvasSize(1080, 1080)

        mock_creation_service.get_project_with_access.return_value = mock_project

        command = UpdateProjectCommand(
            project_id="proj_123",
            user_id="user_456",
            title="Updated Title",
        )

        result = await handler.handle(command)

        assert result.success is True
        assert result.project == mock_project
        mock_project.update_metadata.assert_called_once_with(title="Updated Title")
        mock_creation_service._repository.update.assert_called_once_with(mock_project)

    @pytest.mark.asyncio
    async def test_update_project_not_owner(self, handler, mock_creation_service):
        """Test update by non-owner fails."""
        from application.commands.creation import UpdateProjectCommand
        from domains.creation import ProjectAccessDeniedException

        mock_creation_service.get_project_with_access.side_effect = ProjectAccessDeniedException(
            project_id="proj_123",
            user_id="other_user",
        )

        command = UpdateProjectCommand(
            project_id="proj_123",
            user_id="other_user",
            title="Hacked Title",
        )

        result = await handler.handle(command)

        assert result.success is False
        assert "access" in result.error.lower() or "denied" in result.error.lower()


class TestDeleteProjectHandler:
    """Tests for DeleteProjectHandler."""

    @pytest.fixture
    def mock_creation_service(self):
        """Create mock creation service."""
        service = MagicMock(spec=CreationService)
        service.delete_project = AsyncMock()
        return service

    @pytest.fixture
    def handler(self, mock_creation_service):
        """Create handler with mock service."""
        from application.commands.creation import DeleteProjectHandler
        return DeleteProjectHandler(mock_creation_service)

    @pytest.mark.asyncio
    async def test_delete_project_success(self, handler, mock_creation_service):
        """Test successful project deletion (soft delete)."""
        from application.commands.creation import DeleteProjectCommand

        mock_creation_service.delete_project.return_value = True

        command = DeleteProjectCommand(
            project_id="proj_123",
            user_id="user_456",
            permanent=False,
        )

        result = await handler.handle(command)

        assert result.success is True
        mock_creation_service.delete_project.assert_called_once_with(
            project_id="proj_123",
            user_id="user_456",
            hard_delete=False,
        )

    @pytest.mark.asyncio
    async def test_delete_project_permanent(self, handler, mock_creation_service):
        """Test permanent project deletion (hard delete)."""
        from application.commands.creation import DeleteProjectCommand

        mock_creation_service.delete_project.return_value = True

        command = DeleteProjectCommand(
            project_id="proj_123",
            user_id="user_456",
            permanent=True,
        )

        result = await handler.handle(command)

        assert result.success is True
        mock_creation_service.delete_project.assert_called_once_with(
            project_id="proj_123",
            user_id="user_456",
            hard_delete=True,
        )


class TestGetProjectHandler:
    """Tests for GetProjectHandler."""

    @pytest.fixture
    def mock_creation_service(self):
        """Create mock creation service."""
        service = MagicMock(spec=CreationService)
        service.get_project_with_access = AsyncMock()
        return service

    @pytest.fixture
    def handler(self, mock_creation_service):
        """Create handler with mock service."""
        from application.queries.creation import GetProjectHandler
        return GetProjectHandler(mock_creation_service)

    @pytest.mark.asyncio
    async def test_get_project_success(self, handler, mock_creation_service):
        """Test getting project successfully."""
        from application.queries.creation import GetProjectQuery
        from domains.creation import ProjectMetadata, CanvasSize

        # Mock Project entity
        mock_project = MagicMock(spec=Project)
        mock_project.project_id = "proj_123"
        mock_project.owner_id = "user_456"
        mock_project.metadata = ProjectMetadata(title="My Project")
        mock_project.canvas_size = CanvasSize(1080, 1080)
        mock_project.to_dict.return_value = {
            "project_id": "proj_123",
            "owner_id": "user_456",
            "title": "My Project",
            "canvas_data": {"objects": []},
        }

        mock_creation_service.get_project_with_access.return_value = mock_project

        query = GetProjectQuery(
            project_id="proj_123",
            user_id="user_456",
        )

        result = await handler.handle(query)

        assert result.success is True
        assert result.project == mock_project
        assert result.project_dict is not None
        assert result.project_dict["title"] == "My Project"

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, handler, mock_creation_service):
        """Test getting non-existent project."""
        from application.queries.creation import GetProjectQuery
        from domains.creation import ProjectNotFoundException

        mock_creation_service.get_project_with_access.side_effect = ProjectNotFoundException("proj_999")

        query = GetProjectQuery(
            project_id="proj_999",
            user_id="user_456",
        )

        result = await handler.handle(query)

        assert result.success is False
        assert "not found" in result.error.lower() or "proj_999" in result.error.lower()


class TestGetUserProjectsHandler:
    """Tests for GetUserProjectsHandler."""

    @pytest.fixture
    def mock_creation_service(self):
        """Create mock creation service."""
        service = MagicMock(spec=CreationService)
        service.get_user_projects = AsyncMock()
        service.count_user_projects = AsyncMock()
        return service

    @pytest.fixture
    def handler(self, mock_creation_service):
        """Create handler with mock service."""
        from application.queries.creation import GetUserProjectsHandler
        return GetUserProjectsHandler(mock_creation_service)

    @pytest.mark.asyncio
    async def test_get_user_projects(self, handler, mock_creation_service):
        """Test getting user's projects."""
        from application.queries.creation import GetUserProjectsQuery
        from domains.creation import ProjectMetadata, CanvasSize

        # Mock multiple projects
        mock_projects = []
        for i in range(1, 4):
            mock_project = MagicMock(spec=Project)
            mock_project.project_id = f"p{i}"
            mock_project.owner_id = "user_123"
            mock_project.metadata = ProjectMetadata(title=f"Project {i}")
            mock_project.canvas_size = CanvasSize(1080, 1080)
            mock_project.to_dict.return_value = {
                "project_id": f"p{i}",
                "owner_id": "user_123",
                "title": f"Project {i}",
            }
            mock_projects.append(mock_project)

        mock_creation_service.get_user_projects.return_value = mock_projects
        mock_creation_service.count_user_projects.return_value = 3

        query = GetUserProjectsQuery(
            user_id="user_123",
            limit=50,
            offset=0,
        )

        result = await handler.handle(query)

        assert result.success is True
        assert len(result.projects) == 3
        assert len(result.projects_list) == 3
        assert result.total_count == 3

    @pytest.mark.asyncio
    async def test_get_user_projects_filtered(self, handler, mock_creation_service):
        """Test getting user's projects with status filter."""
        from application.queries.creation import GetUserProjectsQuery
        from domains.creation import ProjectMetadata, CanvasSize, ProjectStatus

        # Mock single active project
        mock_project = MagicMock(spec=Project)
        mock_project.project_id = "p1"
        mock_project.owner_id = "user_123"
        mock_project.metadata = ProjectMetadata(title="Active Project")
        mock_project.canvas_size = CanvasSize(1080, 1080)
        mock_project.status = ProjectStatus.ACTIVE
        mock_project.to_dict.return_value = {
            "project_id": "p1",
            "owner_id": "user_123",
            "title": "Active Project",
            "status": "active",
        }

        mock_creation_service.get_user_projects.return_value = [mock_project]
        mock_creation_service.count_user_projects.return_value = 1

        query = GetUserProjectsQuery(
            user_id="user_123",
            status="active",
        )

        result = await handler.handle(query)

        assert result.success is True
        assert len(result.projects) == 1
        assert len(result.projects_list) == 1

    @pytest.mark.asyncio
    async def test_get_user_projects_empty(self, handler, mock_creation_service):
        """Test getting projects for user with none."""
        from application.queries.creation import GetUserProjectsQuery

        mock_creation_service.get_user_projects.return_value = []
        mock_creation_service.count_user_projects.return_value = 0

        query = GetUserProjectsQuery(user_id="new_user")

        result = await handler.handle(query)

        assert result.success is True
        assert len(result.projects) == 0
        assert len(result.projects_list) == 0
        assert result.total_count == 0

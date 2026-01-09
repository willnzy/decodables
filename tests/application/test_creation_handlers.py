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


@pytest.mark.skip(reason="Project entity DDD migration needed")
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

        mock_creation_service.create_project.return_value = MagicMock(
            success=True,
            project=Project(
                id="proj_new",
                user_id="user_123",
                title="New Project",
            ),
        )

        command = CreateProjectCommand(
            user_id="user_123",
            title="New Project",
            tier="starter",
        )

        result = await handler.handle(command)

        assert result.success is True
        assert result.project.title == "New Project"

    @pytest.mark.asyncio
    async def test_create_project_limit_exceeded(self, handler, mock_creation_service):
        """Test project creation when limit exceeded."""
        from application.commands.creation import CreateProjectCommand

        mock_creation_service.create_project.return_value = MagicMock(
            success=False,
            error="Project limit exceeded",
        )

        command = CreateProjectCommand(
            user_id="user_123",
            title="Another Project",
            tier="free",
        )

        result = await handler.handle(command)

        assert result.success is False
        assert "limit" in result.error.lower()


@pytest.mark.skip(reason="Project entity DDD migration needed")
class TestUpdateProjectHandler:
    """Tests for UpdateProjectHandler."""

    @pytest.fixture
    def mock_creation_service(self):
        """Create mock creation service."""
        service = MagicMock(spec=CreationService)
        service.update_project = AsyncMock()
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

        mock_creation_service.update_project.return_value = MagicMock(
            success=True,
            project=Project(
                id="proj_123",
                user_id="user_456",
                title="Updated Title",
            ),
        )

        command = UpdateProjectCommand(
            project_id="proj_123",
            user_id="user_456",
            title="Updated Title",
        )

        result = await handler.handle(command)

        assert result.success is True
        assert result.project.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_project_not_owner(self, handler, mock_creation_service):
        """Test update by non-owner fails."""
        from application.commands.creation import UpdateProjectCommand

        mock_creation_service.update_project.return_value = MagicMock(
            success=False,
            error="Access denied",
        )

        command = UpdateProjectCommand(
            project_id="proj_123",
            user_id="other_user",
            title="Hacked Title",
        )

        result = await handler.handle(command)

        assert result.success is False


@pytest.mark.skip(reason="Project entity DDD migration needed")
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
        """Test successful project deletion."""
        from application.commands.creation import DeleteProjectCommand

        mock_creation_service.delete_project.return_value = MagicMock(
            success=True,
        )

        command = DeleteProjectCommand(
            project_id="proj_123",
            user_id="user_456",
            permanent=False,
        )

        result = await handler.handle(command)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_delete_project_permanent(self, handler, mock_creation_service):
        """Test permanent project deletion."""
        from application.commands.creation import DeleteProjectCommand

        mock_creation_service.delete_project.return_value = MagicMock(
            success=True,
        )

        command = DeleteProjectCommand(
            project_id="proj_123",
            user_id="user_456",
            permanent=True,
        )

        result = await handler.handle(command)

        assert result.success is True
        mock_creation_service.delete_project.assert_called_once()


@pytest.mark.skip(reason="Project entity DDD migration needed")
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

        mock_creation_service.get_project_with_access.return_value = Project(
            id="proj_123",
            user_id="user_456",
            title="My Project",
            canvas_data={"objects": []},
        )

        query = GetProjectQuery(
            project_id="proj_123",
            user_id="user_456",
        )

        result = await handler.handle(query)

        assert result.success is True
        assert result.project.title == "My Project"
        assert result.project_dict is not None

    @pytest.mark.skip(reason="Project entity constructor needs DDD refactor")
    @pytest.mark.asyncio
    async def test_get_project_not_found(self, handler, mock_creation_service):
        """Test getting non-existent project."""
        from application.queries.creation import GetProjectQuery
        from domains.creation import ProjectNotFoundError

        mock_creation_service.get_project_with_access.side_effect = ProjectNotFoundError("proj_999")

        query = GetProjectQuery(
            project_id="proj_999",
            user_id="user_456",
        )

        result = await handler.handle(query)

        assert result.success is False
        assert "not found" in result.error.lower()


@pytest.mark.skip(reason="Project entity DDD migration needed")
class TestGetUserProjectsHandler:
    """Tests for GetUserProjectsHandler."""

    @pytest.fixture
    def mock_creation_service(self):
        """Create mock creation service."""
        service = MagicMock(spec=CreationService)
        service.get_user_projects = AsyncMock()
        return service

    @pytest.fixture
    def handler(self, mock_creation_service):
        """Create handler with mock service."""
        from application.queries.creation import GetUserProjectsHandler
        return GetUserProjectsHandler(mock_creation_service)

    @pytest.mark.skip(reason="Project entity constructor needs DDD refactor")
    @pytest.mark.asyncio
    async def test_get_user_projects(self, handler, mock_creation_service):
        """Test getting user's projects."""
        from application.queries.creation import GetUserProjectsQuery

        mock_creation_service.get_user_projects.return_value = [
            Project(id="p1", user_id="user_123", title="Project 1"),
            Project(id="p2", user_id="user_123", title="Project 2"),
            Project(id="p3", user_id="user_123", title="Project 3"),
        ]

        query = GetUserProjectsQuery(
            user_id="user_123",
            limit=50,
            offset=0,
        )

        result = await handler.handle(query)

        assert result.success is True
        assert len(result.projects) == 3
        assert result.total_count == 3

    @pytest.mark.asyncio
    async def test_get_user_projects_filtered(self, handler, mock_creation_service):
        """Test getting user's projects with status filter."""
        from application.queries.creation import GetUserProjectsQuery

        mock_creation_service.get_user_projects.return_value = [
            Project(
                id="p1",
                user_id="user_123",
                title="Active Project",
                status=ProjectStatus.ACTIVE,
            ),
        ]

        query = GetUserProjectsQuery(
            user_id="user_123",
            status="active",
        )

        result = await handler.handle(query)

        assert result.success is True
        assert len(result.projects) == 1

    @pytest.mark.asyncio
    async def test_get_user_projects_empty(self, handler, mock_creation_service):
        """Test getting projects for user with none."""
        from application.queries.creation import GetUserProjectsQuery

        mock_creation_service.get_user_projects.return_value = []

        query = GetUserProjectsQuery(user_id="new_user")

        result = await handler.handle(query)

        assert result.success is True
        assert len(result.projects) == 0
        assert result.total_count == 0

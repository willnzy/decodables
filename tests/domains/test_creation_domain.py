"""
Creation Domain Tests - Project aggregate and project management.

@module tests.domains.test_creation_domain
@version 1.0.0

Tests cover:
- Project aggregate creation and operations
- Project status transitions
- Project limit enforcement
- Soft delete and restore
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

from domains.creation import (
    Project,
    ProjectStatus,
    ProjectLimitExceededException,
    ProjectNotFoundException,
    ProjectAccessDeniedException,
)


class TestProjectStatus:
    """Tests for ProjectStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert ProjectStatus.ACTIVE.value == "active"
        assert ProjectStatus.DELETED.value == "deleted"
        assert ProjectStatus.ARCHIVED.value == "archived"

    def test_status_from_string(self):
        """Test creating status from string."""
        assert ProjectStatus("active") == ProjectStatus.ACTIVE
        assert ProjectStatus("deleted") == ProjectStatus.DELETED


class TestProjectAggregate:
    """Tests for Project aggregate."""

    def test_create_project(self):
        """Test creating Project aggregate."""
        project = Project(
            id="proj_123",
            user_id="user_456",
            title="My Decodable",
            canvas_data={"objects": []},
        )

        assert project.id == "proj_123"
        assert project.user_id == "user_456"
        assert project.title == "My Decodable"
        assert project.status == ProjectStatus.ACTIVE

    def test_create_with_defaults(self):
        """Test creating Project with default values."""
        project = Project(
            id="proj_789",
            user_id="user_123",
        )

        assert project.title == "Untitled"
        assert project.canvas_data == {}
        assert project.thumbnail_url is None
        assert project.status == ProjectStatus.ACTIVE

    def test_update_title(self):
        """Test updating project title."""
        project = Project(id="proj_123", user_id="user_456")

        project.update_title("New Title")

        assert project.title == "New Title"
        assert project.updated_at is not None

    def test_update_canvas_data(self):
        """Test updating canvas data."""
        project = Project(id="proj_123", user_id="user_456")

        new_data = {"objects": [{"type": "rect"}]}
        project.update_canvas_data(new_data)

        assert project.canvas_data == new_data

    def test_soft_delete(self):
        """Test soft deleting project."""
        project = Project(
            id="proj_123",
            user_id="user_456",
            status=ProjectStatus.ACTIVE,
        )

        project.soft_delete()

        assert project.status == ProjectStatus.DELETED
        assert project.deleted_at is not None
        assert project.is_deleted is True

    def test_restore(self):
        """Test restoring deleted project."""
        project = Project(
            id="proj_123",
            user_id="user_456",
            status=ProjectStatus.DELETED,
            deleted_at=datetime.now(timezone.utc),
        )

        project.restore()

        assert project.status == ProjectStatus.ACTIVE
        assert project.deleted_at is None
        assert project.is_deleted is False

    def test_is_owned_by(self):
        """Test ownership check."""
        project = Project(id="proj_123", user_id="user_456")

        assert project.is_owned_by("user_456") is True
        assert project.is_owned_by("other_user") is False

    def test_duplicate(self):
        """Test duplicating project."""
        original = Project(
            id="proj_123",
            user_id="user_456",
            title="Original",
            canvas_data={"objects": [{"type": "text"}]},
        )

        duplicate = original.duplicate(new_id="proj_789")

        assert duplicate.id == "proj_789"
        assert duplicate.user_id == "user_456"
        assert duplicate.title == "Original (Copy)"
        assert duplicate.canvas_data == original.canvas_data
        assert duplicate.status == ProjectStatus.ACTIVE

    def test_duplicate_for_purchase(self):
        """Test duplicating project for marketplace purchase."""
        original = Project(
            id="proj_123",
            user_id="seller_456",
            title="Template",
            canvas_data={"objects": []},
        )

        duplicate = original.duplicate_for_buyer(
            new_id="proj_789",
            buyer_id="buyer_123",
            source_listing_id="listing_001",
        )

        assert duplicate.id == "proj_789"
        assert duplicate.user_id == "buyer_123"
        assert duplicate.title == "Template"
        assert duplicate.source_listing_id == "listing_001"

    def test_to_dict(self):
        """Test serializing Project to dict."""
        project = Project(
            id="proj_123",
            user_id="user_456",
            title="Test Project",
            canvas_data={"objects": []},
        )

        data = project.to_dict()

        assert data["id"] == "proj_123"
        assert data["user_id"] == "user_456"
        assert data["title"] == "Test Project"
        assert "canvas_data" in data

    def test_from_dict(self):
        """Test creating Project from dict."""
        data = {
            "id": "proj_789",
            "user_id": "user_123",
            "title": "From Dict",
            "canvas_data": {"objects": []},
            "status": "active",
        }

        project = Project.from_dict(data)

        assert project.id == "proj_789"
        assert project.title == "From Dict"
        assert project.status == ProjectStatus.ACTIVE


class TestCreationService:
    """Tests for CreationService (with mocked repository)."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock project repository."""
        repo = MagicMock()
        repo.get_by_id = AsyncMock()
        repo.get_by_user = AsyncMock()
        repo.count_by_user = AsyncMock()
        repo.save = AsyncMock()
        repo.delete = AsyncMock()
        return repo

    @pytest.fixture
    def creation_service(self, mock_repository):
        """Create creation service with mock repository."""
        from domains.creation import CreationService
        return CreationService(mock_repository)

    @pytest.mark.asyncio
    async def test_create_project(self, creation_service, mock_repository):
        """Test creating a project."""
        mock_repository.count_by_user.return_value = 0

        result = await creation_service.create_project(
            user_id="user_123",
            title="New Project",
            tier="free",
        )

        assert result.success is True
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_project_limit_exceeded(self, creation_service, mock_repository):
        """Test project creation when limit exceeded."""
        # Free user already has 1 project (limit is 1)
        mock_repository.count_by_user.return_value = 1

        result = await creation_service.create_project(
            user_id="user_123",
            title="Another Project",
            tier="free",
        )

        assert result.success is False
        assert "limit" in result.error.lower()
        mock_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_project_with_access(self, creation_service, mock_repository):
        """Test getting project with access check."""
        mock_repository.get_by_id.return_value = Project(
            id="proj_123",
            user_id="user_456",
            title="Test",
        )

        # Owner can access
        project = await creation_service.get_project_with_access(
            project_id="proj_123",
            user_id="user_456",
        )

        assert project.id == "proj_123"

    @pytest.mark.asyncio
    async def test_get_project_access_denied(self, creation_service, mock_repository):
        """Test getting project without access."""
        mock_repository.get_by_id.return_value = Project(
            id="proj_123",
            user_id="user_456",
            title="Test",
        )

        # Non-owner cannot access
        with pytest.raises(ProjectAccessDeniedError):
            await creation_service.get_project_with_access(
                project_id="proj_123",
                user_id="other_user",
            )

    @pytest.mark.asyncio
    async def test_get_user_projects(self, creation_service, mock_repository):
        """Test getting user's projects."""
        mock_repository.get_by_user.return_value = [
            Project(id="p1", user_id="user_123", title="Project 1"),
            Project(id="p2", user_id="user_123", title="Project 2"),
        ]

        projects = await creation_service.get_user_projects("user_123")

        assert len(projects) == 2
        mock_repository.get_by_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_project(self, creation_service, mock_repository):
        """Test soft deleting project."""
        mock_repository.get_by_id.return_value = Project(
            id="proj_123",
            user_id="user_456",
            title="To Delete",
        )

        result = await creation_service.delete_project(
            project_id="proj_123",
            user_id="user_456",
        )

        assert result.success is True
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_project_not_owner(self, creation_service, mock_repository):
        """Test deleting project by non-owner fails."""
        mock_repository.get_by_id.return_value = Project(
            id="proj_123",
            user_id="user_456",
            title="Not Mine",
        )

        result = await creation_service.delete_project(
            project_id="proj_123",
            user_id="other_user",
        )

        assert result.success is False
        mock_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_project(self, creation_service, mock_repository):
        """Test duplicating project."""
        mock_repository.get_by_id.return_value = Project(
            id="proj_123",
            user_id="user_456",
            title="Original",
            canvas_data={"objects": []},
        )
        mock_repository.count_by_user.return_value = 0

        result = await creation_service.duplicate_project(
            project_id="proj_123",
            user_id="user_456",
            tier="starter",
        )

        assert result.success is True
        assert result.project.title == "Original (Copy)"


class TestProjectLimits:
    """Tests for project limit enforcement by tier."""

    def test_free_tier_limit(self):
        """Test Free tier project limit is 1."""
        from domains.creation import get_project_limit
        assert get_project_limit("free") == 1

    def test_starter_tier_limit(self):
        """Test Starter tier project limit is 20."""
        from domains.creation import get_project_limit
        assert get_project_limit("starter") == 20

    def test_pro_tier_limit(self):
        """Test Pro tier project limit is 200."""
        from domains.creation import get_project_limit
        assert get_project_limit("pro") == 200

    def test_unknown_tier_defaults_to_free(self):
        """Test unknown tier defaults to Free limit."""
        from domains.creation import get_project_limit
        assert get_project_limit("unknown") == 1
        assert get_project_limit("") == 1
        assert get_project_limit(None) == 1

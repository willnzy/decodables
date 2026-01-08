"""
Creation Commands - Project operations that change state.

@module application.commands.creation
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from domains.creation import (
    CreationService,
    Project,
    CanvasSize,
)


@dataclass
class CreateProjectCommand:
    """
    Command to create a new project.

    Params aligned with API layer (api/user/projects.py):
    - user_id: Owner's user ID
    - title: Project title
    - canvas_data: Optional canvas JSON data
    - tier: User's subscription tier for limit checking
    """
    user_id: str
    title: str = "Untitled"
    canvas_data: Optional[Dict[str, Any]] = None
    tier: str = "free"


@dataclass
class CreateProjectResult:
    """Result of project creation."""
    success: bool
    project: Optional[Project] = None
    project_dict: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class CreateProjectHandler:
    """Handler for CreateProjectCommand."""

    def __init__(self, creation_service: CreationService):
        self._creation_service = creation_service

    async def handle(self, command: CreateProjectCommand) -> CreateProjectResult:
        """Execute project creation."""
        try:
            # Extract canvas size from canvas_data if provided
            canvas_size = None
            if command.canvas_data:
                width = command.canvas_data.get("width", 1080)
                height = command.canvas_data.get("height", 1080)
                canvas_size = CanvasSize(width, height)

            project = await self._creation_service.create_project(
                owner_id=command.user_id,
                title=command.title,
                canvas_size=canvas_size,
                user_tier=command.tier,
            )

            return CreateProjectResult(
                success=True,
                project=project,
                project_dict=project.to_dict() if project else None,
            )

        except Exception as e:
            return CreateProjectResult(
                success=False,
                error=str(e),
            )


@dataclass
class UpdateProjectCommand:
    """
    Command to update project.

    Params aligned with API layer (api/user/projects.py):
    - project_id: Project ID
    - user_id: User making update (for ownership check)
    - title: New title
    - canvas_data: Canvas JSON data (editor state)
    - thumbnail_url: Thumbnail URL
    """
    project_id: str
    user_id: str
    title: Optional[str] = None
    canvas_data: Optional[Dict[str, Any]] = None
    thumbnail_url: Optional[str] = None


@dataclass
class UpdateProjectResult:
    """Result of project update."""
    success: bool
    project: Optional[Project] = None
    error: Optional[str] = None


class UpdateProjectHandler:
    """Handler for UpdateProjectCommand."""

    def __init__(self, creation_service: CreationService):
        self._creation_service = creation_service

    async def handle(self, command: UpdateProjectCommand) -> UpdateProjectResult:
        """Execute project update."""
        try:
            # First verify access
            project = await self._creation_service.get_project_with_access(
                project_id=command.project_id,
                user_id=command.user_id,
                require_edit=True,
            )

            # Update via repository's quick save method
            await self._creation_service._repository.save_project_quick(
                project_id=command.project_id,
                user_id=command.user_id,
                canvas_data=command.canvas_data,
                thumbnail_url=command.thumbnail_url,
                title=command.title,
            )

            return UpdateProjectResult(
                success=True,
                project=project,
            )

        except Exception as e:
            return UpdateProjectResult(
                success=False,
                error=str(e),
            )


@dataclass
class DeleteProjectCommand:
    """
    Command to delete a project.

    Params aligned with API layer (api/user/projects.py):
    - project_id: Project ID
    - user_id: User requesting delete
    - permanent: If true, permanently hide (stage 2); if false, soft delete (stage 1)
    """
    project_id: str
    user_id: str
    permanent: bool = False


@dataclass
class DeleteProjectResult:
    """Result of project deletion."""
    success: bool
    error: Optional[str] = None


class DeleteProjectHandler:
    """Handler for DeleteProjectCommand."""

    def __init__(self, creation_service: CreationService):
        self._creation_service = creation_service

    async def handle(self, command: DeleteProjectCommand) -> DeleteProjectResult:
        """Execute project deletion."""
        try:
            # Map 'permanent' to service's 'hard_delete' param
            success = await self._creation_service.delete_project(
                project_id=command.project_id,
                user_id=command.user_id,
                hard_delete=command.permanent,
            )

            return DeleteProjectResult(success=success)

        except Exception as e:
            return DeleteProjectResult(
                success=False,
                error=str(e),
            )


@dataclass
class SaveCanvasCommand:
    """
    Command to save canvas data for a page.
    """
    project_id: str
    page_id: str
    user_id: str
    canvas_data: Dict[str, Any]


@dataclass
class SaveCanvasResult:
    """Result of canvas save."""
    success: bool
    error: Optional[str] = None


class SaveCanvasHandler:
    """Handler for SaveCanvasCommand."""

    def __init__(self, creation_service: CreationService):
        self._creation_service = creation_service

    async def handle(self, command: SaveCanvasCommand) -> SaveCanvasResult:
        """Execute canvas save."""
        try:
            await self._creation_service.update_page_canvas(
                project_id=command.project_id,
                page_id=command.page_id,
                user_id=command.user_id,
                canvas_data=command.canvas_data,
            )

            return SaveCanvasResult(success=True)

        except Exception as e:
            return SaveCanvasResult(
                success=False,
                error=str(e),
            )

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
    """
    owner_id: str
    title: str
    canvas_width: int = 1080
    canvas_height: int = 1080
    description: Optional[str] = None
    user_tier: str = "free"


@dataclass
class CreateProjectResult:
    """Result of project creation."""
    success: bool
    project: Optional[Project] = None
    error: Optional[str] = None


class CreateProjectHandler:
    """Handler for CreateProjectCommand."""

    def __init__(self, creation_service: CreationService):
        self._creation_service = creation_service

    async def handle(self, command: CreateProjectCommand) -> CreateProjectResult:
        """Execute project creation."""
        try:
            canvas_size = CanvasSize(command.canvas_width, command.canvas_height)

            project = await self._creation_service.create_project(
                owner_id=command.owner_id,
                title=command.title,
                canvas_size=canvas_size,
                description=command.description,
                user_tier=command.user_tier,
            )

            return CreateProjectResult(
                success=True,
                project=project,
            )

        except Exception as e:
            return CreateProjectResult(
                success=False,
                error=str(e),
            )


@dataclass
class UpdateProjectCommand:
    """
    Command to update project metadata.
    """
    project_id: str
    user_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None


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
            project = await self._creation_service.update_project(
                project_id=command.project_id,
                user_id=command.user_id,
                title=command.title,
                description=command.description,
                tags=command.tags,
                is_public=command.is_public,
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
    """
    project_id: str
    user_id: str
    hard_delete: bool = False


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
            success = await self._creation_service.delete_project(
                project_id=command.project_id,
                user_id=command.user_id,
                hard_delete=command.hard_delete,
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

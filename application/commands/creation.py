"""
Creation Commands - Project operations that change state.

@module application.commands.creation
@version 1.1.0

Changes in v1.1.0:
- Added idempotency_key support for CreateProjectCommand (prevents duplicate creation)
- Added pre-commit serialization validation (ensures response can be built before commit)
- Implements industry best practices for distributed system consistency
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import logging

from domains.creation import (
    CreationService,
    Project,
    CanvasSize,
)
from domains.creation.locked_elements import update_project_locked_status

logger = logging.getLogger(__name__)


class SerializationError(Exception):
    """Raised when response serialization fails before commit."""
    pass


@dataclass
class CreateProjectCommand:
    """
    Command to create a new project.

    Params aligned with API layer (api/user/projects.py):
    - user_id: Owner's user ID
    - title: Project title
    - canvas_data: Optional canvas JSON data
    - tier: User's subscription tier for limit checking
    - idempotency_key: Client-generated unique key for idempotent creation (v1.1.0)

    Idempotency Pattern (Industry Best Practice):
    - Client generates a UUID and sends it with the request
    - If request fails (network error, 500, etc.), client retries with SAME key
    - Server checks if project with this key already exists
    - If exists: return existing project (no duplicate created)
    - If not: create new project with this key
    - Used by Stripe, PayPal, AWS for payment/resource creation APIs
    """
    user_id: str
    title: str = "Untitled"
    canvas_data: Optional[Dict[str, Any]] = None
    tier: str = "t1"
    idempotency_key: Optional[str] = None  # v1.1.0: Client-generated UUID for idempotent creation


@dataclass
class CreateProjectResult:
    """Result of project creation."""
    success: bool
    project: Optional[Project] = None
    project_dict: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    exception: Optional[Exception] = None  # Original exception for type checking


class CreateProjectHandler:
    """
    Handler for CreateProjectCommand.

    v1.1.0 Enhancements:
    1. Idempotency support - prevents duplicate project creation on retry
    2. Pre-commit serialization validation - catches serialization errors before DB commit
    3. Rollback on serialization failure - ensures consistency
    """

    def __init__(self, creation_service: CreationService):
        self._creation_service = creation_service

    async def handle(self, command: CreateProjectCommand) -> CreateProjectResult:
        """
        Execute project creation with idempotency and serialization safety.

        Flow:
        1. If idempotency_key provided, check for existing project
        2. If exists, return existing (idempotent behavior)
        3. If not, create new project
        4. Validate serialization BEFORE returning (catch Pydantic errors)
        5. If serialization fails, delete project and raise error
        """
        project = None

        try:
            # Step 1: Idempotency check - return existing if key matches
            if command.idempotency_key:
                existing = await self._creation_service.get_by_idempotency_key(
                    user_id=command.user_id,
                    idempotency_key=command.idempotency_key,
                )
                if existing:
                    logger.info(
                        f"[Idempotent] Returning existing project {existing.project_id} "
                        f"for idempotency_key={command.idempotency_key}"
                    )
                    # Validate serialization for existing project too
                    project_dict = existing.to_dict()
                    return CreateProjectResult(
                        success=True,
                        project=existing,
                        project_dict=project_dict,
                    )

            # Step 2: Extract canvas size from canvas_data if provided
            canvas_size = None
            if command.canvas_data:
                width = command.canvas_data.get("width", 1080)
                height = command.canvas_data.get("height", 1080)
                canvas_size = CanvasSize(width, height)

            # Step 3: Create project
            project = await self._creation_service.create_project(
                owner_id=command.user_id,
                title=command.title,
                canvas_size=canvas_size,
                user_tier=command.tier,
                idempotency_key=command.idempotency_key,
            )

            # Step 4: Pre-commit serialization validation
            # This catches Pydantic/serialization errors BEFORE returning success
            try:
                project_dict = project.to_dict()
                # Optionally validate against Pydantic model here
                # from api.user.projects import ProjectResponse
                # ProjectResponse(**project_dict)  # Would catch field mismatches
            except Exception as serialization_error:
                # Step 5: Rollback - delete the created project
                logger.error(
                    f"[SerializationError] Project {project.project_id} created but "
                    f"serialization failed: {serialization_error}. Rolling back."
                )
                try:
                    await self._creation_service.delete_project(
                        project_id=project.project_id,
                        user_id=command.user_id,
                        hard_delete=True,  # Permanently delete, not soft delete
                    )
                    logger.info(f"[Rollback] Project {project.project_id} deleted successfully")
                except Exception as rollback_error:
                    logger.error(f"[Rollback Failed] Could not delete project: {rollback_error}")

                raise SerializationError(
                    f"Project created but response serialization failed: {serialization_error}"
                ) from serialization_error

            return CreateProjectResult(
                success=True,
                project=project,
                project_dict=project_dict,
            )

        except SerializationError:
            # Re-raise serialization errors with clear message
            raise

        except Exception as e:
            return CreateProjectResult(
                success=False,
                error=str(e),
                exception=e,
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
    - user_tier: User's current tier (for locked elements check)
    """
    project_id: str
    user_id: str
    title: Optional[str] = None
    canvas_data: Optional[Dict[str, Any]] = None
    thumbnail_url: Optional[str] = None
    user_tier: str = "t1"  # Default to free tier


@dataclass
class UpdateProjectResult:
    """Result of project update."""
    success: bool
    project: Optional[Project] = None
    error: Optional[str] = None
    exception: Optional[Exception] = None  # Original exception for type checking


class UpdateProjectHandler:
    """Handler for UpdateProjectCommand."""

    def __init__(
        self,
        creation_service: CreationService,
        listing_repository=None,
        thumbnail_service=None,
    ):
        """
        Initialize handler with dependencies.

        Args:
            creation_service: Creation service for project operations
            listing_repository: Listing repository for locked elements check (optional)
            thumbnail_service: ThumbnailService for background thumbnail generation (optional)
        """
        self._creation_service = creation_service
        self._listing_repository = listing_repository
        self._thumbnail_service = thumbnail_service

    async def handle(self, command: UpdateProjectCommand) -> UpdateProjectResult:
        """
        Execute project update.

        P1-013: Now includes locked elements check when canvas_data is updated.
        v2.3.0: Triggers background thumbnail generation when canvas_data is updated.
        """
        import asyncio

        try:
            # First verify access - this also confirms ownership
            project = await self._creation_service.get_project_with_access(
                project_id=command.project_id,
                user_id=command.user_id,
                require_edit=True,
            )

            # Track if canvas_data was updated (for thumbnail generation)
            canvas_updated = command.canvas_data is not None

            # Update project metadata through domain aggregate
            if command.title is not None:
                project.update_metadata(title=command.title)

            if command.canvas_data is not None:
                project.canvas_data = command.canvas_data

            if command.thumbnail_url is not None:
                project.metadata.thumbnail_url = command.thumbnail_url

            # P1-013: Check for locked elements if canvas_data was updated
            if command.canvas_data is not None and self._listing_repository is not None:
                try:
                    has_locked = await update_project_locked_status(
                        project=project,
                        canvas_data=command.canvas_data,
                        user_tier=command.user_tier,
                        listing_repo=self._listing_repository
                    )

                    if has_locked:
                        logger.warning(
                            f"Project {project.id} contains locked elements "
                            f"(user tier: {command.user_tier})"
                        )
                except Exception as lock_check_error:
                    # Don't fail the entire update if locked elements check fails
                    logger.error(f"Failed to check locked elements: {lock_check_error}")
                    # Mark as potentially containing locked elements (fail-safe)
                    project.contains_locked_elements = True

            # Persist changes through repository
            await self._creation_service._repository.update(project)

            # v2.3.0: Trigger background thumbnail generation when canvas_data is updated
            # This runs asynchronously (non-blocking) to avoid slowing down save operations
            if canvas_updated and self._thumbnail_service is not None:
                # Create background task for thumbnail generation
                asyncio.create_task(
                    self._generate_thumbnail_background(
                        command.project_id,
                        command.user_id,
                    )
                )
                logger.debug(f"[UpdateProject] Triggered background thumbnail generation for {command.project_id[:8]}...")

            return UpdateProjectResult(
                success=True,
                project=project,
            )

        except Exception as e:
            return UpdateProjectResult(
                success=False,
                error=str(e),
                exception=e,
            )

    async def _generate_thumbnail_background(
        self,
        project_id: str,
        user_id: str,
    ):
        """
        Generate thumbnail in background (non-blocking).

        This method wraps the thumbnail generation with error handling
        to ensure background task failures don't affect the main flow.

        Args:
            project_id: Project ID
            user_id: User ID
        """
        try:
            thumbnail_url = await self._thumbnail_service.generate_and_store(
                project_id, user_id
            )
            if thumbnail_url:
                logger.info(f"[UpdateProject] Background thumbnail generated for {project_id[:8]}...")
            else:
                logger.warning(f"[UpdateProject] Background thumbnail generation returned None for {project_id[:8]}...")
        except Exception as e:
            # Log but don't raise - this is a background task
            logger.error(f"[UpdateProject] Background thumbnail generation failed for {project_id[:8]}...: {e}")


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
    exception: Optional[Exception] = None  # Original exception for type checking


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
                exception=e,
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


@dataclass
class RestoreProjectCommand:
    """
    Command to restore a deleted project from trash.

    Params aligned with API layer (api/user/projects.py):
    - project_id: Project ID to restore
    - user_id: User requesting restore (must be owner)
    """
    project_id: str
    user_id: str


@dataclass
class RestoreProjectResult:
    """Result of project restoration."""
    success: bool
    project: Optional[Project] = None
    project_dict: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    exception: Optional[Exception] = None  # Original exception for type checking


class RestoreProjectHandler:
    """Handler for RestoreProjectCommand."""

    def __init__(self, creation_service: CreationService):
        self._creation_service = creation_service

    async def handle(self, command: RestoreProjectCommand) -> RestoreProjectResult:
        """Execute project restoration."""
        try:
            project = await self._creation_service.restore_project(
                project_id=command.project_id,
                user_id=command.user_id,
            )

            return RestoreProjectResult(
                success=True,
                project=project,
                project_dict=project.to_dict() if project else None,
            )

        except Exception as e:
            return RestoreProjectResult(
                success=False,
                error=str(e),
                exception=e,
            )

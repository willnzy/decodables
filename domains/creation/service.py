"""
Creation Domain Service - Orchestrates project operations.

@module domains.creation.service
@version 2.1.0

This service handles domain logic that doesn't naturally belong to aggregates.
It coordinates operations but delegates persistence to the repository.

Project limits are now fetched from TierService (system_configs) instead of hardcoded.

v2.1.0 Changes:
- Added idempotency_key support for create_project (industry best practice)
- Added get_by_idempotency_key method
- Prevents duplicate project creation on retry
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING

from .aggregates.project import Project, Page
from .repository import IProjectRepository
from .value_objects import ProjectStatus, CanvasSize, ProjectMetadata
from .exceptions import (
    ProjectNotFoundException,
    ProjectAccessDeniedException,
    InvalidProjectDataException,
    ProjectLimitExceededException,
)

if TYPE_CHECKING:
    from domains.identity.tier_service import TierService


class CreationService:
    """
    Domain service for creation operations.

    This service:
    - Manages project lifecycle
    - Enforces access control
    - Handles project limits (from TierService configuration)
    """

    def __init__(
        self,
        repository: IProjectRepository,
        tier_service: "TierService" = None
    ):
        """
        Initialize creation service with repository and tier service.

        Args:
            repository: Project repository implementation
            tier_service: TierService for fetching tier-based limits
        """
        self._repository = repository
        self._tier_service = tier_service

    async def get_project(self, project_id: str) -> Optional[Project]:
        """
        Get project by ID.

        Args:
            project_id: Project ID

        Returns:
            Project or None
        """
        return await self._repository.get_by_id(project_id)

    async def get_project_or_raise(self, project_id: str) -> Project:
        """
        Get project or raise exception.

        Args:
            project_id: Project ID

        Returns:
            Project

        Raises:
            ProjectNotFoundException: If not found
        """
        project = await self._repository.get_by_id(project_id)
        if not project:
            raise ProjectNotFoundException(project_id)
        return project

    async def get_project_with_access(
        self,
        project_id: str,
        user_id: str,
        require_edit: bool = False
    ) -> Project:
        """
        Get project with access check.

        Args:
            project_id: Project ID
            user_id: User requesting access
            require_edit: Require edit permission

        Returns:
            Project

        Raises:
            ProjectNotFoundException: If not found
            ProjectAccessDeniedException: If access denied
        """
        project = await self.get_project_or_raise(project_id)

        if require_edit:
            if not project.can_edit(user_id):
                raise ProjectAccessDeniedException(project_id, user_id)
        else:
            if not project.can_access(user_id):
                raise ProjectAccessDeniedException(project_id, user_id)

        return project

    async def get_by_idempotency_key(
        self,
        user_id: str,
        idempotency_key: str
    ) -> Optional[Project]:
        """
        Get project by idempotency key for a specific user.

        v2.1.0: Idempotency support - returns existing project if already created
        with this key, enabling safe retries.

        Args:
            user_id: Owner's user ID
            idempotency_key: Client-generated unique key

        Returns:
            Project if found, None otherwise
        """
        if not idempotency_key:
            return None

        return await self._repository.get_by_idempotency_key(
            user_id=user_id,
            idempotency_key=idempotency_key,
        )

    async def create_project(
        self,
        owner_id: str,
        title: str,
        canvas_size: Optional[CanvasSize] = None,
        description: Optional[str] = None,
        user_tier: str = "t1",
        idempotency_key: Optional[str] = None
    ) -> Project:
        """
        Create a new project with atomic limit check.

        Uses optimistic concurrency control:
        1. Check limit before create
        2. Create project
        3. Verify count after create didn't exceed limit
        4. If exceeded, rollback (delete) and raise error

        v2.1.0: Added idempotency_key support for safe retries.

        Args:
            owner_id: User ID of owner
            title: Project title
            canvas_size: Canvas dimensions
            description: Optional description
            user_tier: User's subscription tier
            idempotency_key: Client-generated unique key for idempotent creation

        Returns:
            Created Project

        Raises:
            ProjectLimitExceededException: If limit reached
            InvalidProjectDataException: If data invalid
        """
        if not title or not title.strip():
            raise InvalidProjectDataException("title", "Title is required")

        # Get project limit from TierService (configurable)
        if self._tier_service:
            limit = await self._tier_service.get_max_projects(user_tier)
        else:
            # Fallback if tier_service not injected
            from domains.identity.tier_service import EMERGENCY_TIER_CONFIGS
            limit = EMERGENCY_TIER_CONFIGS.get(user_tier, {}).get("max_projects", 1)

        # Pre-check (optimistic, may have race condition)
        current_count = await self._repository.count_by_owner(owner_id)
        if current_count >= limit:
            raise ProjectLimitExceededException(owner_id, limit)

        # Create project with idempotency_key
        project = Project.create_new(
            owner_id=owner_id,
            title=title.strip(),
            canvas_size=canvas_size,
            description=description,
        )
        # v2.1.0: Store idempotency_key for duplicate detection
        if idempotency_key:
            project.idempotency_key = idempotency_key

        created = await self._repository.create(project)

        # Post-check (catches race condition)
        final_count = await self._repository.count_by_owner(owner_id)
        if final_count > limit:
            # Race condition detected - rollback by deleting
            await self._repository.delete(created.project_id)
            raise ProjectLimitExceededException(owner_id, limit)

        return created

    async def update_project(
        self,
        project_id: str,
        user_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_public: Optional[bool] = None
    ) -> Project:
        """
        Update project metadata.

        Args:
            project_id: Project ID
            user_id: User making update
            title: New title
            description: New description
            tags: New tags
            is_public: Visibility setting

        Returns:
            Updated Project
        """
        project = await self.get_project_with_access(project_id, user_id, require_edit=True)

        project.update_metadata(
            title=title,
            description=description,
            tags=tags,
            is_public=is_public,
        )

        return await self._repository.update(project)

    async def delete_project(
        self,
        project_id: str,
        user_id: str,
        hard_delete: bool = False
    ) -> bool:
        """
        Delete a project.

        Args:
            project_id: Project ID
            user_id: User requesting delete
            hard_delete: Permanently delete

        Returns:
            True if deleted
        """
        project = await self.get_project_with_access(project_id, user_id, require_edit=True)

        # Only owner can delete
        if project.owner_id != user_id:
            raise ProjectAccessDeniedException(project_id, user_id)

        if hard_delete:
            return await self._repository.delete(project_id)
        else:
            project.mark_deleted()
            await self._repository.update(project)
            return True

    async def archive_project(self, project_id: str, user_id: str) -> Project:
        """
        Archive a project.

        Args:
            project_id: Project ID
            user_id: User requesting archive

        Returns:
            Archived Project
        """
        project = await self.get_project_with_access(project_id, user_id, require_edit=True)
        project.archive()
        return await self._repository.update(project)

    async def restore_project(self, project_id: str, user_id: str) -> Project:
        """
        Restore archived project.

        Args:
            project_id: Project ID
            user_id: User requesting restore

        Returns:
            Restored Project
        """
        project = await self.get_project_with_access(project_id, user_id, require_edit=True)
        project.restore()
        return await self._repository.update(project)

    async def duplicate_project(
        self,
        project_id: str,
        user_id: str,
        tier: str = "t1"
    ) -> Project:
        """
        Duplicate a project with atomic limit check.

        Args:
            project_id: Source project ID
            user_id: User requesting duplication
            tier: User's subscription tier for limit checking

        Returns:
            New duplicated Project

        Raises:
            ProjectNotFoundException: If source project not found
            ProjectAccessDeniedException: If user doesn't own project
            ProjectLimitExceededException: If user at project limit
        """
        # Verify access to source project
        source = await self.get_project_with_access(project_id, user_id)

        limit = self.PROJECT_LIMITS.get(tier, 5)

        # Pre-check (optimistic)
        current_count = await self._repository.count_by_owner(user_id)
        if current_count >= limit:
            raise ProjectLimitExceededException(user_id, limit)

        # Create new project with copied data
        new_title = f"{source.metadata.title} (Copy)"
        new_project = Project.create_new(
            owner_id=user_id,
            title=new_title,
            canvas_size=source.canvas_size,
            description=source.metadata.description,
        )

        # Copy pages from source
        for page in source.pages:
            new_project.add_page(page.canvas_data)

        created = await self._repository.create(new_project)

        # Post-check (catches race condition)
        final_count = await self._repository.count_by_owner(user_id)
        if final_count > limit:
            await self._repository.delete(created.project_id)
            raise ProjectLimitExceededException(user_id, limit)

        return created

    async def add_page(
        self,
        project_id: str,
        user_id: str,
        canvas_data: Optional[Dict[str, Any]] = None
    ) -> Page:
        """
        Add a page to project.

        Args:
            project_id: Project ID
            user_id: User adding page
            canvas_data: Initial canvas data

        Returns:
            New Page
        """
        project = await self.get_project_with_access(project_id, user_id, require_edit=True)
        page = project.add_page(canvas_data)
        await self._repository.update(project)
        return page

    async def update_page_canvas(
        self,
        project_id: str,
        page_id: str,
        user_id: str,
        canvas_data: Dict[str, Any]
    ) -> Page:
        """
        Update page canvas data.

        Args:
            project_id: Project ID
            page_id: Page ID
            user_id: User making update
            canvas_data: New canvas data

        Returns:
            Updated Page
        """
        project = await self.get_project_with_access(project_id, user_id, require_edit=True)
        project.update_page_canvas(page_id, canvas_data)
        await self._repository.update(project)
        return project.get_page(page_id)

    async def get_user_projects(
        self,
        user_id: str,
        status: Optional[ProjectStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Project]:
        """
        Get projects owned by user.

        Args:
            user_id: User ID
            status: Filter by status
            limit: Max results
            offset: Results to skip

        Returns:
            List of Projects
        """
        return await self._repository.get_by_owner(
            owner_id=user_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def count_user_projects(self, user_id: str) -> int:
        """
        Count projects owned by user.

        Args:
            user_id: User ID

        Returns:
            Total project count
        """
        return await self._repository.count_by_owner(user_id)

    async def add_collaborator(
        self,
        project_id: str,
        owner_id: str,
        collaborator_id: str
    ) -> Project:
        """
        Add collaborator to project.

        Args:
            project_id: Project ID
            owner_id: Owner making change
            collaborator_id: User to add

        Returns:
            Updated Project
        """
        project = await self.get_project_with_access(project_id, owner_id, require_edit=True)

        if project.owner_id != owner_id:
            raise ProjectAccessDeniedException(project_id, owner_id)

        project.add_collaborator(collaborator_id)
        return await self._repository.update(project)

    async def search_projects(
        self,
        query: str,
        user_id: Optional[str] = None,
        include_public: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[Project]:
        """
        Search projects.

        Args:
            query: Search query
            user_id: Filter by owner
            include_public: Include public projects
            limit: Max results
            offset: Results to skip

        Returns:
            List of matching Projects
        """
        return await self._repository.search(
            query=query,
            owner_id=user_id,
            include_public=include_public,
            limit=limit,
            offset=offset,
        )

    async def get_user_deleted_projects(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get user's deleted projects (recoverable only).

        Only returns projects within recovery period.
        Expired projects are automatically filtered out.

        Args:
            user_id: User ID
            limit: Max results per page
            offset: Results to skip for pagination

        Returns:
            Tuple of (list of project dicts, total count)
        """
        # Use BaseRepository method to auto-filter expired records
        projects, total = await self._repository.list_deleted_recoverable(
            user_id=user_id,
            offset=offset,
            limit=limit
        )

        # Convert Project entities to dicts for backward compatibility
        project_dicts = []
        for proj in projects:
            project_dicts.append({
                "id": proj.project_id,
                "title": proj.title,
                "thumbnail_url": proj.thumbnail_url,
                "deleted_at": proj.deleted_at,
                "recovery_expires_at": proj.recovery_expires_at,
            })

        return project_dicts, total

    async def get_seller_project_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get seller statistics for projects.

        Args:
            user_id: User ID

        Returns:
            Dict with total_listings, total_sales, total_revenue
        """
        return await self._repository.get_seller_project_stats(user_id)

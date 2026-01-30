"""
Project Repository Implementation - Supabase data access for creation domain.

@module infrastructure.repositories.project_repository
@version 2.0.0 (AsyncClient migration)

Changes in v2.0:
- Migrated all methods to use AsyncClient with await
- All .execute() calls now properly awaited

Changes in v1.0:
- Implements IProjectRepository using Supabase PostgreSQL
- Inherits from BaseRepository for soft/hard delete support
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging
import json

from core.utils.validation import sanitize_postgrest_query

from domains.creation.repository import IProjectRepository
from domains.creation.aggregates.project import Project, Page
from domains.creation.value_objects import (
    ProjectStatus,
    CanvasSize,
    ProjectMetadata,
)
from domains.creation.exceptions import ProjectNotFoundException
from postgrest.exceptions import APIError
from core.database import retry_on_network_error
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class SupabaseProjectRepository(BaseRepository[Project], IProjectRepository):
    """
    Supabase implementation of project repository.

    Inherits soft/hard delete operations from BaseRepository.
    """

    @property
    def table_name(self) -> str:
        """Table name for projects."""
        return "projects"

    async def get_by_id(self, project_id: str) -> Optional[Project]:
        """Get project by ID."""
        try:
            result = await self.client.table("projects").select("*").eq(
                "id", project_id
            ).single().execute()

            if not result.data:
                return None

            project = self._map_to_project(result.data)

            # Load pages
            pages_result = await self.client.table("project_pages").select("*").eq(
                "project_id", project_id
            ).order("page_number").execute()

            project.pages = [self._map_to_page(row) for row in pages_result.data]

            return project

        except APIError as e:
            if e.code == "PGRST116":
                return None
            logger.error(f"Failed to get project {project_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}")
            return None

    async def save(self, project: Project) -> Project:
        """Persist project (upsert)."""
        try:
            data = self._map_to_row(project)
            await self.client.table("projects").upsert(
                data, on_conflict="id"
            ).execute()

            # v3.26: Batch save pages (N+1 fix)
            if project.pages:
                await self.save_pages_batch(project.project_id, project.pages)

            return project

        except Exception as e:
            logger.error(f"Failed to save project {project.project_id}: {e}")
            raise

    async def create(self, project: Project) -> Project:
        """Create a new project."""
        try:
            data = self._map_to_row(project)
            await self.client.table("projects").insert(data).execute()

            # v3.26: Batch create pages (N+1 fix)
            if project.pages:
                await self.save_pages_batch(project.project_id, project.pages)

            return project

        except Exception as e:
            logger.error(f"Failed to create project {project.project_id}: {e}")
            raise

    async def update(self, project: Project) -> Project:
        """Update existing project."""
        try:
            data = self._map_to_row(project)
            data["updated_at"] = datetime.now(timezone.utc).isoformat()

            result = await self.client.table("projects").update(data).eq(
                "id", project.project_id
            ).execute()

            if not result.data or len(result.data) == 0:
                raise ProjectNotFoundException(project.project_id)

            return project

        except ProjectNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to update project {project.project_id}: {e}")
            raise

    async def delete(self, project_id: str) -> bool:
        """
        Soft delete a project (mark as deleted).

        Uses BaseRepository.soft_delete() for soft deletion.
        For hard delete (physical removal), use hard_delete() method.

        Note: This delegates to soft_delete() for safety.
        Project pages are preserved for potential restoration.
        """
        # Use 'id' field (UUID) for BaseRepository compatibility
        return await super().soft_delete(project_id)

    async def soft_delete(self, project_id: str, user_id: Optional[str] = None) -> bool:
        """
        Soft delete a project (inherited from BaseRepository).

        Args:
            project_id: Project ID (can be UUID or project_id string)
            user_id: Optional user ID for ownership check

        Returns:
            True if deleted successfully

        Note: Uses is_deleted flag, not status field.
        """
        # Support both UUID (id) and legacy project_id
        return await super().soft_delete(project_id, user_id)

    async def get_by_owner(
        self,
        owner_id: str,
        status: Optional[ProjectStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Project]:
        """Get projects owned by a user."""
        try:
            query = self.client.table("projects").select("*").eq(
                "user_id", owner_id
            ).eq("is_deleted", False).neq("status", ProjectStatus.DELETED.value).order(
                "updated_at", desc=True
            ).range(offset, offset + limit - 1)

            if status:
                query = query.eq("status", status.value)

            result = await query.execute()

            return [self._map_to_project(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get projects for owner {owner_id}: {e}")
            return []

    async def get_shared_with_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Project]:
        """Get projects shared with a user."""
        try:
            result = await self.client.table("projects").select("*").contains(
                "collaborators", [user_id]
            ).neq("status", ProjectStatus.DELETED.value).order(
                "updated_at", desc=True
            ).range(offset, offset + limit - 1).execute()

            return [self._map_to_project(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get shared projects for user {user_id}: {e}")
            return []

    async def get_public_projects(
        self,
        limit: int = 50,
        offset: int = 0,
        tags: Optional[List[str]] = None
    ) -> List[Project]:
        """Get public projects."""
        try:
            query = self.client.table("projects").select("*").eq(
                "is_public", True
            ).eq("status", ProjectStatus.ACTIVE.value).order(
                "updated_at", desc=True
            ).range(offset, offset + limit - 1)

            if tags:
                query = query.contains("tags", tags)

            result = await query.execute()

            return [self._map_to_project(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get public projects: {e}")
            return []

    async def count_by_owner(
        self,
        owner_id: str,
        status: Optional[ProjectStatus] = None
    ) -> int:
        """Count projects owned by user."""
        try:
            query = self.client.table("projects").select(
                "id", count="exact"
            ).eq("user_id", owner_id).neq(
                "status", ProjectStatus.DELETED.value
            ).eq("is_deleted", False)

            if status:
                query = query.eq("status", status.value)

            result = await query.execute()

            return result.count if result.count else 0

        except Exception as e:
            logger.error(f"Failed to count projects for owner {owner_id}: {e}")
            return 0

    async def save_page(self, project_id: str, page: Page) -> Page:
        """Save a single page."""
        try:
            data = {
                "page_id": page.page_id,
                "project_id": project_id,
                "page_number": page.page_number,
                "canvas_data": json.dumps(page.canvas_data) if page.canvas_data else None,
                "thumbnail_url": page.thumbnail_url,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            await self.client.table("project_pages").upsert(
                data, on_conflict="page_id"
            ).execute()

            return page

        except Exception as e:
            logger.error(f"Failed to save page {page.page_id}: {e}")
            raise

    async def save_pages_batch(self, project_id: str, pages: List[Page]) -> List[Page]:
        """
        Save multiple pages in a single batch operation (v3.26 - N+1 fix).

        Replaces N individual INSERT calls with 1 batch UPSERT.

        Args:
            project_id: Project ID
            pages: List of pages to save

        Returns:
            List of saved pages
        """
        if not pages:
            return []

        try:
            now = datetime.now(timezone.utc).isoformat()
            batch_data = [
                {
                    "page_id": page.page_id,
                    "project_id": project_id,
                    "page_number": page.page_number,
                    "canvas_data": json.dumps(page.canvas_data) if page.canvas_data else None,
                    "thumbnail_url": page.thumbnail_url,
                    "updated_at": now,
                }
                for page in pages
            ]

            await self.client.table("project_pages").upsert(
                batch_data, on_conflict="page_id"
            ).execute()

            return pages

        except Exception as e:
            logger.error(f"Failed to batch save {len(pages)} pages for project {project_id}: {e}")
            raise

    async def get_page(self, project_id: str, page_id: str) -> Optional[Page]:
        """Get a specific page."""
        try:
            result = await self.client.table("project_pages").select("*").eq(
                "project_id", project_id
            ).eq("page_id", page_id).single().execute()

            if not result.data:
                return None

            return self._map_to_page(result.data)

        except APIError as e:
            if e.code == "PGRST116":
                return None
            logger.error(f"Failed to get page {page_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get page {page_id}: {e}")
            return None

    async def search(
        self,
        query: str,
        owner_id: Optional[str] = None,
        include_public: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[Project]:
        """Search projects by title/description."""
        try:
            # Build search query
            safe_query = sanitize_postgrest_query(query)
            db_query = self.client.table("projects").select("*").neq(
                "status", ProjectStatus.DELETED.value
            ).or_(f"title.ilike.%{safe_query}%,description.ilike.%{safe_query}%").order(
                "updated_at", desc=True
            ).range(offset, offset + limit - 1)

            if owner_id and not include_public:
                db_query = db_query.eq("user_id", owner_id)
            elif owner_id and include_public:
                db_query = db_query.or_(f"user_id.eq.{owner_id},is_public.eq.true")
            elif include_public:
                db_query = db_query.eq("is_public", True)

            result = await db_query.execute()

            return [self._map_to_project(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to search projects: {e}")
            return []

    def _map_to_entity(self, row: dict) -> Project:
        """
        Map database row to Project entity (BaseRepository requirement).

        This is the standard mapping method for BaseRepository.
        _map_to_project() is kept for backward compatibility.
        """
        return self._map_to_project(row)

    def _map_to_project(self, row: dict) -> Project:
        """Map database row to Project."""
        metadata = ProjectMetadata(
            title=row.get("title", "Untitled"),
            description=row.get("description"),
            tags=row.get("tags", []),
            thumbnail_url=row.get("thumbnail_url"),
            is_public=row.get("is_public", False),
            is_template=row.get("is_template", False),
            template_category=row.get("template_category"),
            view_count=row.get("view_count", 0),
            like_count=row.get("like_count", 0),
        )

        canvas_size = CanvasSize.from_string(row.get("canvas_size", "1080x1080"))

        # Parse canvas_data from JSON string if needed
        canvas_data = row.get("canvas_data")
        if isinstance(canvas_data, str):
            canvas_data = json.loads(canvas_data)

        return Project(
            project_id=row.get("project_id") or row.get("id"),
            owner_id=row.get("owner_id") or row.get("user_id"),
            metadata=metadata,
            canvas_size=canvas_size,
            status=ProjectStatus(row.get("status", "draft")),
            pages=[],  # Loaded separately if needed
            collaborators=row.get("collaborators", []),
            canvas_data=canvas_data,
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                if row.get("created_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
                if row.get("updated_at") else datetime.now(timezone.utc),
            # v3.33 Phase 2.6: Folder organization and starring
            folder_id=row.get("folder_id"),
            is_starred=row.get("is_starred", False),
            # Soft delete support
            deleted_at=datetime.fromisoformat(row["deleted_at"].replace("Z", "+00:00"))
                if row.get("deleted_at") else None,
            recovery_expires_at=datetime.fromisoformat(row["recovery_expires_at"].replace("Z", "+00:00"))
                if row.get("recovery_expires_at") else None,
        )

    def _map_to_page(self, row: dict) -> Page:
        """Map database row to Page."""
        canvas_data = row.get("canvas_data")
        if isinstance(canvas_data, str):
            canvas_data = json.loads(canvas_data)

        return Page(
            page_id=row["page_id"],
            page_number=row["page_number"],
            canvas_data=canvas_data,
            thumbnail_url=row.get("thumbnail_url"),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                if row.get("created_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
                if row.get("updated_at") else datetime.now(timezone.utc),
        )

    def _map_to_row(self, project: Project) -> dict:
        """Map Project to database row."""
        row = {
            "id": project.project_id,
            "user_id": project.owner_id,
            "title": project.metadata.title,
            "description": project.metadata.description,
            "tags": project.metadata.tags,
            "thumbnail_url": project.metadata.thumbnail_url,
            "is_public": project.metadata.is_public,
            "is_template": project.metadata.is_template,
            "template_category": project.metadata.template_category,
            "canvas_size": project.canvas_size.to_string(),
            "status": project.status.value,
            "collaborators": project.collaborators,
        }
        # v2.2.0: Add canvas_data (critical - this was missing, causing data loss on save)
        if project.canvas_data is not None:
            row["canvas_data"] = project.canvas_data
        # v2.1.0: Add idempotency_key if present
        if hasattr(project, 'idempotency_key') and project.idempotency_key:
            row["idempotency_key"] = project.idempotency_key
        # v3.33 Phase 2.6: Folder organization and starring
        if hasattr(project, 'folder_id'):
            row["folder_id"] = project.folder_id
        if hasattr(project, 'is_starred'):
            row["is_starred"] = project.is_starred
        return row

    # Extended Methods

    @retry_on_network_error()
    async def get_user_projects(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        include_canvas_data: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get user's projects with pagination.

        Args:
            user_id: User ID
            page: Page number
            limit: Items per page
            search: Search query for title
            include_canvas_data: Whether to include canvas_data

        Returns:
            List of project dicts
        """
        offset = (page - 1) * limit
        fields = "*" if include_canvas_data else "id, title, thumbnail_url, created_at, updated_at"

        query = self.client.table("projects").select(fields).eq(
            "user_id", user_id
        ).eq("is_deleted", False)

        if search:
            safe_search = sanitize_postgrest_query(search)
            query = query.ilike("title", f"%{safe_search}%")

        result = await query.order("updated_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data or []

    @retry_on_network_error()
    async def count_user_projects(
        self,
        user_id: str,
        search: Optional[str] = None
    ) -> int:
        """
        Count user's projects.

        Args:
            user_id: User ID
            search: Search query for title

        Returns:
            Project count
        """
        query = self.client.table("projects").select("id", count="exact").eq(
            "user_id", user_id
        ).eq("is_deleted", False)

        if search:
            safe_search = sanitize_postgrest_query(search)
            query = query.ilike("title", f"%{safe_search}%")

        result = await query.execute()
        return result.count or 0

    @retry_on_network_error()
    async def get_project_detail(
        self,
        project_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get project detail (must be owner or purchased).

        Business Rule: Owner can access own projects, buyers can access purchased projects.
        Security: Query-level access control to prevent IDOR - we only return data
        if the user has valid access rights.

        Args:
            project_id: Project ID
            user_id: User ID

        Returns:
            Project dict or None (returns None for both not-found and access-denied
            to prevent information disclosure about project existence)
        """
        # First try: Owner access (query-level filtering)
        owner_result = await self.client.table("projects").select("*").eq(
            "id", project_id
        ).eq("user_id", user_id).execute()

        if owner_result.data:
            return owner_result.data[0]

        # Second try: Check if user has purchased this project via marketplace
        # Correct query path: purchases → listings → check resource_id
        # Step 1: Find the listing for this project
        listing_result = await self.client.table("marketplace_listings").select(
            "id"
        ).eq("resource_type", "project").eq("resource_id", project_id).execute()

        if listing_result.data:
            listing_id = listing_result.data[0]["id"]
            # Step 2: Check if user purchased this listing
            purchase_result = await self.client.table("marketplace_purchases").select(
                "id"
            ).eq("user_id", user_id).eq("listing_id", listing_id).execute()

            if purchase_result.data:
                # User has purchased, fetch the project data
                project_result = await self.client.table("projects").select("*").eq(
                    "id", project_id
                ).execute()

                if project_result.data:
                    project_data = project_result.data[0]
                    # Don't return deleted projects even to purchasers
                    if not project_data.get("is_deleted", False):
                        return project_data

        # No access - return None (same response for not-found and access-denied)
        return None

    @retry_on_network_error()
    async def create_project(
        self,
        user_id: str,
        title: Optional[str] = None,
        canvas_data: Optional[dict] = None,
        tz: str = "UTC"
    ) -> Optional[Dict[str, Any]]:
        """
        Create new project.

        Args:
            user_id: User ID
            title: Project title
            canvas_data: Canvas data dict
            tz: Timezone

        Returns:
            Created project dict
        """
        result = await self.client.table("projects").insert({
            "user_id": user_id,
            "title": title or "Untitled Project",
            "canvas_data": canvas_data or {},
            "timezone": tz,
        }).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def duplicate_project(
        self,
        project_id: str,
        user_id: str,
        tz: str = "UTC"
    ) -> Optional[Dict[str, Any]]:
        """
        Duplicate a project.

        Args:
            project_id: Source project ID
            user_id: User ID
            tz: Timezone

        Returns:
            New project dict or None
        """
        original = await self.get_project_detail(project_id, user_id)
        if not original:
            return None

        new_title = f"{original.get('title', 'Project')} (Copy)"

        result = await self.client.table("projects").insert({
            "user_id": user_id,
            "title": new_title,
            "canvas_data": original.get("canvas_data", {}),
            "timezone": tz,
        }).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def save_project(
        self,
        project_id: str,
        user_id: str,
        canvas_data: Optional[dict] = None,
        thumbnail_url: Optional[str] = None,
        title: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Save/update project.

        Args:
            project_id: Project ID
            user_id: User ID (for ownership check)
            canvas_data: Canvas data
            thumbnail_url: Thumbnail URL
            title: Project title

        Returns:
            Updated project dict
        """
        update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}

        if canvas_data is not None:
            update_data["canvas_data"] = canvas_data
        if thumbnail_url is not None:
            update_data["thumbnail_url"] = thumbnail_url
        if title is not None:
            update_data["title"] = title

        result = await self.client.table("projects").update(update_data).eq(
            "id", project_id
        ).eq("user_id", user_id).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def soft_delete_project(
        self,
        project_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Soft delete project.

        Args:
            project_id: Project ID
            user_id: User ID (for ownership check)

        Returns:
            Updated project dict
        """
        result = await self.client.table("projects").update({
            "is_deleted": True,
            "deleted_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", project_id).eq("user_id", user_id).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def restore_project(
        self,
        project_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Restore soft-deleted project (admin function).

        Args:
            project_id: Project ID

        Returns:
            Updated project dict
        """
        result = await self.client.table("projects").update({
            "is_deleted": False,
            "deleted_at": None
        }).eq("id", project_id).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def user_restore_project(
        self,
        project_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Restore soft-deleted project (user function).

        Args:
            project_id: Project ID
            user_id: User ID (for ownership check)

        Returns:
            Updated project dict
        """
        result = await self.client.table("projects").update({
            "is_deleted": False,
            "deleted_at": None
        }).eq("id", project_id).eq("user_id", user_id).execute()

        return result.data[0] if result.data else None

    # Legacy method removed - use list_deleted_recoverable() from BaseRepository instead
    # This automatically filters expired records and returns Entity + total count

    @retry_on_network_error()
    async def permanently_hide_project(
        self,
        project_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Permanently hide project (stage 2 delete).

        Args:
            project_id: Project ID
            user_id: User ID (for ownership check)

        Returns:
            Updated project dict
        """
        result = await self.client.table("projects").update({
            "is_permanently_deleted": True
        }).eq("id", project_id).eq("user_id", user_id).eq("is_deleted", True).execute()

        return result.data[0] if result.data else None

    async def update_project_hash(
        self,
        project_id: str,
        new_hash: str,
        user_id: Optional[str] = None
    ):
        """
        Update project content hash.

        WS-1: Added user_id for ownership check (1C#14).

        Args:
            project_id: Project ID
            new_hash: New content hash
            user_id: User ID for ownership check (optional for backward compat)
        """
        query = self.client.table("projects").update({"content_hash": new_hash}).eq(
            "id", project_id
        )
        # WS-1: ownership check when user_id is provided
        if user_id:
            query = query.eq("user_id", user_id)
        await query.execute()

    @retry_on_network_error()
    async def get_all_projects_feed(
        self,
        offset: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get site-wide project feed (admin function) (v3.25: offset pagination).

        Args:
            offset: Number of records to skip
            limit: Number of records to return

        Returns:
            List of project dicts with user info
        """
        result = await self.client.table("projects").select(
            "id, title, thumbnail_url, created_at, user_id, profiles(username, avatar_url)"
        ).eq("is_deleted", False).order("created_at", desc=True).range(
            offset, offset + limit - 1
        ).execute()

        return result.data or []

    @retry_on_network_error()
    async def get_dashboard_projects(
        self,
        user_id: str,
        workspace_id: Optional[str] = None,
        view_type: str = "all",
        offset: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        include_canvas_data: bool = True,
        folder_id: Optional[str] = "NOT_SET",
    ) -> Dict[str, Any]:
        """
        Get projects for dashboard with view type filtering.

        P1-002 fix: Migrated from page-based to offset-based pagination (DDD compliant).
        v3.45: Added workspace_id filter for data isolation.

        Args:
            user_id: User ID
            workspace_id: Workspace ID for data isolation (optional for backward compat)
            view_type: "all", "bought", or "selling"
            offset: Number of records to skip
            limit: Items per page
            search: Search query
            include_canvas_data: Whether to include canvas_data

        Returns:
            Dict with items, total, offset, limit, and view-specific metadata
        """

        # Determine select fields
        # v3.37: Added folder_id and is_starred for folder filtering
        if include_canvas_data:
            select_fields = "id, title, thumbnail_url, canvas_data, source_listing_id, is_purchased, origin_owner_id, listing_status, marketplace_listing_id, folder_id, is_starred, created_at, updated_at"
        else:
            select_fields = "id, title, thumbnail_url, source_listing_id, is_purchased, origin_owner_id, listing_status, marketplace_listing_id, folder_id, is_starred, created_at, updated_at"

        # v3.30: Special handling for "selling" view - query via marketplace_listings
        if view_type == "selling":
            # Get project IDs from marketplace_listings (reliable source of truth)
            listings_result = await self.client.table("marketplace_listings").select(
                "resource_id"
            ).eq("seller_id", user_id).eq("resource_type", "project").eq("is_deleted", False).execute()

            selling_project_ids = [
                str(l["resource_id"]) for l in (listings_result.data or [])
                if l.get("resource_id")
            ]

            if not selling_project_ids:
                # No selling projects, return empty
                items = []
                total = 0
            else:
                # Query projects by IDs
                query = self.client.table("projects").select(select_fields).in_(
                    "id", selling_project_ids
                ).eq("is_deleted", False)

                # v3.45: Workspace isolation
                if workspace_id:
                    query = query.eq("workspace_id", workspace_id)

                # Apply folder filter
                if folder_id != "NOT_SET":
                    if folder_id is None:
                        query = query.is_("folder_id", "null")
                    else:
                        query = query.eq("folder_id", folder_id)

                if search and search.strip():
                    safe_search = sanitize_postgrest_query(search.strip())
                    query = query.ilike("title", f"%{safe_search}%")

                result = await query.order("updated_at", desc=True).order("id", desc=True).range(offset, offset + limit - 1).execute()
                items = result.data or []

                # Count with same filters
                count_query = self.client.table("projects").select("id", count="exact").in_(
                    "id", selling_project_ids
                ).eq("is_deleted", False)
                if workspace_id:
                    count_query = count_query.eq("workspace_id", workspace_id)
                if folder_id != "NOT_SET":
                    if folder_id is None:
                        count_query = count_query.is_("folder_id", "null")
                    else:
                        count_query = count_query.eq("folder_id", folder_id)
                if search and search.strip():
                    safe_search = sanitize_postgrest_query(search.strip())
                    count_query = count_query.ilike("title", f"%{safe_search}%")
                count_result = await count_query.execute()
                total = count_result.count or len(items)
        else:
            # Build base query for "all" and "bought" views
            query = self.client.table("projects").select(select_fields).eq(
                "user_id", user_id
            ).eq("is_deleted", False)

            # v3.45: Workspace isolation
            if workspace_id:
                query = query.eq("workspace_id", workspace_id)

            # Apply view type filter
            if view_type == "bought":
                query = query.eq("is_purchased", True)

            # Apply folder filter
            if folder_id != "NOT_SET":
                if folder_id is None:
                    query = query.is_("folder_id", "null")
                else:
                    query = query.eq("folder_id", folder_id)

            # Apply search filter
            if search and search.strip():
                safe_search = sanitize_postgrest_query(search.strip())
                query = query.ilike("title", f"%{safe_search}%")

            # Execute query
            result = await query.order("updated_at", desc=True).order("id", desc=True).range(offset, offset + limit - 1).execute()
            items = result.data or []

            # Get total count with same filters
            count_query = self.client.table("projects").select("id", count="exact").eq(
                "user_id", user_id
            ).eq("is_deleted", False)

            if workspace_id:
                count_query = count_query.eq("workspace_id", workspace_id)

            if view_type == "bought":
                count_query = count_query.eq("is_purchased", True)

            if folder_id != "NOT_SET":
                if folder_id is None:
                    count_query = count_query.is_("folder_id", "null")
                else:
                    count_query = count_query.eq("folder_id", folder_id)

            if search and search.strip():
                safe_search = sanitize_postgrest_query(search.strip())
                count_query = count_query.ilike("title", f"%{safe_search}%")

            count_result = await count_query.execute()
            total = count_result.count or len(items)

        # Get counts for all view types (for tab badges)
        # All projects count
        all_count_query = self.client.table("projects").select("id", count="exact").eq(
            "user_id", user_id
        ).eq("is_deleted", False)
        if workspace_id:
            all_count_query = all_count_query.eq("workspace_id", workspace_id)
        if search and search.strip():
            safe_search = sanitize_postgrest_query(search.strip())
            all_count_query = all_count_query.ilike("title", f"%{safe_search}%")
        all_count_result = await all_count_query.execute()
        all_count = all_count_result.count or 0

        # Bought projects count
        bought_count_query = self.client.table("projects").select("id", count="exact").eq(
            "user_id", user_id
        ).eq("is_deleted", False).eq("is_purchased", True)
        if workspace_id:
            bought_count_query = bought_count_query.eq("workspace_id", workspace_id)
        if search and search.strip():
            safe_search = sanitize_postgrest_query(search.strip())
            bought_count_query = bought_count_query.ilike("title", f"%{safe_search}%")
        bought_count_result = await bought_count_query.execute()
        bought_count = bought_count_result.count or 0

        # Selling projects count
        # v3.30: Only count approved listings (consistent with Total Selling stats)
        selling_listings_result = await self.client.table("marketplace_listings").select(
            "resource_id", count="exact"
        ).eq("seller_id", user_id).eq("resource_type", "project").eq(
            "is_deleted", False
        ).eq("moderation_status", "approved").execute()
        selling_count = selling_listings_result.count or 0

        counts = {
            "all": all_count,
            "bought": bought_count,
            "selling": selling_count,
        }

        # Enrich with marketplace listing data if present
        if items:
            marketplace_listing_ids = [
                item.get("marketplace_listing_id")
                for item in items
                if item.get("marketplace_listing_id")
            ]

            if marketplace_listing_ids:
                # Include listing_id (business ID) for API calls
                listings_res = await self.client.table("marketplace_listings").select(
                    "id, listing_id, title, description, moderation_status, is_public, allowed_tiers, price_credits, sales_count, usage_count, version, changelog"
                ).in_("id", marketplace_listing_ids).execute()

                # Map by database id (UUID) for lookup, but use listing_id as the returned id
                listings_map = {}
                for l in (listings_res.data or []):
                    db_id = l["id"]
                    # Replace 'id' with 'listing_id' so frontend uses business ID for API calls
                    l["id"] = l.pop("listing_id")
                    listings_map[db_id] = l

                for item in items:
                    db_listing_id = item.get("marketplace_listing_id")
                    if db_listing_id and db_listing_id in listings_map:
                        item["marketplace_listing"] = listings_map[db_listing_id]

        return {"items": items, "total": total, "offset": offset, "limit": limit, "view_type": view_type, "counts": counts}

    @retry_on_network_error()
    async def get_seller_project_stats(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get seller statistics for projects.

        v3.30: Only count approved listings (not pending/rejected).

        Args:
            user_id: User ID (maps to seller_id in marketplace_listings)

        Returns:
            Dict with total_selling, total_sales, unique_buyers, total_revenue
        """
        # Note: marketplace_listings uses seller_id (not user_id) and price_credits (not price)
        # v3.30: Only count listings that have been approved (not pending/rejected)
        listings = await self.client.table("marketplace_listings").select(
            "id, price_credits, sales_count, unique_buyers_count"
        ).eq("seller_id", user_id).eq("resource_type", "project").eq(
            "is_deleted", False
        ).eq("moderation_status", "approved").execute()

        data = listings.data or []
        total_sales = sum(l.get("sales_count", 0) for l in data)
        unique_buyers = sum(l.get("unique_buyers_count", 0) for l in data)
        total_revenue = sum(l.get("price_credits", 0) * l.get("sales_count", 0) for l in data)

        return {
            "total_selling": len(data),  # Matches SellerStatsResponse field name
            "total_sales": total_sales,
            "unique_buyers": unique_buyers,
            "total_revenue": float(total_revenue)
        }

    # ==========================================
    # v2.1.0: Idempotency Support
    # ==========================================

    async def get_by_idempotency_key(
        self,
        user_id: str,
        idempotency_key: str
    ) -> Optional[Project]:
        """
        Get project by idempotency key for a specific user.

        v2.1.0: Idempotency support - enables safe retries on creation.
        Industry best practice from Stripe/PayPal.

        Args:
            user_id: Owner's user ID
            idempotency_key: Client-generated unique key

        Returns:
            Project if found with matching key, None otherwise
        """
        if not idempotency_key or not user_id:
            return None

        try:
            result = await self.client.table("projects").select("*").eq(
                "user_id", user_id
            ).eq(
                "idempotency_key", idempotency_key
            ).single().execute()

            if not result.data:
                return None

            return self._map_to_project(result.data)

        except APIError as e:
            # single() throws PGRST116 when 0 or multiple rows returned
            if e.code == "PGRST116":
                return None
            logger.error(f"Failed to get project by idempotency_key: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get project by idempotency_key: {e}")
            return None

    # ==========================================
    # v3.33 Phase 2.6: Folder Organization and Starring
    # ==========================================

    @retry_on_network_error()
    async def move_to_folder(
        self,
        project_id: str,
        user_id: str,
        folder_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Move project to a folder (or root if folder_id is None).

        Args:
            project_id: Project ID
            user_id: User ID (for ownership check)
            folder_id: Target folder ID (None = move to root)

        Returns:
            Updated project dict or None if not found/unauthorized
        """
        result = await self.client.table("projects").update({
            "folder_id": folder_id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", project_id).eq("user_id", user_id).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def toggle_star(
        self,
        project_id: str,
        user_id: str,
        is_starred: bool
    ) -> Optional[Dict[str, Any]]:
        """
        Toggle project starred status.

        Args:
            project_id: Project ID
            user_id: User ID (for ownership check)
            is_starred: New starred status

        Returns:
            Updated project dict or None if not found/unauthorized
        """
        result = await self.client.table("projects").update({
            "is_starred": is_starred,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", project_id).eq("user_id", user_id).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def get_by_folder(
        self,
        user_id: str,
        folder_id: Optional[str],
        offset: int = 0,
        limit: int = 50,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get projects in a specific folder.

        Args:
            user_id: User ID
            folder_id: Folder ID (None = root/unfiled)
            offset: Number of records to skip
            limit: Number of records to return
            search: Optional search query

        Returns:
            List of project dicts
        """
        query = self.client.table("projects").select("*").eq(
            "user_id", user_id
        ).eq("is_deleted", False)

        if folder_id is None:
            query = query.is_("folder_id", "null")
        else:
            query = query.eq("folder_id", folder_id)

        if search and search.strip():
            safe_search = sanitize_postgrest_query(search.strip())
            query = query.ilike("title", f"%{safe_search}%")

        result = await query.order("is_starred", desc=True).order(
            "updated_at", desc=True
        ).range(offset, offset + limit - 1).execute()

        return result.data or []

    @retry_on_network_error()
    async def get_starred(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get starred projects.

        Args:
            user_id: User ID
            offset: Number of records to skip
            limit: Number of records to return

        Returns:
            List of starred project dicts
        """
        result = await self.client.table("projects").select("*").eq(
            "user_id", user_id
        ).eq("is_deleted", False).eq("is_starred", True).order(
            "updated_at", desc=True
        ).range(offset, offset + limit - 1).execute()

        return result.data or []

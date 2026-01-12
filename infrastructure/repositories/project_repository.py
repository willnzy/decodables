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

from domains.creation.repository import IProjectRepository
from domains.creation.aggregates.project import Project, Page
from domains.creation.value_objects import (
    ProjectStatus,
    CanvasSize,
    ProjectMetadata,
)
from domains.creation.exceptions import ProjectNotFoundException
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
                "project_id", project_id
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

        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}")
            return None

    async def save(self, project: Project) -> Project:
        """Persist project (upsert)."""
        try:
            data = self._map_to_row(project)
            await self.client.table("projects").upsert(
                data, on_conflict="project_id"
            ).execute()

            # Save pages
            for page in project.pages:
                await self.save_page(project.project_id, page)

            return project

        except Exception as e:
            logger.error(f"Failed to save project {project.project_id}: {e}")
            raise

    async def create(self, project: Project) -> Project:
        """Create a new project."""
        try:
            data = self._map_to_row(project)
            await self.client.table("projects").insert(data).execute()

            # Create initial pages
            for page in project.pages:
                await self.save_page(project.project_id, page)

            return project

        except Exception as e:
            logger.error(f"Failed to create project {project.project_id}: {e}")
            raise

    async def update(self, project: Project) -> Project:
        """Update existing project."""
        try:
            data = self._map_to_row(project)
            data["updated_at"] = datetime.utcnow().isoformat()

            result = await self.client.table("projects").update(data).eq(
                "project_id", project.project_id
            ).select("*").single().execute()

            if not result.data:
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
        # Get project first to find its UUID
        result = await self.client.table("projects").select("id").eq(
            "project_id", project_id
        ).single().execute()

        if not result.data:
            return False

        return await super().soft_delete(result.data["id"])

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
                "owner_id", owner_id
            ).neq("status", ProjectStatus.DELETED.value).order(
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
                "project_id", count="exact"
            ).eq("owner_id", owner_id).neq("status", ProjectStatus.DELETED.value)

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
                "updated_at": datetime.utcnow().isoformat(),
            }

            await self.client.table("project_pages").upsert(
                data, on_conflict="page_id"
            ).execute()

            return page

        except Exception as e:
            logger.error(f"Failed to save page {page.page_id}: {e}")
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
            db_query = self.client.table("projects").select("*").neq(
                "status", ProjectStatus.DELETED.value
            ).or_(f"title.ilike.%{query}%,description.ilike.%{query}%").order(
                "updated_at", desc=True
            ).range(offset, offset + limit - 1)

            if owner_id and not include_public:
                db_query = db_query.eq("owner_id", owner_id)
            elif owner_id and include_public:
                db_query = db_query.or_(f"owner_id.eq.{owner_id},is_public.eq.true")
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
            project_id=row["project_id"],
            owner_id=row["owner_id"],
            metadata=metadata,
            canvas_size=canvas_size,
            status=ProjectStatus(row.get("status", "draft")),
            pages=[],  # Loaded separately if needed
            collaborators=row.get("collaborators", []),
            canvas_data=canvas_data,
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                if row.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
                if row.get("updated_at") else datetime.utcnow(),
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
                if row.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
                if row.get("updated_at") else datetime.utcnow(),
        )

    def _map_to_row(self, project: Project) -> dict:
        """Map Project to database row."""
        return {
            "project_id": project.project_id,
            "owner_id": project.owner_id,
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
            query = query.ilike("title", f"%{search}%")

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
            query = query.ilike("title", f"%{search}%")

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

        # Second try: Check if user has purchased this project
        # Use a single query with join to verify both project existence AND purchase
        purchase_result = await self.client.table("marketplace_purchases").select(
            "id, projects!inner(id, user_id, title, canvas_data, thumbnail_url, created_at, updated_at, is_deleted)"
        ).eq("buyer_id", user_id).eq("project_id", project_id).execute()

        if purchase_result.data and purchase_result.data[0].get("projects"):
            project_data = purchase_result.data[0]["projects"]
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
        new_hash: str
    ):
        """
        Update project content hash.

        Args:
            project_id: Project ID
            new_hash: New content hash
        """
        await self.client.table("projects").update({"content_hash": new_hash}).eq(
            "id", project_id
        ).execute()

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
        view_type: str = "all",
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        include_canvas_data: bool = True
    ) -> Dict[str, Any]:
        """
        Get projects for dashboard with view type filtering.

        Args:
            user_id: User ID
            view_type: "all", "bought", or "selling"
            page: Page number
            limit: Items per page
            search: Search query
            include_canvas_data: Whether to include canvas_data

        Returns:
            Dict with items, total, page, and view-specific metadata
        """
        offset = (page - 1) * limit

        # Determine select fields
        if include_canvas_data:
            select_fields = "id, title, thumbnail_url, canvas_data, source_listing_id, is_purchased, origin_owner_id, listing_status, marketplace_listing_id, created_at, updated_at"
        else:
            select_fields = "id, title, thumbnail_url, source_listing_id, is_purchased, origin_owner_id, listing_status, marketplace_listing_id, created_at, updated_at"

        # Build base query
        query = self.client.table("projects").select(select_fields).eq(
            "user_id", user_id
        ).eq("is_deleted", False)

        # Apply view type filter
        if view_type == "bought":
            query = query.eq("is_purchased", True)
        elif view_type == "selling":
            query = query.not_.is_("listing_status", "null")

        # Apply search filter
        if search and search.strip():
            query = query.ilike("title", f"%{search.strip()}%")

        # Execute query
        result = await query.range(offset, offset + limit - 1).order("updated_at", desc=True).execute()
        items = result.data or []

        # Get total count with same filters
        count_query = self.client.table("projects").select("id", count="exact").eq(
            "user_id", user_id
        ).eq("is_deleted", False)

        if view_type == "bought":
            count_query = count_query.eq("is_purchased", True)
        elif view_type == "selling":
            count_query = count_query.not_.is_("listing_status", "null")

        if search and search.strip():
            count_query = count_query.ilike("title", f"%{search.strip()}%")

        count_result = await count_query.execute()
        total = count_result.count or len(items)

        # Enrich with marketplace listing data if present
        if items:
            marketplace_listing_ids = [
                item.get("marketplace_listing_id")
                for item in items
                if item.get("marketplace_listing_id")
            ]

            if marketplace_listing_ids:
                listings_res = await self.client.table("marketplace_listings").select(
                    "id, title, description, moderation_status, is_public, allowed_tiers, price_credits, sales_count, usage_count, version, changelog"
                ).in_("id", marketplace_listing_ids).execute()

                listings_map = {l["id"]: l for l in (listings_res.data or [])}

                for item in items:
                    listing_id = item.get("marketplace_listing_id")
                    if listing_id and listing_id in listings_map:
                        item["marketplace_listing_data"] = listings_map[listing_id]

        return {"items": items, "total": total, "page": page, "view_type": view_type}

    @retry_on_network_error()
    async def get_seller_project_stats(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get seller statistics for projects.

        Args:
            user_id: User ID

        Returns:
            Dict with total_listings, total_sales, total_revenue
        """
        listings = await self.client.table("marketplace_listings").select(
            "id, price, sales_count"
        ).eq("user_id", user_id).eq("resource_type", "project").execute()

        data = listings.data or []
        total_sales = sum(l.get("sales_count", 0) for l in data)
        total_revenue = sum(l.get("price", 0) * l.get("sales_count", 0) for l in data)

        return {
            "total_listings": len(data),
            "total_sales": total_sales,
            "total_revenue": total_revenue
        }

"""
Project Repository Extended - Additional methods for services/db migration.

@module infrastructure.repositories.project_repository_extended
@version 1.0.0

Extends SupabaseProjectRepository with additional methods needed for
backward compatibility with services/db/projects.py functions.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from core.database import DatabaseClient, retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseProjectRepositoryExtended:
    """
    Extended project repository with additional methods for projects table.

    This repository works directly with the "projects" table and provides
    all methods needed to replace services/db/projects.py functions.
    """

    def __init__(self, client: DatabaseClient):
        """
        Initialize repository with database client.

        Args:
            client: Supabase database client
        """
        self.client = client

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

        result = query.order("updated_at", desc=True).range(offset, offset + limit - 1).execute()
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

        result = query.execute()
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

        Args:
            project_id: Project ID
            user_id: User ID

        Returns:
            Project dict or None
        """
        result = self.client.table("projects").select("*").eq("id", project_id).execute()
        if not result.data:
            return None

        project = result.data[0]

        # Owner access
        if project.get("user_id") == user_id:
            return project

        # Check if purchased
        purchase = self.client.table("marketplace_purchases").select("id").eq(
            "buyer_id", user_id
        ).eq("project_id", project_id).execute()

        if purchase.data:
            return project

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
        result = self.client.table("projects").insert({
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

        result = self.client.table("projects").insert({
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

        result = self.client.table("projects").update(update_data).eq(
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
        result = self.client.table("projects").update({
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
        result = self.client.table("projects").update({
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
        result = self.client.table("projects").update({
            "is_deleted": False,
            "deleted_at": None
        }).eq("id", project_id).eq("user_id", user_id).execute()

        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def get_user_deleted_projects(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get user's deleted projects.

        Args:
            user_id: User ID
            page: Page number
            limit: Items per page

        Returns:
            List of deleted project dicts
        """
        offset = (page - 1) * limit
        result = self.client.table("projects").select(
            "id, title, thumbnail_url, deleted_at"
        ).eq("user_id", user_id).eq("is_deleted", True).order(
            "deleted_at", desc=True
        ).range(offset, offset + limit - 1).execute()

        return result.data or []

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
        result = self.client.table("projects").update({
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
        self.client.table("projects").update({"content_hash": new_hash}).eq(
            "id", project_id
        ).execute()

    @retry_on_network_error()
    async def get_all_projects_feed(
        self,
        page: int = 1,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get site-wide project feed (admin function).

        Args:
            page: Page number
            limit: Items per page

        Returns:
            List of project dicts with user info
        """
        offset = (page - 1) * limit
        result = self.client.table("projects").select(
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
        result = query.range(offset, offset + limit - 1).order("updated_at", desc=True).execute()
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

        count_result = count_query.execute()
        total = count_result.count or len(items)

        # Enrich with marketplace listing data if present
        if items:
            marketplace_listing_ids = [
                item.get("marketplace_listing_id")
                for item in items
                if item.get("marketplace_listing_id")
            ]

            if marketplace_listing_ids:
                listings_res = self.client.table("marketplace_listings").select(
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
        listings = self.client.table("marketplace_listings").select(
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

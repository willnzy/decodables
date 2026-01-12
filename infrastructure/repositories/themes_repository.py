"""Supabase implementation of ThemesRepository.

@module infrastructure.repositories.themes_repository
@version 2.2.0 (AsyncClient migration)

Changes in v2.2.0:
- Migrated all methods to use AsyncClient with await
- All .execute() calls now properly awaited

v2.1.0: Added CRUD, review workflow, and batch operations
"""

import logging
from datetime import date, datetime, timezone
from typing import List, Dict, Any, Optional, Set

logger = logging.getLogger(__name__)

# Table name
TABLE_NAME = "daily_themes"


class SupabaseThemesRepository:
    """Supabase implementation of ThemesRepository."""

    def __init__(self, supabase_client):
        """
        Initialize with Supabase client.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client

    # ==========================================
    # Read Operations
    # ==========================================

    async def get_by_id(self, theme_id: str) -> Optional[Dict[str, Any]]:
        """Get a theme by its ID."""
        try:
            result = await (
                self.supabase.table(TABLE_NAME)
                .select("*")
                .eq("id", theme_id)
                .eq("is_deleted", False)
                .single()
                .execute()
            )
            return result.data
        except Exception as e:
            # Single returns error if not found
            if "PGRST116" in str(e):
                return None
            logger.error(f"Failed to get theme by id {theme_id}: {e}")
            raise

    async def get_by_date(self, target_date: date) -> Optional[Dict[str, Any]]:
        """Get a theme for a specific date."""
        try:
            result = await (
                self.supabase.table(TABLE_NAME)
                .select("*")
                .eq("date", target_date.isoformat())
                .eq("is_deleted", False)
                .order("priority", desc=True)
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to get theme by date {target_date}: {e}")
            raise

    async def list_active_themes(self) -> List[Dict[str, Any]]:
        """Get all active themes ordered by priority (descending)."""
        try:
            result = await (
                self.supabase.table(TABLE_NAME)
                .select("*")
                .eq("is_active", True)
                .eq("is_deleted", False)
                .order("priority", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to list active themes: {e}")
            raise

    async def list_all(
        self,
        offset: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """List themes with pagination and filters."""
        try:
            query = (
                self.supabase.table(TABLE_NAME)
                .select("*")
                .eq("is_deleted", False)
            )

            # Apply filters
            if filters:
                if "category" in filters and filters["category"]:
                    query = query.eq("category", filters["category"])
                if "status" in filters and filters["status"]:
                    query = query.eq("status", filters["status"])
                if "review_status" in filters and filters["review_status"]:
                    query = query.eq("review_status", filters["review_status"])
                if "ai_generated" in filters and filters["ai_generated"] is not None:
                    query = query.eq("ai_generated", filters["ai_generated"])
                if "date_from" in filters and filters["date_from"]:
                    query = query.gte("date", filters["date_from"])
                if "date_to" in filters and filters["date_to"]:
                    query = query.lte("date", filters["date_to"])

            # Apply pagination and ordering
            query = query.order("date", desc=False).range(offset, offset + limit - 1)

            result = await query.execute()
            return result.data or []

        except Exception as e:
            logger.error(f"Failed to list themes: {e}")
            raise

    async def count_all(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count themes matching filters."""
        try:
            query = (
                self.supabase.table(TABLE_NAME)
                .select("id", count="exact")
                .eq("is_deleted", False)
            )

            # Apply filters
            if filters:
                if "category" in filters and filters["category"]:
                    query = query.eq("category", filters["category"])
                if "status" in filters and filters["status"]:
                    query = query.eq("status", filters["status"])
                if "review_status" in filters and filters["review_status"]:
                    query = query.eq("review_status", filters["review_status"])
                if "ai_generated" in filters and filters["ai_generated"] is not None:
                    query = query.eq("ai_generated", filters["ai_generated"])
                if "date_from" in filters and filters["date_from"]:
                    query = query.gte("date", filters["date_from"])
                if "date_to" in filters and filters["date_to"]:
                    query = query.lte("date", filters["date_to"])

            result = await query.execute()
            return result.count or 0

        except Exception as e:
            logger.error(f"Failed to count themes: {e}")
            raise

    # ==========================================
    # Write Operations
    # ==========================================

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new theme."""
        try:
            # Add timestamps
            now = datetime.now(timezone.utc).isoformat()
            data["created_at"] = now
            data["updated_at"] = now

            result = await self.supabase.table(TABLE_NAME).insert(data).execute()

            if not result.data:
                raise Exception("Failed to create theme - no data returned")

            return result.data[0]

        except Exception as e:
            logger.error(f"Failed to create theme: {e}")
            raise

    async def update(
        self, theme_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update an existing theme."""
        try:
            # Add updated timestamp
            data["updated_at"] = datetime.now(timezone.utc).isoformat()

            result = await (
                self.supabase.table(TABLE_NAME)
                .update(data)
                .eq("id", theme_id)
                .eq("is_deleted", False)
                .execute()
            )

            if result.data:
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to update theme {theme_id}: {e}")
            raise

    async def delete(self, theme_id: str) -> bool:
        """Soft delete a theme."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            result = await (
                self.supabase.table(TABLE_NAME)
                .update({
                    "is_deleted": True,
                    "deleted_at": now,
                    "updated_at": now,
                })
                .eq("id", theme_id)
                .eq("is_deleted", False)
                .execute()
            )

            return bool(result.data)

        except Exception as e:
            logger.error(f"Failed to delete theme {theme_id}: {e}")
            raise

    # ==========================================
    # Review Operations (v2.1)
    # ==========================================

    async def list_for_review(
        self,
        filters: Optional[Dict[str, Any]] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List themes for review."""
        try:
            query = (
                self.supabase.table(TABLE_NAME)
                .select("*")
                .eq("is_deleted", False)
            )

            # Apply filters
            if filters:
                if "review_status" in filters and filters["review_status"]:
                    query = query.eq("review_status", filters["review_status"])
                if "date_from" in filters and filters["date_from"]:
                    query = query.gte("date", filters["date_from"])
                if "date_to" in filters and filters["date_to"]:
                    query = query.lte("date", filters["date_to"])

            # Order by date ascending (nearest first)
            query = query.order("date", desc=False).range(offset, offset + limit - 1)

            result = await query.execute()
            return result.data or []

        except Exception as e:
            logger.error(f"Failed to list themes for review: {e}")
            raise

    async def count_for_review(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count themes for review."""
        try:
            query = (
                self.supabase.table(TABLE_NAME)
                .select("id", count="exact")
                .eq("is_deleted", False)
            )

            # Apply filters
            if filters:
                if "review_status" in filters and filters["review_status"]:
                    query = query.eq("review_status", filters["review_status"])
                if "date_from" in filters and filters["date_from"]:
                    query = query.gte("date", filters["date_from"])
                if "date_to" in filters and filters["date_to"]:
                    query = query.lte("date", filters["date_to"])

            result = await query.execute()
            return result.count or 0

        except Exception as e:
            logger.error(f"Failed to count themes for review: {e}")
            raise

    async def batch_update_review_status(
        self,
        theme_ids: List[str],
        review_status: str,
        reviewed_by: str,
    ) -> int:
        """Batch update review status for multiple themes."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            updated_count = 0

            for theme_id in theme_ids:
                result = await (
                    self.supabase.table(TABLE_NAME)
                    .update({
                        "review_status": review_status,
                        "reviewed_by": reviewed_by,
                        "reviewed_at": now,
                        "updated_at": now,
                    })
                    .eq("id", theme_id)
                    .eq("is_deleted", False)
                    .execute()
                )
                if result.data:
                    updated_count += 1

            return updated_count

        except Exception as e:
            logger.error(f"Failed to batch update review status: {e}")
            raise

    # ==========================================
    # Statistics Operations (v2.1)
    # ==========================================

    async def get_existing_dates(
        self, start_date: date, end_date: date
    ) -> Set[date]:
        """Get dates that already have themes."""
        try:
            result = await (
                self.supabase.table(TABLE_NAME)
                .select("date")
                .eq("is_deleted", False)
                .gte("date", start_date.isoformat())
                .lte("date", end_date.isoformat())
                .execute()
            )

            dates = set()
            for row in result.data or []:
                if row.get("date"):
                    dates.add(date.fromisoformat(row["date"]))

            return dates

        except Exception as e:
            logger.error(f"Failed to get existing dates: {e}")
            raise

    async def get_review_status_stats(
        self, start_date: date, end_date: date
    ) -> Dict[str, int]:
        """Get statistics of review statuses in date range."""
        try:
            result = await (
                self.supabase.table(TABLE_NAME)
                .select("review_status")
                .eq("is_deleted", False)
                .gte("date", start_date.isoformat())
                .lte("date", end_date.isoformat())
                .execute()
            )

            stats = {
                "pending": 0,
                "auto_approved": 0,
                "reviewed": 0,
                "rejected": 0,
            }

            for row in result.data or []:
                status = row.get("review_status", "pending")
                if status in stats:
                    stats[status] += 1

            return stats

        except Exception as e:
            logger.error(f"Failed to get review status stats: {e}")
            raise

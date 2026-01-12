"""
Base Repository - Abstract base class for all Supabase repositories.

@module infrastructure.repositories.base_repository
@version 2.0.0 (AsyncClient Migration - Phase 4)

Provides common functionality for soft delete, hard delete, and automatic filtering.
All concrete repositories should inherit from this class.

v2.0 Changes:
- Now requires AsyncClient via dependency injection (no lazy loading)
- All operations use native async/await
- Updated retry decorators to async version
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, TypeVar, Generic
from datetime import datetime, timezone, timedelta
import logging

from core.database import retry_on_network_error_async

logger = logging.getLogger(__name__)

# Type variable for domain entities
T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository with common CRUD operations.

    Provides:
    - Soft delete support (is_deleted flag)
    - Hard delete support (is_permanently_deleted flag or actual deletion)
    - Automatic filtering of deleted records
    - Common database operations
    - Lazy client initialization

    Subclasses must implement:
    - table_name: str property
    - _map_to_entity(row: Dict) -> T
    - _map_to_row(entity: T) -> Dict
    """

    def __init__(self, client):
        """
        Initialize repository with AsyncClient.

        v2.0: Client is now REQUIRED (no lazy loading).
        Must be injected via FastAPI dependency.

        Args:
            client: Supabase AsyncClient instance (required)

        Raises:
            ValueError: If client is None

        Example:
            from core.database.dependencies import get_async_db
            from fastapi import Depends

            async def some_endpoint(db = Depends(get_async_db)):
                repo = SomeRepository(client=db)
        """
        if client is None:
            raise ValueError(
                "AsyncClient is required for BaseRepository v2.0. "
                "Use FastAPI dependency injection: Depends(get_async_db)"
            )
        self._client = client

    @property
    def client(self):
        """Get AsyncClient instance."""
        return self._client

    @property
    @abstractmethod
    def table_name(self) -> str:
        """
        Name of the database table this repository manages.

        Returns:
            Table name as string
        """
        pass

    @abstractmethod
    def _map_to_entity(self, row: Dict[str, Any]) -> T:
        """
        Map database row to domain entity.

        Args:
            row: Database row as dict

        Returns:
            Domain entity instance
        """
        pass

    @abstractmethod
    def _map_to_row(self, entity: T) -> Dict[str, Any]:
        """
        Map domain entity to database row.

        Args:
            entity: Domain entity instance

        Returns:
            Database row as dict
        """
        pass

    # ============================================================
    # Soft Delete Operations
    # ============================================================

    async def _get_recovery_period_days(self) -> int:
        """
        获取软删除恢复期天数配置.

        从 system_configs 表读取 'soft_delete.recovery_period_days' 配置,
        如果读取失败或配置不存在,返回默认值 30 天.

        Returns:
            恢复期天数 (默认 30)
        """
        try:
            result = self.client.table("system_configs") \
                .select("value") \
                .eq("key", "soft_delete.recovery_period_days") \
                .single() \
                await .execute()

            if result.data and result.data.get("value"):
                return int(result.data["value"])
        except Exception as e:
            logger.warning(
                f"Failed to get recovery_period_days config: {e}, using default 30"
            )

        return 30  # 默认值

    @retry_on_network_error_async()
    async def soft_delete(self, id: str, user_id: Optional[str] = None) -> bool:
        """
        Soft delete a record (mark as deleted).

        自动计算恢复期过期时间:
        recovery_expires_at = deleted_at + recovery_period_days (默认30天)

        Args:
            id: Record ID
            user_id: Optional user ID for ownership check

        Returns:
            True if marked deleted, False otherwise

        Raises:
            Exception: If database operation fails
        """
        try:
            # 获取恢复期天数配置
            recovery_days = await self._get_recovery_period_days()

            # 计算删除时间和过期时间
            deleted_at = datetime.now(timezone.utc)
            recovery_expires_at = deleted_at + timedelta(days=recovery_days)

            query = self.client.table(self.table_name).update({
                "is_deleted": True,
                "deleted_at": deleted_at.isoformat(),
                "recovery_expires_at": recovery_expires_at.isoformat()
            }).eq("id", id)

            # Add user ownership check if provided
            if user_id:
                query = query.eq("user_id", user_id)

            result = await query.execute()

            if result.data:
                logger.info(
                    f"Soft deleted {self.table_name} record: {id}, "
                    f"recoverable until {recovery_expires_at.isoformat()}"
                )
                return True
            else:
                logger.warning(f"Failed to soft delete {self.table_name} record: {id} (not found or no permission)")
                return False

        except Exception as e:
            logger.error(f"Error soft deleting {self.table_name} record {id}: {e}")
            raise

    @retry_on_network_error_async()
    async def restore(self, id: str, user_id: Optional[str] = None) -> bool:
        """
        Restore a soft-deleted record.

        Args:
            id: Record ID
            user_id: Optional user ID for ownership check

        Returns:
            True if restored, False otherwise

        Raises:
            Exception: If database operation fails
        """
        try:
            query = self.client.table(self.table_name).update({
                "is_deleted": False,
                "deleted_at": None,
                "recovery_expires_at": None
            }).eq("id", id).eq("is_deleted", True)

            # Add user ownership check if provided
            if user_id:
                query = query.eq("user_id", user_id)

            result = await query.execute()

            if result.data:
                logger.info(f"Restored {self.table_name} record: {id}")
                return True
            else:
                logger.warning(f"Failed to restore {self.table_name} record: {id} (not found or no permission)")
                return False

        except Exception as e:
            logger.error(f"Error restoring {self.table_name} record {id}: {e}")
            raise

    @retry_on_network_error_async()
    async def list_deleted_recoverable(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 20
    ) -> tuple[List[T], int]:
        """
        查询用户的可恢复删除记录 (恢复期内的删除记录).

        只返回 is_deleted=true 且 recovery_expires_at > NOW() 的记录,
        即恢复期尚未过期的删除记录.

        Args:
            user_id: User ID
            offset: Offset for pagination
            limit: Limit for pagination

        Returns:
            Tuple of (list of entities, total count)

        Raises:
            Exception: If database operation fails
        """
        try:
            # 查询恢复期内的删除记录
            query = self.client.table(self.table_name) \
                .select("*", count="exact") \
                .eq("user_id", user_id) \
                .eq("is_deleted", True) \
                .gt("recovery_expires_at", datetime.now(timezone.utc).isoformat()) \
                .order("deleted_at", desc=True) \
                .range(offset, offset + limit - 1)

            result = await query.execute()

            entities = [self._map_to_entity(row) for row in result.data]
            total = result.count or 0

            return entities, total

        except Exception as e:
            logger.error(f"Error listing deleted recoverable records: {e}")
            raise

    # ============================================================
    # Hard Delete Operations
    # ============================================================

    @retry_on_network_error_async()
    async def hard_delete(
        self,
        id: str,
        user_id: Optional[str] = None,
        permanent_delete: bool = False
    ) -> bool:
        """
        Hard delete a record.

        Behavior:
        - If table has 'is_permanently_deleted' field and permanent_delete=False:
          Marks record as permanently deleted (Stage 2 delete)
        - If permanent_delete=True or no 'is_permanently_deleted' field:
          Physically removes record from database

        Args:
            id: Record ID
            user_id: Optional user ID for ownership check
            permanent_delete: Force physical deletion (default: False)

        Returns:
            True if deleted, False otherwise

        Raises:
            Exception: If database operation fails
        """
        try:
            # Check if table supports is_permanently_deleted (Stage 2 delete)
            supports_permanent_flag = await self._supports_permanent_delete_flag()

            if supports_permanent_flag and not permanent_delete:
                # Stage 2: Mark as permanently deleted
                query = self.client.table(self.table_name).update({
                    "is_permanently_deleted": True
                }).eq("id", id)

                # Only allow hard delete on already soft-deleted records
                query = query.eq("is_deleted", True)

                if user_id:
                    query = query.eq("user_id", user_id)

                result = await query.execute()

                if result.data:
                    logger.info(f"Permanently deleted (Stage 2) {self.table_name} record: {id}")
                    return True
                else:
                    logger.warning(
                        f"Failed to permanently delete {self.table_name} record: {id} "
                        f"(not found, not soft-deleted, or no permission)"
                    )
                    return False
            else:
                # Physical deletion from database
                query = self.client.table(self.table_name).delete().eq("id", id)

                if user_id:
                    query = query.eq("user_id", user_id)

                result = await query.execute()

                if result.data:
                    logger.info(f"Physically deleted {self.table_name} record: {id}")
                    return True
                else:
                    logger.warning(f"Failed to physically delete {self.table_name} record: {id} (not found or no permission)")
                    return False

        except Exception as e:
            logger.error(f"Error hard deleting {self.table_name} record {id}: {e}")
            raise

    async def _supports_permanent_delete_flag(self) -> bool:
        """
        Check if table supports is_permanently_deleted field.

        This is a heuristic check - we try to query a non-existent record
        with the field to see if it's supported.

        Returns:
            True if table has is_permanently_deleted column
        """
        try:
            # Try selecting is_permanently_deleted from a non-existent ID
            # If column exists, query succeeds (returns empty)
            # If column doesn't exist, query raises exception
            self.client.table(self.table_name).select(
                "is_permanently_deleted"
            await ).eq("id", "00000000-0000-0000-0000-000000000000").limit(1).execute()
            return True
        except Exception:
            # Column doesn't exist
            return False

    # ============================================================
    # Query Helpers with Automatic Filtering
    # ============================================================

    def _query_active_only(self, select: str = "*"):
        """
        Create query that automatically filters out deleted records.

        Args:
            select: Fields to select (default: "*")

        Returns:
            Supabase query builder with is_deleted = false filter
        """
        return self.client.table(self.table_name).select(select).eq("is_deleted", False)

    def _query_deleted_only(self, select: str = "*"):
        """
        Create query that only returns soft-deleted records.

        Args:
            select: Fields to select (default: "*")

        Returns:
            Supabase query builder with is_deleted = true filter
        """
        return self.client.table(self.table_name).select(select).eq("is_deleted", True)

    def _query_all(self, select: str = "*"):
        """
        Create query that returns all records (including deleted).

        Args:
            select: Fields to select (default: "*")

        Returns:
            Supabase query builder without delete filter
        """
        return self.client.table(self.table_name).select(select)

    # ============================================================
    # Common CRUD Operations
    # ============================================================

    @retry_on_network_error_async()
    async def get_by_id(
        self,
        id: str,
        include_deleted: bool = False
    ) -> Optional[T]:
        """
        Get entity by ID.

        Args:
            id: Record ID
            include_deleted: If True, include soft-deleted records (default: False)

        Returns:
            Domain entity or None if not found
        """
        try:
            if include_deleted:
                query = self._query_all()
            else:
                query = self._query_active_only()

            result = await query.eq("id", id).single().execute()

            if not result.data:
                return None

            return self._map_to_entity(result.data)

        except Exception as e:
            logger.error(f"Failed to get {self.table_name} by ID {id}: {e}")
            return None

    @retry_on_network_error_async()
    async def exists(self, id: str) -> bool:
        """
        Check if record exists (excluding deleted).

        Args:
            id: Record ID

        Returns:
            True if exists and not deleted
        """
        try:
            result = await self._query_active_only("id").eq("id", id).limit(1).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error checking existence of {self.table_name} {id}: {e}")
            return False

    @retry_on_network_error_async()
    async def count(
        self,
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False
    ) -> int:
        """
        Count records with optional filters.

        Args:
            filters: Optional filter dict (e.g., {"user_id": "123"})
            include_deleted: If True, include soft-deleted records (default: False)

        Returns:
            Count of matching records
        """
        try:
            if include_deleted:
                query = self._query_all("id")
            else:
                query = self._query_active_only("id")

            # Apply filters
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)

            result = await query.execute()
            return len(result.data) if result.data else 0

        except Exception as e:
            logger.error(f"Error counting {self.table_name} records: {e}")
            return 0

    # ============================================================
    # Bulk Operations
    # ============================================================

    @retry_on_network_error_async()
    async def get_deleted_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get user's deleted records.

        Args:
            user_id: User ID
            limit: Max results (default: 50)
            offset: Results to skip (default: 0)

        Returns:
            List of deleted record dicts (not mapped to entities)
        """
        try:
            result = self._query_deleted_only(
                "id, created_at, deleted_at"
            ).eq("user_id", user_id).order(
                "deleted_at", desc=True
            await ).range(offset, offset + limit - 1).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Error getting deleted {self.table_name} for user {user_id}: {e}")
            return []

    @retry_on_network_error_async()
    async def permanently_hide(
        self,
        id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Permanently hide record (Stage 2 delete).

        Only works if table has is_permanently_deleted field.
        Requires record to be already soft-deleted.

        Args:
            id: Record ID
            user_id: Optional user ID for ownership check

        Returns:
            Updated record dict or None if failed
        """
        try:
            query = self.client.table(self.table_name).update({
                "is_permanently_deleted": True
            }).eq("id", id).eq("is_deleted", True)

            if user_id:
                query = query.eq("user_id", user_id)

            result = await query.execute()

            if result.data:
                logger.info(f"Permanently hid {self.table_name} record: {id}")
                return result.data[0]
            else:
                logger.warning(f"Failed to permanently hide {self.table_name} record: {id}")
                return None

        except Exception as e:
            logger.error(f"Error permanently hiding {self.table_name} record {id}: {e}")
            raise

"""
Admin Logs Service - Admin-specific logs and audit operations.

@module domains.admin.admin_logs_service
@version 1.0.0

This service encapsulates admin-specific log operations:
- Error logs querying and statistics
- Operation logs querying and export
- Unified audit logs

WHY separate from LoggingService?
- LoggingService handles error log creation (write operations)
- AdminLogsService handles admin queries (read operations)
- Different security context (admin authentication required)
- Different repositories (ErrorLogs + AdminUsers)

Architecture: API → Container → Service → Repository
"""

import logging
from typing import Dict, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# =============================================================================
# Repository Protocols (DIP compliance)
# =============================================================================

@runtime_checkable
class ErrorLogsRepositoryProtocol(Protocol):
    """Protocol for error logs repository operations."""
    async def get_error_logs(
        self,
        error_level: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> Dict: ...
    async def get_error_stats(self, hours: int = 24) -> Dict: ...


@runtime_checkable
class AdminUsersRepositoryProtocol(Protocol):
    """Protocol for admin users repository operations (logs-related)."""
    async def admin_get_operation_logs(
        self,
        offset: int = 0,
        limit: int = 50,
        operation_type: Optional[str] = None,
        admin_id: Optional[str] = None,
        target_user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        source: Optional[str] = None,
    ) -> Dict: ...


class AdminLogsService:
    """
    Admin Logs Service.

    Handles all admin-specific log query operations.
    Provides unified interface for error logs, operation logs, and audit logs.
    """

    def __init__(
        self,
        error_logs_repo: ErrorLogsRepositoryProtocol,
        admin_repo: AdminUsersRepositoryProtocol,
    ):
        """
        Initialize Admin Logs Service with repository dependencies.

        WHY interface injection?
        - Dependency Inversion Principle (DIP)
        - Easy mocking for tests
        - Decouples from infrastructure

        Args:
            error_logs_repo: Error logs repository
            admin_repo: Admin users repository (for operation logs)
        """
        self._error_logs_repo = error_logs_repo
        self._admin_repo = admin_repo

    # =========================================================================
    # Error Logs
    # =========================================================================

    async def get_error_logs(
        self,
        error_level: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> Dict:
        """
        Get error logs with filtering.

        Args:
            error_level: Filter by error level
            start_date: Filter from date
            end_date: Filter to date
            offset: Pagination offset
            limit: Maximum results

        Returns:
            Dict with logs list and pagination info
        """
        return await self._error_logs_repo.get_error_logs(
            error_level=error_level,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit
        )

    async def get_error_stats(self, hours: int = 24) -> Dict:
        """
        Get error statistics for the specified time period.

        Args:
            hours: Time range in hours

        Returns:
            Dict with error statistics
        """
        return await self._error_logs_repo.get_error_stats(hours=hours)

    # =========================================================================
    # Operation Logs
    # =========================================================================

    async def get_operation_logs(
        self,
        offset: int = 0,
        limit: int = 50,
        operation_type: Optional[str] = None,
        admin_id: Optional[str] = None,
        target_user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict:
        """
        Get admin operation logs.

        Args:
            offset: Pagination offset
            limit: Maximum results
            operation_type: Filter by operation type
            admin_id: Filter by admin ID
            target_user_id: Filter by target user
            start_date: Filter from date
            end_date: Filter to date

        Returns:
            Dict with logs list and pagination info
        """
        return await self._admin_repo.admin_get_operation_logs(
            offset=offset,
            limit=limit,
            operation_type=operation_type,
            admin_id=admin_id,
            target_user_id=target_user_id,
            start_date=start_date,
            end_date=end_date,
        )

    async def export_operation_logs(
        self,
        operation_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100000,
    ) -> List[Dict]:
        """
        Get operation logs for export.

        Args:
            operation_type: Filter by operation type
            start_date: Filter from date
            end_date: Filter to date
            limit: Maximum results (default 100000 for export)

        Returns:
            List of log entries
        """
        result = await self._admin_repo.admin_get_operation_logs(
            offset=0,
            limit=limit,
            operation_type=operation_type,
            admin_id=None,
            target_user_id=None,
            start_date=start_date,
            end_date=end_date,
        )
        return result.get("logs", [])

    # =========================================================================
    # Unified Audit Logs
    # =========================================================================

    async def get_audit_logs(
        self,
        offset: int = 0,
        limit: int = 50,
        operation_type: Optional[str] = None,
        admin_id: Optional[str] = None,
        target_user_id: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        source: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict:
        """
        Get comprehensive audit logs with advanced filtering.

        Combines admin operations, webhook events, and system changes
        into unified queryable audit trail.

        Args:
            offset: Pagination offset
            limit: Maximum results
            operation_type: Filter by operation type
            admin_id: Filter by admin ID
            target_user_id: Filter by affected user
            target_type: Filter by target type
            target_id: Filter by specific resource ID
            source: Filter by action source
            start_date: Filter from date
            end_date: Filter to date

        Returns:
            Dict with logs, total, offset, limit, has_more
        """
        return await self._admin_repo.admin_get_operation_logs(
            offset=offset,
            limit=limit,
            operation_type=operation_type,
            admin_id=admin_id,
            target_user_id=target_user_id,
            target_type=target_type,
            target_id=target_id,
            source=source,
            start_date=start_date,
            end_date=end_date,
        )

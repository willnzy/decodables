"""
Support Service - Support and report management service.

@module domains.support.support_service
@version 3.0.0

Service for managing support tickets and marketplace reports.
Encapsulates business logic for report creation and retrieval.
"""

import logging
from typing import Dict, List, Any

from infrastructure.repositories.support_repository import SupabaseSupportRepository
from infrastructure.logging.activity_logger import log_activity

logger = logging.getLogger(__name__)


class ReportAlreadyExistsException(Exception):
    """Raised when user already reported this listing."""
    pass


class SupportService:
    """
    Service for support and report management.

    Handles marketplace content reports with business logic validation.

    Responsibilities:
    - Create marketplace content reports with duplicate detection
    - Retrieve user's reports with pagination
    - Activity logging for all report submissions

    Architecture: API → SupportService → Repository

    v3.0.0: Created for DDD compliance (MARKET-CRITICAL-1 fix)
    """

    def __init__(self, db_client):
        """
        Initialize SupportService.

        Args:
            db_client: Supabase database client
        """
        self.repository = SupabaseSupportRepository(db_client)

    # ==========================================
    # Public Methods
    # ==========================================

    async def create_report(
        self,
        user_id: str,
        listing_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Create a marketplace content report.

        Args:
            user_id: Reporter user ID
            listing_id: Listing being reported
            reason: Report reason

        Returns:
            Dict: Created report record

        Raises:
            ReportAlreadyExistsException: If user already reported this listing

        Example:
            >>> report = await service.create_report(
            ...     "user_123",
            ...     "listing_abc",
            ...     "Copyright violation"
            ... )
        """
        try:
            report = await self.repository.create_report(user_id, listing_id, reason)

            if report:
                # Log activity
                log_activity(user_id, "submit_report", {"listing_id": listing_id})

            return report

        except Exception as e:
            error_msg = str(e)
            # Translate repository exception to domain exception
            if "already reported" in error_msg.lower():
                raise ReportAlreadyExistsException("You have already reported this listing")
            # Re-raise other exceptions
            raise

    async def get_user_reports(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get reports submitted by a user with pagination.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            tuple: (reports, total_count)
                - reports: List of report records
                - total_count: Total number of matching records

        Example:
            >>> reports, total = await service.get_user_reports("user_123", page=1, limit=20)
            >>> print(f"Found {total} reports, showing {len(reports)}")
        """
        reports, total_count = await self.repository.get_user_reports_with_count(
            user_id, page, limit
        )

        return reports, total_count

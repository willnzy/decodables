"""
Moderation Service - Business logic for content moderation.

@module domains.moderation.service
@version 3.28 (DDD Compliant)

Changes in v3.28:
- Complete DDD Migration from api/admin/moderation.py (MOD-CRITICAL-1)
- All business logic moved to Service layer
- API layer only handles HTTP concerns
- Added retry + OOM protection to Repository calls
- Fixed total calculation bug (MOD-HIGH-1)
- Unified method signatures (MOD-MEDIUM-3)

Architecture:
- API → Service → Repository
- Service layer orchestrates multiple Repository calls
- Centralized logging and event recording
"""

import asyncio
import logging

from core.database import get_async_db_client
from typing import Optional, Dict, List, Tuple

from infrastructure.repositories import (
    SupabaseAdminModerationRepository,
    SupabaseAdminUsersRepository,
)
from domains.moderation.constants import (
    OP_LISTING_APPROVE,
    OP_LISTING_REJECT,
    OP_REPORT_RESPOND,
    VALID_REPORT_TRANSITIONS,
)

logger = logging.getLogger(__name__)


async def _get_repos() -> Tuple[SupabaseAdminModerationRepository, SupabaseAdminUsersRepository]:
    """
    Get repository instances.

    v3.29: Fixed async function declaration (SyntaxError fix).
    v3.28: DDD Migration helper.
    v3.30: Removed StatsRepository - admin operations should only log to admin_operations table.
    """
    db_client = await get_async_db_client()
    moderation_repo = SupabaseAdminModerationRepository(db_client)
    admin_users_repo = SupabaseAdminUsersRepository(db_client)
    return moderation_repo, admin_users_repo


# ==========================================
# Marketplace Moderation Functions
# ==========================================

async def get_moderation_list(
    status: Optional[str] = None,
    resource_type: Optional[str] = None,
    offset: int = 0,
    limit: int = 20
) -> Tuple[List[Dict], int]:
    """
    List marketplace listings for moderation.

    v3.28: DDD Migration - Uses Repository with retry + OOM protection.
    v3.28: MOD-HIGH-1 Fix - Returns tuple (items, total) instead of calculating len(items).

    Args:
        status: Filter by moderation status
        resource_type: Filter by resource type
        offset: Pagination offset
        limit: Maximum number of items to return

    Returns:
        Tuple of (items list, total count)
    """
    try:
        moderation_repo, _ = await _get_repos()
        items, total = await moderation_repo.admin_get_moderation_list(
            status=status,
            resource_type=resource_type,
            offset=offset,
            limit=limit
        )
        return (items, total)

    except Exception as e:
        logger.error(f"[Moderation] Failed to list moderation queue: {e}")
        return ([], 0)


async def get_moderation_detail(listing_id: str) -> Optional[Dict]:
    """
    Get moderation detail for a listing.

    v3.28: DDD Migration - Uses Repository.

    Args:
        listing_id: Listing ID

    Returns:
        Listing dict or None if not found
    """
    try:
        moderation_repo, _ = await _get_repos()
        item = await moderation_repo.admin_get_moderation_detail(listing_id)
        return item

    except Exception as e:
        logger.error(f"[Moderation] Failed to get moderation detail for {listing_id}: {e}")
        return None


async def approve_listing(listing_id: str, admin_id: str) -> Optional[Dict]:
    """
    Approve a marketplace listing.

    v3.28: DDD Migration - Business logic orchestration moved to Service layer.

    Args:
        listing_id: Listing ID
        admin_id: Admin user ID

    Returns:
        Result dict or None if failed
    """
    try:
        moderation_repo, admin_users_repo = await _get_repos()

        # Approve listing
        result = await moderation_repo.admin_approve_listing(listing_id, admin_id)
        if not result:
            logger.warning(f"[Moderation] Listing {listing_id} not found for approval")
            return None

        # Log admin operation (admin_operations table - for audit trail)
        await admin_users_repo.admin_log_operation(
            admin_id=admin_id,
            operation_type=OP_LISTING_APPROVE,
            target_user_id=result.get("seller_id"),
            details=f"Approved listing: {result.get('title', listing_id)[:50]}",
            reason=None
        )

        return result

    except Exception as e:
        logger.error(f"[Moderation] Failed to approve listing {listing_id}: {e}")
        raise  # Re-raise to API layer for proper error handling


async def reject_listing(listing_id: str, admin_id: str, reason: str) -> Optional[Dict]:
    """
    Reject a marketplace listing.

    v3.28: DDD Migration - Business logic orchestration moved to Service layer.

    Args:
        listing_id: Listing ID
        admin_id: Admin user ID
        reason: Rejection reason

    Returns:
        Result dict or None if failed
    """
    try:
        moderation_repo, admin_users_repo = await _get_repos()

        # Reject listing
        result = await moderation_repo.admin_reject_listing(listing_id, admin_id, reason)
        if not result:
            logger.warning(f"[Moderation] Listing {listing_id} not found for rejection")
            return None

        # Log admin operation (admin_operations table - for audit trail)
        await admin_users_repo.admin_log_operation(
            admin_id=admin_id,
            operation_type=OP_LISTING_REJECT,
            target_user_id=result.get("seller_id"),
            details=f"Rejected listing: {result.get('title', listing_id)[:50]}",
            reason=reason
        )

        return result

    except Exception as e:
        logger.error(f"[Moderation] Failed to reject listing {listing_id}: {e}")
        raise  # Re-raise to API layer for proper error handling


async def delete_listing(listing_id: str, admin_id: str) -> Optional[Dict]:
    """
    Soft-delete a marketplace listing.

    v3.28: DDD Migration - Business logic orchestration moved to Service layer.

    Args:
        listing_id: Listing ID
        admin_id: Admin user ID

    Returns:
        Result dict or None if failed
    """
    try:
        moderation_repo, admin_users_repo = await _get_repos()

        # Delete listing
        result = await moderation_repo.admin_delete_listing(listing_id)
        if not result:
            logger.warning(f"[Moderation] Listing {listing_id} not found for deletion")
            return None

        # Log admin operation (admin_operations table - for audit trail)
        await admin_users_repo.admin_log_operation(
            admin_id=admin_id,
            operation_type="listing_delete",
            target_user_id=result.get("seller_id"),
            details=f"Deleted listing: {result.get('title', listing_id)[:50]}",
            reason=None
        )

        return result

    except Exception as e:
        logger.error(f"[Moderation] Failed to delete listing {listing_id}: {e}")
        raise  # Re-raise to API layer for proper error handling


async def unpublish_listing(listing_id: str, admin_id: str) -> Optional[Dict]:
    """
    Force-unpublish a marketplace listing.

    v3.28: DDD Migration - Business logic orchestration moved to Service layer.

    Args:
        listing_id: Listing ID
        admin_id: Admin user ID

    Returns:
        Result dict or None if failed
    """
    try:
        moderation_repo, admin_users_repo = await _get_repos()

        # Unpublish listing
        result = await moderation_repo.admin_unpublish_listing(listing_id)
        if not result:
            logger.warning(f"[Moderation] Listing {listing_id} not found for unpublishing")
            return None

        # Log admin operation (admin_operations table - for audit trail)
        await admin_users_repo.admin_log_operation(
            admin_id=admin_id,
            operation_type="listing_unpublish",
            target_user_id=result.get("seller_id"),
            details=f"Unpublished listing: {result.get('title', listing_id)[:50]}",
            reason=None
        )

        return result

    except Exception as e:
        logger.error(f"[Moderation] Failed to unpublish listing {listing_id}: {e}")
        raise  # Re-raise to API layer for proper error handling


# ==========================================
# Content Reports Functions
# ==========================================

async def get_reports(
    status: Optional[str] = None,
    offset: int = 0,
    limit: int = 20
) -> Tuple[List[Dict], int, bool]:
    """
    Get content reports with pagination.

    v3.28: DDD Migration - Uses Repository.
    v3.28: MOD-HIGH-4 Fix - Single query returns both items and total.

    Args:
        status: Filter by report status
        offset: Pagination offset
        limit: Maximum number of items to return

    Returns:
        Tuple of (reports list, total count, has_more flag)
    """
    try:
        moderation_repo, _ = await _get_repos()

        # v3.28: Single query returns both items and total
        reports, total = await moderation_repo.admin_get_reports(
            status=status,
            offset=offset,
            limit=limit
        )

        has_more = offset + limit < total

        return (reports, total, has_more)

    except Exception as e:
        logger.error(f"[Moderation] Failed to get reports: {e}")
        return ([], 0, False)


async def get_reports_stats() -> Dict[str, int]:
    """
    Get reports statistics by status.

    v3.28: DDD Migration - Uses Repository.
    v3.28: MOD-MEDIUM-2 Fix - Single query with in-memory aggregation.

    Returns:
        Dict with counts by status
    """
    try:
        moderation_repo, _ = await _get_repos()
        stats = await moderation_repo.admin_get_reports_stats()
        return stats

    except Exception as e:
        logger.error(f"[Moderation] Failed to get reports stats: {e}")
        return {
            "pending": 0,
            "reviewed": 0,
            "resolved": 0,
            "dismissed": 0,
            "total": 0
        }


async def get_report_detail(report_id: str) -> Optional[Dict]:
    """
    Get detailed information about a specific report.

    v3.28: DDD Migration - Uses Repository.

    Args:
        report_id: Report ID

    Returns:
        Report dict or None if not found
    """
    try:
        moderation_repo, _ = await _get_repos()
        report = await moderation_repo.admin_get_report_detail(report_id)
        return report

    except Exception as e:
        logger.error(f"[Moderation] Failed to get report detail for {report_id}: {e}")
        return None


async def respond_to_report(
    report_id: str,
    admin_id: str,
    new_status: str,
    admin_response: Optional[str] = None
) -> Optional[Dict]:
    """
    Respond to a content report.

    v3.28: DDD Migration - Business logic orchestration moved to Service layer.
    v3.28: MOD-MEDIUM-3 Fix - Unified parameter name (new_status).

    Args:
        report_id: Report ID
        admin_id: Admin user ID
        new_status: New report status (reviewed/resolved/dismissed)
        admin_response: Optional admin response text

    Returns:
        Result dict or None if failed
    """
    try:
        moderation_repo, admin_users_repo = await _get_repos()

        # WS-14: 状态机护栏 — 检查当前报告状态是否允许转换
        current_report = await moderation_repo.admin_get_report_detail(report_id)
        if not current_report:
            logger.warning(f"[Moderation] Report {report_id} not found")
            return None

        current_status = current_report.get("status", "pending")
        allowed_transitions = VALID_REPORT_TRANSITIONS.get(current_status, set())
        if new_status not in allowed_transitions:
            raise ValueError(
                f"Cannot transition report from '{current_status}' to '{new_status}'. "
                f"Allowed transitions: {allowed_transitions or 'none (terminal state)'}"
            )

        # Respond to report
        result = await moderation_repo.admin_respond_to_report(
            report_id=report_id,
            admin_id=admin_id,
            new_status=new_status,
            admin_response=admin_response
        )

        if not result:
            logger.warning(f"[Moderation] Report {report_id} update failed")
            return None

        # Log admin operation (admin_operations table - for audit trail)
        await admin_users_repo.admin_log_operation(
            admin_id=admin_id,
            operation_type=OP_REPORT_RESPOND,
            target_user_id=result.get("reporter_id"),
            details=f"Report #{report_id[:8]}... → {new_status}",
            reason=admin_response
        )

        return result

    except Exception as e:
        logger.error(f"[Moderation] Failed to respond to report {report_id}: {e}")
        raise  # Re-raise to API layer for proper error handling

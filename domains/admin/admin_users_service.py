"""
Admin Users Service - Admin-specific user management operations.

@module domains.admin.admin_users_service
@version 1.0.0

This service encapsulates admin-specific user operations:
- User search and audit
- Credit adjustments with logging
- Tier changes with logging
- User discount creation
- Project and asset management

WHY separate from IdentityService?
- Admin operations require audit logging for all actions
- Different security context (admin authentication required)
- Cross-domain operations (users + projects + assets + analytics)
- Separates admin concerns from regular user operations

Architecture: API → Container → Service → Repository
"""

import logging
from typing import Dict, List, Optional, Protocol, runtime_checkable

from domains.billing.payment_service import get_customer_payments

logger = logging.getLogger(__name__)


# =============================================================================
# Repository Protocols (DIP compliance)
# =============================================================================

@runtime_checkable
class UserRepositoryProtocol(Protocol):
    """Protocol for user repository operations."""
    async def search_users(self, query: str, limit: int = 20) -> List[Dict]: ...
    async def get_users_by_tier(self, tier: str, offset: int = 0, limit: int = 100) -> List[Dict]: ...
    async def get_profile(self, user_id: str) -> Optional[Dict]: ...
    async def update_subscription_tier(self, user_id: str, tier: str, subscription_status: str) -> Optional[Dict]: ...
    async def create_user_discount(self, user_id: str, discount_percent: int, valid_days: int, target_plan: Optional[str]) -> Dict: ...


@runtime_checkable
class AdminUsersRepositoryProtocol(Protocol):
    """Protocol for admin users repository operations."""
    async def get_full_user_audit(self, user_id: str) -> Dict: ...
    async def admin_adjust_credits(self, user_id: str, amount: int, bucket: str, reason: Optional[str]) -> None: ...
    async def admin_log_operation(self, admin_id: str, operation_type: str, target_user_id: str, details: str, reason: Optional[str]) -> None: ...
    async def admin_get_user_projects(self, user_id: str, offset: int, limit: int, include_deleted: bool) -> Dict: ...


@runtime_checkable
class ProjectRepositoryProtocol(Protocol):
    """Protocol for project repository operations."""
    async def restore_project(self, project_id: str) -> Optional[Dict]: ...
    async def get_all_projects_feed(self, offset: int, limit: int) -> List[Dict]: ...


@runtime_checkable
class AssetRepositoryProtocol(Protocol):
    """Protocol for asset repository operations."""
    async def get_user_asset_usage(self, user_id: str, limit: int = 1000, top_n: int = 10) -> Dict: ...


@runtime_checkable
class AnalyticsRepositoryProtocol(Protocol):
    """Protocol for analytics repository operations."""
    async def get_user_env_stats(self, user_id: str, limit: int = 100) -> Dict: ...


# WS-17: Use canonical VALID_TIERS from identity constants (was duplicated here)
from domains.identity.constants import VALID_TIERS


class AdminUsersService:
    """
    Admin Users Service.

    Handles all admin-specific user operations with audit logging.
    All operations are logged for compliance and debugging.
    """

    def __init__(
        self,
        user_repo: UserRepositoryProtocol,
        admin_repo: AdminUsersRepositoryProtocol,
        project_repo: ProjectRepositoryProtocol,
        asset_repo: AssetRepositoryProtocol,
        analytics_repo: AnalyticsRepositoryProtocol,
    ):
        """
        Initialize Admin Users Service with repository dependencies.

        WHY interface injection?
        - Dependency Inversion Principle (DIP)
        - Easy mocking for tests
        - Decouples from infrastructure

        Args:
            user_repo: User repository
            admin_repo: Admin users repository (for audit and logging)
            project_repo: Project repository
            asset_repo: Asset repository
            analytics_repo: Analytics repository
        """
        self._user_repo = user_repo
        self._admin_repo = admin_repo
        self._project_repo = project_repo
        self._asset_repo = asset_repo
        self._analytics_repo = analytics_repo

    # =========================================================================
    # User Search and Audit
    # =========================================================================

    async def search_users(self, query: str, limit: int = 20) -> Dict:
        """
        Search users by query string.

        Args:
            query: Search keyword (user_id, email, or user_code)
            limit: Maximum results to return

        Returns:
            Dict with users list and count
        """
        users = await self._user_repo.search_users(query, limit=limit)
        return {"users": users, "count": len(users), "limit": limit}

    async def get_users_by_tier(
        self,
        tier: str,
        offset: int = 0,
        limit: int = 100
    ) -> Dict:
        """
        Get users by subscription tier.

        Args:
            tier: User tier (t1/t2/t3)
            offset: Pagination offset
            limit: Maximum results

        Returns:
            Dict with users, pagination info, and has_more flag

        Raises:
            ValueError: If tier is invalid
        """
        tier_lower = tier.lower()
        if tier_lower not in VALID_TIERS:
            raise ValueError(f"Invalid tier. Must be one of: {', '.join(VALID_TIERS)}")

        users = await self._user_repo.get_users_by_tier(tier_lower, offset=offset, limit=limit)
        return {
            "users": users,
            "count": len(users),
            "tier": tier_lower,
            "offset": offset,
            "limit": limit,
            "has_more": len(users) >= limit
        }

    async def get_user_audit(self, user_id: str) -> Dict:
        """
        Get full user audit data.

        Args:
            user_id: User ID

        Returns:
            Complete audit data for the user
        """
        return await self._admin_repo.get_full_user_audit(user_id)

    # =========================================================================
    # Credit and Tier Management
    # =========================================================================

    async def adjust_credits(
        self,
        user_id: str,
        amount: int,
        bucket: str,
        reason: Optional[str],
        admin_id: str
    ) -> Dict:
        """
        Adjust user credits with admin logging.

        Args:
            user_id: Target user ID
            amount: Credit amount (positive or negative)
            bucket: Credit bucket (monthly/permanent)
            reason: Reason for adjustment
            admin_id: Admin performing the action

        Returns:
            Status dict
        """
        await self._admin_repo.admin_adjust_credits(user_id, amount, bucket, reason)
        await self._admin_repo.admin_log_operation(
            admin_id=admin_id,
            operation_type="credit_adjust",
            target_user_id=user_id,
            details=f"{'+' if amount > 0 else ''}{amount} {bucket} credits",
            reason=reason,
        )
        return {"status": "ok"}

    async def update_user_tier(
        self,
        user_id: str,
        new_tier: str,
        admin_id: str
    ) -> Dict:
        """
        Update user tier with admin logging.

        Args:
            user_id: Target user ID
            new_tier: New tier value
            admin_id: Admin performing the action

        Returns:
            Status dict
        """
        old_profile = await self._user_repo.get_profile(user_id)
        old_tier = old_profile.get("tier", "unknown") if old_profile else "unknown"

        subscription_status = "active" if new_tier in ["t2", "t3"] else "inactive"
        await self._user_repo.update_subscription_tier(user_id, new_tier, subscription_status=subscription_status)

        await self._admin_repo.admin_log_operation(
            admin_id=admin_id,
            operation_type="tier_change",
            target_user_id=user_id,
            details=f"{old_tier} → {new_tier}",
            reason=None,
        )
        return {"status": "ok"}

    async def create_user_discount(
        self,
        user_id: str,
        discount_percent: int,
        valid_days: int,
        target_plan: Optional[str],
        admin_id: str
    ) -> Dict:
        """
        Create user-specific discount with admin logging.

        Args:
            user_id: Target user ID
            discount_percent: Discount percentage (1-100)
            valid_days: Days the discount is valid
            target_plan: Optional target plan
            admin_id: Admin performing the action

        Returns:
            Created discount data
        """
        discount = await self._user_repo.create_user_discount(
            user_id,
            discount_percent,
            valid_days,
            target_plan,
        )

        await self._admin_repo.admin_log_operation(
            admin_id=admin_id,
            operation_type="discount_create",
            target_user_id=user_id,
            details=f"{discount_percent}% off for {valid_days} days" + (f" on {target_plan}" if target_plan else ""),
            reason=None,
        )

        return discount

    # =========================================================================
    # User Data Access
    # =========================================================================

    async def get_user_payments(self, user_id: str) -> Dict:
        """
        Get user's Stripe payment history.

        Args:
            user_id: User ID

        Returns:
            Dict with payments list and Stripe customer ID

        Raises:
            ValueError: If user not found
        """
        profile = await self._user_repo.get_profile(user_id)
        if not profile:
            raise ValueError("User not found")

        stripe_customer_id = profile.get("stripe_customer_id")
        if not stripe_customer_id:
            return {"payments": [], "message": "No Stripe customer associated"}

        try:
            payments = get_customer_payments(stripe_customer_id)
            return {"payments": payments, "stripe_customer_id": stripe_customer_id}
        except Exception as e:
            logger.error(f"[AdminUsersService] Failed to fetch payments for {user_id}: {e}")
            raise RuntimeError("Failed to fetch payment history")

    async def get_user_projects(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 20,
        include_deleted: bool = True
    ) -> Dict:
        """
        Get user's projects.

        Args:
            user_id: User ID
            offset: Pagination offset
            limit: Maximum results
            include_deleted: Include soft-deleted projects

        Returns:
            Dict with projects list
        """
        return await self._admin_repo.admin_get_user_projects(user_id, offset, limit, include_deleted)

    async def get_user_asset_usage(self, user_id: str, top_n: int = 10) -> Dict:
        """
        Get user's asset usage statistics.

        Args:
            user_id: User ID
            top_n: Number of top assets to return

        Returns:
            Asset usage statistics
        """
        stats = await self._asset_repo.get_user_asset_usage(user_id, limit=1000, top_n=top_n)
        return {"user_id": user_id, **stats}

    async def get_user_env_stats(self, user_id: str, limit: int = 100) -> Dict:
        """
        Get user's environment statistics.

        Args:
            user_id: User ID
            limit: Maximum events to analyze

        Returns:
            Environment statistics (browsers, devices, OS, referrers)
        """
        stats = await self._analytics_repo.get_user_env_stats(user_id, limit=limit)
        return {
            "user_id": user_id,
            "sample_size": stats["total_events"],
            "browsers": stats["browsers"],
            "devices": stats["devices"],
            "os_types": stats["os_stats"],
            "referrers": dict(sorted(stats["referrers"].items(), key=lambda x: x[1], reverse=True)[:10]),
            "screen_sizes": {},
        }

    # =========================================================================
    # Project Management
    # =========================================================================

    async def restore_project(self, project_id: str) -> Optional[Dict]:
        """
        Restore a deleted project.

        Args:
            project_id: Project ID

        Returns:
            Restored project data or None if not found
        """
        return await self._project_repo.restore_project(project_id)

    async def get_projects_feed(self, offset: int = 0, limit: int = 50) -> Dict:
        """
        Get site-wide project feed.

        Args:
            offset: Pagination offset
            limit: Maximum results

        Returns:
            Dict with projects list and pagination info
        """
        items = await self._project_repo.get_all_projects_feed(offset, limit)
        return {"items": items, "total": len(items), "offset": offset, "limit": limit}

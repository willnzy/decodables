"""
User Profile Service - Business logic for user profile operations.

@module domains.identity.user_profile_service
@version 1.1.0 (DIP Compliance)

This Service encapsulates user profile-related business logic:
- User profile retrieval with credit calculations
- Credit history management
- Purchase history
- Notification management
- User preferences (timezone)

v1.1.0 Changes:
- Migrated from concrete repository types to interface types (DIP)
- Service now depends on abstractions, not implementations
- Enables easy mocking in tests and provider switching

Architecture: Service → Interface → Repository → Database
"""

import logging
from typing import Dict, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# =============================================================================
# Repository Interfaces (Protocol-based for structural typing)
# =============================================================================
# WHY Protocol instead of ABC?
# - More flexible: works with any class that has the required methods
# - Better for duck typing: doesn't require explicit inheritance
# - Easier testing: mock objects just need matching methods

@runtime_checkable
class UserRepositoryProtocol(Protocol):
    """Protocol for user repository operations."""
    async def get_profile(self, user_id: str) -> Optional[Dict]: ...
    async def update_timezone(self, user_id: str, timezone: str) -> Optional[Dict]: ...


@runtime_checkable
class CreditRepositoryProtocol(Protocol):
    """Protocol for credit repository operations."""
    async def check_and_reset_monthly_credits_if_needed(self, user_id: str) -> None: ...
    async def get_credit_history(self, user_id: str, page: int, limit: int) -> Dict: ...


@runtime_checkable
class ListingRepositoryProtocol(Protocol):
    """Protocol for listing repository operations."""
    async def get_user_purchases(self, user_id: str) -> List[Dict]: ...


@runtime_checkable
class NotificationRepositoryProtocol(Protocol):
    """Protocol for notification repository operations."""
    async def get_user_notifications(self, user_id: str, unread_only: bool = False) -> List[Dict]: ...
    async def mark_as_read(self, notification_id: str, user_id: str) -> Optional[Dict]: ...
    async def mark_all_as_read(self, user_id: str) -> None: ...


class UserProfileService:
    """
    User Profile Service.

    Handles all user profile-related operations including credits, purchases,
    notifications, and preferences.

    v1.1.0: Depends on Protocol interfaces, not concrete implementations.
    This enables:
    - Easy mocking in unit tests
    - Provider switching (Supabase -> other DB)
    - Loose coupling between layers
    """

    def __init__(
        self,
        user_repo: UserRepositoryProtocol,
        credit_repo: CreditRepositoryProtocol,
        listing_repo: ListingRepositoryProtocol,
        notif_repo: NotificationRepositoryProtocol,
    ):
        """
        Initialize User Profile Service with interface dependencies.

        WHY interface injection?
        - Dependency Inversion Principle (DIP): High-level modules should not
          depend on low-level modules. Both should depend on abstractions.
        - Enables constructor injection pattern (testable, explicit dependencies)

        Args:
            user_repo: User repository (must implement UserRepositoryProtocol)
            credit_repo: Credit repository (must implement CreditRepositoryProtocol)
            listing_repo: Listing repository (must implement ListingRepositoryProtocol)
            notif_repo: Notification repository (must implement NotificationRepositoryProtocol)
        """
        self._user_repo = user_repo
        self._credit_repo = credit_repo
        self._listing_repo = listing_repo
        self._notif_repo = notif_repo

    async def get_user_profile(self, user_id: str) -> Dict:
        """
        Get user profile with credits and member status.

        This method:
        1. Resets monthly credits if needed
        2. Fetches user profile
        3. Calculates total credits
        4. Determines member status

        Args:
            user_id: User ID

        Returns:
            User profile dict with credits_total and is_member fields
        """
        try:
            # Reset monthly credits when needed
            await self._credit_repo.check_and_reset_monthly_credits_if_needed(user_id)

            # Get user profile
            profile = await self._user_repo.get_profile(user_id)
            if not profile:
                logger.warning(f"[UserProfileService] Profile not found for user {user_id}")
                return {}

            # Calculate total credits
            credits_total = profile.get("credits_monthly", 0) + profile.get("credits_permanent", 0)

            # Determine member status
            is_member = self._is_member(profile.get("tier"))

            return {
                **profile,
                "credits_total": credits_total,
                "is_member": is_member
            }

        except Exception as e:
            logger.error(f"[UserProfileService] Failed to get profile for {user_id}: {e}")
            raise

    async def get_credit_history(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 20
    ) -> Dict:
        """
        Get paginated credit history.

        Args:
            user_id: User ID
            offset: Offset for pagination
            limit: Number of items per page

        Returns:
            Dict with items, total, offset, and limit
        """
        try:
            # Convert offset/limit to page format for existing repository method
            page = (offset // limit) + 1
            result = await self._credit_repo.get_credit_history(user_id, page, limit)

            return {
                "items": result["items"],
                "total": result["total"],
                "offset": offset,
                "limit": limit
            }

        except Exception as e:
            logger.error(f"[UserProfileService] Failed to get credit history for {user_id}: {e}")
            raise

    async def get_purchases(self, user_id: str) -> List[Dict]:
        """
        Get user's marketplace purchases.

        Args:
            user_id: User ID

        Returns:
            List of purchase records
        """
        try:
            return await self._listing_repo.get_user_purchases(user_id)

        except Exception as e:
            logger.error(f"[UserProfileService] Failed to get purchases for {user_id}: {e}")
            raise

    async def get_notifications(
        self,
        user_id: str,
        unread_only: bool = False
    ) -> List[Dict]:
        """
        Get user notifications.

        Args:
            user_id: User ID
            unread_only: If True, return only unread notifications

        Returns:
            List of notification records
        """
        try:
            return await self._notif_repo.get_user_notifications(
                user_id,
                unread_only=unread_only
            )

        except Exception as e:
            logger.error(f"[UserProfileService] Failed to get notifications for {user_id}: {e}")
            raise

    async def mark_notification_read(self, notification_id: str, user_id: str) -> bool:
        """
        Mark a notification as read.

        Args:
            notification_id: Notification ID
            user_id: User ID (for ownership verification)

        Returns:
            True if marked successfully, False if not found

        Raises:
            Exception: If operation fails
        """
        try:
            result = await self._notif_repo.mark_as_read(notification_id, user_id)
            return result is not None

        except Exception as e:
            logger.error(
                f"[UserProfileService] Failed to mark notification {notification_id} "
                f"as read for {user_id}: {e}"
            )
            raise

    async def mark_all_notifications_read(self, user_id: str) -> None:
        """
        Mark all notifications as read for a user.

        Args:
            user_id: User ID

        Raises:
            Exception: If operation fails
        """
        try:
            await self._notif_repo.mark_all_as_read(user_id)

        except Exception as e:
            logger.error(f"[UserProfileService] Failed to mark all notifications as read for {user_id}: {e}")
            raise

    async def update_timezone(self, user_id: str, timezone: str) -> bool:
        """
        Update user's timezone preference.

        Args:
            user_id: User ID
            timezone: Timezone string (IANA format, e.g., "America/New_York")

        Returns:
            True if updated successfully, False if failed

        Raises:
            Exception: If operation fails
        """
        try:
            result = await self._user_repo.update_timezone(user_id, timezone)
            return result is not None

        except Exception as e:
            logger.error(f"[UserProfileService] Failed to update timezone for {user_id}: {e}")
            raise

    def _is_member(self, tier: Optional[str]) -> bool:
        """
        Check if user is a paying member.

        Args:
            tier: User tier (free/starter/pro)

        Returns:
            True if user is starter or pro tier
        """
        tier_normalized = (tier or "t1").lower()
        return tier_normalized in ["t2", "t3"]

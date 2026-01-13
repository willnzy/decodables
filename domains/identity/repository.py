"""
User Repository Interface - Abstract data access for identity domain.

@module domains.identity.repository
@version 1.0.0

This defines the repository interface (port) for user operations.
Concrete implementations live in infrastructure/repositories/.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple

from .aggregates.user_profile import UserProfile
from .value_objects import UserTier, OnboardingStep


class IUserRepository(ABC):
    """
    Repository interface for user operations.

    Follows the Repository pattern from DDD.
    Infrastructure layer provides the concrete implementation.
    """

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[UserProfile]:
        """
        Get user profile by user ID.

        Args:
            user_id: The user's unique identifier (Clerk ID)

        Returns:
            UserProfile aggregate or None if not found
        """
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[UserProfile]:
        """
        Get user profile by email.

        Args:
            email: User's email address

        Returns:
            UserProfile aggregate or None if not found
        """
        pass

    @abstractmethod
    async def save(self, user_profile: UserProfile) -> UserProfile:
        """
        Persist user profile.

        Creates new user if not exists, updates if exists.

        Args:
            user_profile: The UserProfile aggregate to save

        Returns:
            Saved UserProfile aggregate
        """
        pass

    @abstractmethod
    async def create(self, user_profile: UserProfile) -> UserProfile:
        """
        Create a new user profile.

        Args:
            user_profile: The UserProfile to create

        Returns:
            Created UserProfile

        Raises:
            UserAlreadyExistsException: If user already exists
        """
        pass

    @abstractmethod
    async def create_or_get(
        self,
        user_profile: UserProfile,
        source: str
    ) -> Tuple[UserProfile, bool]:
        """
        Create user or get existing (idempotent operation).

        This method is designed to handle concurrent user creation from
        multiple sources (e.g., Webhook and JIT) without race conditions.

        Business Pattern:
        - Stripe: Idempotent Requests
        - AWS: Idempotent APIs
        - Kubernetes: Declarative Apply

        Args:
            user_profile: The UserProfile to create
            source: Creation source ('webhook' or 'jit')

        Returns:
            Tuple of (UserProfile, was_created)
            - was_created=True: User was newly created
            - was_created=False: User already existed

        Implementation Notes:
        - Uses database-level atomic operations (RPC)
        - First-come-first-served: whoever creates first wins
        - Safe for concurrent calls with same user_id
        - Logs all creation attempts for monitoring
        """
        pass

    @abstractmethod
    async def update(self, user_profile: UserProfile) -> UserProfile:
        """
        Update existing user profile.

        Args:
            user_profile: The UserProfile to update

        Returns:
            Updated UserProfile

        Raises:
            UserNotFoundException: If user doesn't exist
        """
        pass

    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        """
        Delete a user profile.

        Args:
            user_id: User ID to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, user_id: str) -> bool:
        """
        Check if user exists.

        Args:
            user_id: User ID to check

        Returns:
            True if exists
        """
        pass

    @abstractmethod
    async def get_by_tier(
        self,
        tier: UserTier,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserProfile]:
        """
        Get users by subscription tier.

        Args:
            tier: Subscription tier to filter by
            limit: Maximum results
            offset: Results to skip

        Returns:
            List of UserProfile aggregates
        """
        pass

    @abstractmethod
    async def get_users_needing_onboarding(
        self,
        limit: int = 100
    ) -> List[UserProfile]:
        """
        Get users who haven't completed onboarding.

        Args:
            limit: Maximum results

        Returns:
            List of UserProfile aggregates
        """
        pass

    @abstractmethod
    async def update_tier(
        self,
        user_id: str,
        new_tier: UserTier,
        stripe_customer_id: Optional[str] = None
    ) -> UserProfile:
        """
        Update user's subscription tier.

        Args:
            user_id: User ID
            new_tier: New tier
            stripe_customer_id: Stripe customer ID if applicable

        Returns:
            Updated UserProfile
        """
        pass

    @abstractmethod
    async def update_onboarding_step(
        self,
        user_id: str,
        step: OnboardingStep
    ) -> UserProfile:
        """
        Update user's onboarding progress.

        Args:
            user_id: User ID
            step: New onboarding step

        Returns:
            Updated UserProfile
        """
        pass

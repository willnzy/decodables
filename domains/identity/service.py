"""
Identity Domain Service - Orchestrates user profile operations.

@module domains.identity.service
@version 1.0.0

This service handles domain logic that doesn't naturally belong to aggregates.
It coordinates operations but delegates persistence to the repository.
"""

from typing import Optional, List

from .aggregates.user_profile import UserProfile
from .repository import IUserRepository
from .value_objects import UserTier, OnboardingStep, UserPreferences
from .exceptions import (
    UserNotFoundException,
    UserAlreadyExistsException,
    InvalidUserDataException,
)


class IdentityService:
    """
    Domain service for identity operations.

    This service:
    - Manages user lifecycle
    - Handles tier changes
    - Tracks onboarding progress
    """

    def __init__(self, repository: IUserRepository):
        """
        Initialize identity service with repository.

        Args:
            repository: User repository implementation
        """
        self._repository = repository

    async def get_user(self, user_id: str) -> Optional[UserProfile]:
        """
        Get user profile by ID.

        Args:
            user_id: User ID

        Returns:
            UserProfile or None
        """
        return await self._repository.get_by_id(user_id)

    async def get_user_or_raise(self, user_id: str) -> UserProfile:
        """
        Get user profile or raise exception.

        Args:
            user_id: User ID

        Returns:
            UserProfile

        Raises:
            UserNotFoundException: If user not found
        """
        user = await self._repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(user_id)
        return user

    async def create_user(
        self,
        user_id: str,
        email: str,
        display_name: Optional[str] = None
    ) -> UserProfile:
        """
        Create a new user profile.

        Called when user signs up via Clerk webhook.

        Args:
            user_id: Clerk user ID
            email: User email
            display_name: Optional display name

        Returns:
            Created UserProfile

        Raises:
            UserAlreadyExistsException: If user exists
            InvalidUserDataException: If data is invalid
        """
        if not email:
            raise InvalidUserDataException("email", "Email is required")

        if await self._repository.exists(user_id):
            raise UserAlreadyExistsException(user_id)

        profile = UserProfile.create_new(
            user_id=user_id,
            email=email,
            display_name=display_name,
        )

        return await self._repository.create(profile)

    async def update_profile(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> UserProfile:
        """
        Update user's basic profile.

        Args:
            user_id: User ID
            display_name: New display name
            avatar_url: New avatar URL

        Returns:
            Updated UserProfile
        """
        profile = await self.get_user_or_raise(user_id)
        profile.update_profile(display_name=display_name, avatar_url=avatar_url)
        return await self._repository.update(profile)

    async def update_preferences(
        self,
        user_id: str,
        preferences: UserPreferences
    ) -> UserProfile:
        """
        Update user preferences.

        Args:
            user_id: User ID
            preferences: New preferences

        Returns:
            Updated UserProfile
        """
        profile = await self.get_user_or_raise(user_id)
        profile.update_preferences(preferences)
        return await self._repository.update(profile)

    async def upgrade_tier(
        self,
        user_id: str,
        new_tier: UserTier,
        stripe_customer_id: Optional[str] = None
    ) -> UserProfile:
        """
        Upgrade user's subscription tier.

        Called when subscription is created/upgraded via Stripe webhook.

        Args:
            user_id: User ID
            new_tier: New tier
            stripe_customer_id: Stripe customer ID

        Returns:
            Updated UserProfile
        """
        return await self._repository.update_tier(
            user_id=user_id,
            new_tier=new_tier,
            stripe_customer_id=stripe_customer_id,
        )

    async def downgrade_tier(
        self,
        user_id: str,
        new_tier: UserTier = UserTier.FREE
    ) -> UserProfile:
        """
        Downgrade user's subscription tier.

        Called when subscription is cancelled via Stripe webhook.

        Args:
            user_id: User ID
            new_tier: Tier to downgrade to

        Returns:
            Updated UserProfile
        """
        return await self._repository.update_tier(
            user_id=user_id,
            new_tier=new_tier,
        )

    async def advance_onboarding(
        self,
        user_id: str,
        step: OnboardingStep
    ) -> UserProfile:
        """
        Advance user's onboarding progress.

        Args:
            user_id: User ID
            step: Step to advance to

        Returns:
            Updated UserProfile
        """
        return await self._repository.update_onboarding_step(user_id, step)

    async def complete_onboarding(self, user_id: str) -> UserProfile:
        """
        Mark user's onboarding as complete.

        Args:
            user_id: User ID

        Returns:
            Updated UserProfile
        """
        return await self._repository.update_onboarding_step(
            user_id,
            OnboardingStep.COMPLETED
        )

    async def check_feature_access(
        self,
        user_id: str,
        feature: str
    ) -> bool:
        """
        Check if user has access to a feature.

        Args:
            user_id: User ID
            feature: Feature name

        Returns:
            True if user has access
        """
        profile = await self._repository.get_by_id(user_id)
        if not profile:
            return False
        return profile.has_feature(feature)

    async def delete_user(self, user_id: str) -> bool:
        """
        Delete user profile.

        Called when user deletes account.

        Args:
            user_id: User ID

        Returns:
            True if deleted
        """
        return await self._repository.delete(user_id)

    async def get_users_by_tier(
        self,
        tier: UserTier,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserProfile]:
        """
        Get users by subscription tier.

        Args:
            tier: Tier to filter
            limit: Max results
            offset: Results to skip

        Returns:
            List of UserProfiles
        """
        return await self._repository.get_by_tier(tier, limit, offset)

"""
Identity Commands - User operations that change state.

@module application.commands.identity
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any

from domains.identity import (
    IdentityService,
    UserProfile,
    UserTier,
    UserPreferences,
)


@dataclass
class CreateUserCommand:
    """
    Command to create a new user.

    Triggered by Clerk webhook on user signup.
    """
    user_id: str
    email: str
    display_name: Optional[str] = None


@dataclass
class CreateUserResult:
    """Result of user creation."""
    success: bool
    user: Optional[UserProfile] = None
    error: Optional[str] = None


class CreateUserHandler:
    """Handler for CreateUserCommand."""

    def __init__(self, identity_service: IdentityService):
        self._identity_service = identity_service

    async def handle(self, command: CreateUserCommand) -> CreateUserResult:
        """Execute user creation."""
        try:
            user = await self._identity_service.create_user(
                user_id=command.user_id,
                email=command.email,
                display_name=command.display_name,
            )

            return CreateUserResult(
                success=True,
                user=user,
            )

        except Exception as e:
            return CreateUserResult(
                success=False,
                error=str(e),
            )


@dataclass
class UpdateUserProfileCommand:
    """
    Command to update user profile.
    """
    user_id: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


@dataclass
class UpdateUserProfileResult:
    """Result of profile update."""
    success: bool
    user: Optional[UserProfile] = None
    error: Optional[str] = None


class UpdateUserProfileHandler:
    """Handler for UpdateUserProfileCommand."""

    def __init__(self, identity_service: IdentityService):
        self._identity_service = identity_service

    async def handle(self, command: UpdateUserProfileCommand) -> UpdateUserProfileResult:
        """Execute profile update."""
        try:
            # Update basic profile
            if command.display_name is not None or command.avatar_url is not None:
                user = await self._identity_service.update_profile(
                    user_id=command.user_id,
                    display_name=command.display_name,
                    avatar_url=command.avatar_url,
                )
            else:
                user = await self._identity_service.get_user_or_raise(command.user_id)

            # Update preferences if provided
            if command.preferences:
                prefs = UserPreferences.from_dict(command.preferences)
                user = await self._identity_service.update_preferences(
                    user_id=command.user_id,
                    preferences=prefs,
                )

            return UpdateUserProfileResult(
                success=True,
                user=user,
            )

        except Exception as e:
            return UpdateUserProfileResult(
                success=False,
                error=str(e),
            )


@dataclass
class UpdateUserTierCommand:
    """
    Command to update user subscription tier.

    Triggered by Stripe webhook on subscription change.
    """
    user_id: str
    new_tier: str  # "free", "starter", "pro"
    stripe_customer_id: Optional[str] = None
    is_upgrade: bool = True


@dataclass
class UpdateUserTierResult:
    """Result of tier update."""
    success: bool
    user: Optional[UserProfile] = None
    previous_tier: Optional[str] = None
    error: Optional[str] = None


class UpdateUserTierHandler:
    """Handler for UpdateUserTierCommand."""

    def __init__(self, identity_service: IdentityService):
        self._identity_service = identity_service

    async def handle(self, command: UpdateUserTierCommand) -> UpdateUserTierResult:
        """Execute tier update."""
        try:
            # Get current user to record previous tier
            current_user = await self._identity_service.get_user(command.user_id)
            previous_tier = current_user.tier.value if current_user else None

            # Parse new tier
            new_tier = UserTier(command.new_tier)

            # Update tier
            if command.is_upgrade:
                user = await self._identity_service.upgrade_tier(
                    user_id=command.user_id,
                    new_tier=new_tier,
                    stripe_customer_id=command.stripe_customer_id,
                )
            else:
                user = await self._identity_service.downgrade_tier(
                    user_id=command.user_id,
                    new_tier=new_tier,
                )

            return UpdateUserTierResult(
                success=True,
                user=user,
                previous_tier=previous_tier,
            )

        except Exception as e:
            return UpdateUserTierResult(
                success=False,
                error=str(e),
            )

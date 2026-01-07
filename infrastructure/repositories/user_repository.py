"""
User Repository Implementation - Supabase data access for identity domain.

@module infrastructure.repositories.user_repository
@version 1.0.0

Implements IUserRepository using Supabase PostgreSQL.
"""

from typing import Optional, List
from datetime import datetime
import logging

from domains.identity.repository import IUserRepository
from domains.identity.aggregates.user_profile import UserProfile
from domains.identity.value_objects import UserTier, OnboardingStep, UserPreferences
from domains.identity.exceptions import (
    UserNotFoundException,
    UserAlreadyExistsException,
)
from core.database import get_supabase_client

logger = logging.getLogger(__name__)


class SupabaseUserRepository(IUserRepository):
    """
    Supabase implementation of user repository.
    """

    def __init__(self, client=None):
        """Initialize repository with Supabase client."""
        self._client = client

    @property
    def client(self):
        """Lazy load Supabase client."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    async def get_by_id(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by user ID."""
        try:
            result = self.client.table("profiles").select("*").eq(
                "id", user_id
            ).single().execute()

            if not result.data:
                return None

            return self._map_to_profile(result.data)

        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None

    async def get_by_email(self, email: str) -> Optional[UserProfile]:
        """Get user profile by email."""
        try:
            result = self.client.table("users").select("*").eq(
                "email", email
            ).single().execute()

            if not result.data:
                return None

            return self._map_to_profile(result.data)

        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            return None

    async def save(self, user_profile: UserProfile) -> UserProfile:
        """Persist user profile (upsert)."""
        try:
            data = self._map_to_row(user_profile)
            result = self.client.table("users").upsert(
                data, on_conflict="user_id"
            ).select("*").single().execute()

            return self._map_to_profile(result.data)

        except Exception as e:
            logger.error(f"Failed to save user {user_profile.user_id}: {e}")
            raise

    async def create(self, user_profile: UserProfile) -> UserProfile:
        """Create a new user profile."""
        # Check if exists
        if await self.exists(user_profile.user_id):
            raise UserAlreadyExistsException(user_profile.user_id)

        try:
            data = self._map_to_row(user_profile)
            result = self.client.table("users").insert(data).select("*").single().execute()

            return self._map_to_profile(result.data)

        except Exception as e:
            logger.error(f"Failed to create user {user_profile.user_id}: {e}")
            raise

    async def update(self, user_profile: UserProfile) -> UserProfile:
        """Update existing user profile."""
        try:
            data = self._map_to_row(user_profile)
            data["updated_at"] = datetime.utcnow().isoformat()

            result = self.client.table("users").update(data).eq(
                "user_id", user_profile.user_id
            ).select("*").single().execute()

            if not result.data:
                raise UserNotFoundException(user_profile.user_id)

            return self._map_to_profile(result.data)

        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to update user {user_profile.user_id}: {e}")
            raise

    async def delete(self, user_id: str) -> bool:
        """Delete a user profile."""
        try:
            result = self.client.table("users").delete().eq(
                "user_id", user_id
            ).execute()

            return len(result.data) > 0 if result.data else False

        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False

    async def exists(self, user_id: str) -> bool:
        """Check if user exists."""
        try:
            result = self.client.table("users").select("user_id").eq(
                "user_id", user_id
            ).single().execute()

            return result.data is not None

        except Exception:
            return False

    async def get_by_tier(
        self,
        tier: UserTier,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserProfile]:
        """Get users by subscription tier."""
        try:
            result = self.client.table("users").select("*").eq(
                "tier", tier.value
            ).range(offset, offset + limit - 1).execute()

            return [self._map_to_profile(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get users by tier {tier}: {e}")
            return []

    async def get_users_needing_onboarding(
        self,
        limit: int = 100
    ) -> List[UserProfile]:
        """Get users who haven't completed onboarding."""
        try:
            result = self.client.table("users").select("*").neq(
                "onboarding_step", OnboardingStep.COMPLETED.value
            ).limit(limit).execute()

            return [self._map_to_profile(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get users needing onboarding: {e}")
            return []

    async def update_tier(
        self,
        user_id: str,
        new_tier: UserTier,
        stripe_customer_id: Optional[str] = None
    ) -> UserProfile:
        """Update user's subscription tier."""
        try:
            update_data = {
                "tier": new_tier.value,
                "updated_at": datetime.utcnow().isoformat(),
            }
            if stripe_customer_id:
                update_data["stripe_customer_id"] = stripe_customer_id

            result = self.client.table("users").update(update_data).eq(
                "user_id", user_id
            ).select("*").single().execute()

            if not result.data:
                raise UserNotFoundException(user_id)

            return self._map_to_profile(result.data)

        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to update tier for user {user_id}: {e}")
            raise

    async def update_onboarding_step(
        self,
        user_id: str,
        step: OnboardingStep
    ) -> UserProfile:
        """Update user's onboarding progress."""
        try:
            result = self.client.table("users").update({
                "onboarding_step": step.value,
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("user_id", user_id).select("*").single().execute()

            if not result.data:
                raise UserNotFoundException(user_id)

            return self._map_to_profile(result.data)

        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to update onboarding for user {user_id}: {e}")
            raise

    def _map_to_profile(self, row: dict) -> UserProfile:
        """Map database row to UserProfile."""
        preferences = UserPreferences.from_dict(row.get("preferences", {})) \
            if row.get("preferences") else UserPreferences()

        return UserProfile(
            user_id=row["user_id"],
            email=row["email"],
            tier=UserTier(row.get("tier", "free")),
            onboarding_step=OnboardingStep(row.get("onboarding_step", "not_started")),
            preferences=preferences,
            display_name=row.get("display_name"),
            avatar_url=row.get("avatar_url"),
            stripe_customer_id=row.get("stripe_customer_id"),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                if row.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
                if row.get("updated_at") else datetime.utcnow(),
        )

    def _map_to_row(self, profile: UserProfile) -> dict:
        """Map UserProfile to database row."""
        return {
            "user_id": profile.user_id,
            "email": profile.email,
            "tier": profile.tier.value,
            "onboarding_step": profile.onboarding_step.value,
            "preferences": profile.preferences.to_dict(),
            "display_name": profile.display_name,
            "avatar_url": profile.avatar_url,
            "stripe_customer_id": profile.stripe_customer_id,
        }

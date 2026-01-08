"""
User Repository Implementation - Supabase data access for identity domain.

@module infrastructure.repositories.user_repository
@version 1.0.0

Implements IUserRepository using Supabase PostgreSQL.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging

from domains.identity.repository import IUserRepository
from domains.identity.aggregates.user_profile import UserProfile
from domains.identity.value_objects import UserTier, OnboardingStep, UserPreferences
from domains.identity.exceptions import (
    UserNotFoundException,
    UserAlreadyExistsException,
)
from core.database import get_supabase_client, retry_on_network_error

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

    # Extended Methods

    @retry_on_network_error()
    async def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile by ID.

        Args:
            user_id: User ID

        Returns:
            Profile dict or None
        """
        if not user_id:
            return None

        result = self.client.table("profiles").select("*").eq("id", user_id).execute()
        return result.data[0] if result.data else None

    def generate_user_code(self) -> str:
        """
        Generate unique 6-char user code.

        Returns:
            Unique user code
        """
        import random
        import string
        chars = string.ascii_uppercase + string.digits
        for _ in range(10):
            code = ''.join(random.choices(chars, k=6))
            existing = self.client.table("profiles").select("id").eq("user_code", code).execute()
            if not existing.data:
                return code
        return ''.join(random.choices(chars, k=8))

    @retry_on_network_error()
    async def create_profile(
        self,
        user_id: str,
        email: str,
        username: str,
        avatar_url: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        timezone_str: str = "UTC"
    ) -> Optional[Dict[str, Any]]:
        """
        Create new user profile with signup bonus.

        Args:
            user_id: User ID
            email: Email address
            username: Username
            avatar_url: Avatar URL
            first_name: First name
            last_name: Last name
            timezone_str: User timezone

        Returns:
            Created profile dict
        """
        user_code = self.generate_user_code()

        data = {
            "id": user_id,
            "email": email,
            "username": username,
            "avatar_url": avatar_url,
            "first_name": first_name,
            "last_name": last_name,
            "tier": "free",
            "credits_monthly": 0,
            "credits_permanent": 50,  # Signup bonus
            "user_code": user_code,
            "timezone": timezone_str,
        }

        result = self.client.table("profiles").insert(data).execute()

        # Note: Credit transaction logging should be done by caller
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def update_subscription_tier(
        self,
        user_id: str,
        tier: str,
        stripe_customer_id: Optional[str] = None,
        subscription_status: str = "active"
    ) -> Optional[Dict[str, Any]]:
        """
        Update user subscription tier.

        Args:
            user_id: User ID
            tier: Tier (free, starter, pro)
            stripe_customer_id: Stripe customer ID
            subscription_status: Subscription status

        Returns:
            Updated profile dict
        """
        update_data = {"tier": tier, "subscription_status": subscription_status}
        if stripe_customer_id:
            update_data["stripe_customer_id"] = stripe_customer_id

        result = self.client.table("profiles").update(update_data).eq("id", user_id).execute()
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def update_profile(
        self,
        user_id: str,
        avatar_url: Optional[str] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        timezone_val: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update user profile fields.

        Args:
            user_id: User ID
            avatar_url: New avatar URL
            username: New username
            first_name: New first name
            last_name: New last name
            timezone_val: New timezone

        Returns:
            Updated profile dict
        """
        update_data = {}
        if avatar_url is not None:
            update_data["avatar_url"] = avatar_url
        if username is not None:
            update_data["username"] = username
        if first_name is not None:
            update_data["first_name"] = first_name
        if last_name is not None:
            update_data["last_name"] = last_name
        if timezone_val is not None:
            update_data["timezone"] = timezone_val

        if not update_data:
            return None

        result = self.client.table("profiles").update(update_data).eq("id", user_id).execute()
        return result.data[0] if result.data else None

    @retry_on_network_error()
    async def update_timezone(self, user_id: str, tz: str) -> Optional[Dict[str, Any]]:
        """
        Update user timezone.

        Args:
            user_id: User ID
            tz: Timezone string

        Returns:
            Updated profile dict
        """
        result = self.client.table("profiles").update({"timezone": tz}).eq("id", user_id).execute()
        return result.data[0] if result.data else None

    async def get_timezone(self, user_id: str) -> str:
        """
        Get user timezone, default to UTC.

        Args:
            user_id: User ID

        Returns:
            Timezone string (defaults to UTC)
        """
        if not user_id:
            return "UTC"
        try:
            result = self.client.table("profiles").select("timezone").eq("id", user_id).execute()
            if result.data:
                return result.data[0].get("timezone") or "UTC"
        except:
            pass
        return "UTC"

    async def search_users(self, query: str) -> List[Dict[str, Any]]:
        """
        Search users by email, username, or user_code.

        Args:
            query: Search query

        Returns:
            List of matching profiles
        """
        result = self.client.table("profiles").select("id, email, username, user_code, tier").or_(
            f"email.ilike.%{query}%,username.ilike.%{query}%,user_code.ilike.%{query}%"
        ).limit(20).execute()
        return result.data or []

    async def get_users_by_tier(self, tier: str) -> List[str]:
        """
        Get all user IDs for a specific tier.

        Args:
            tier: Tier name

        Returns:
            List of user IDs
        """
        result = self.client.table("profiles").select("id").eq("tier", tier).execute()
        return [u["id"] for u in (result.data or [])]

    async def get_user_discount(
        self,
        user_id: str,
        target_plan: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get active discount for user.

        Args:
            user_id: User ID
            target_plan: Target plan filter

        Returns:
            Active discount or None
        """
        query = self.client.table("user_discounts").select("*").eq(
            "user_id", user_id
        ).eq("is_used", False).gte("expires_at", datetime.now(timezone.utc).isoformat())

        if target_plan:
            query = query.eq("target_plan", target_plan)

        result = query.order("discount_percent", desc=True).limit(1).execute()
        return result.data[0] if result.data else None

    async def create_user_discount(
        self,
        user_id: str,
        discount_percent: int,
        valid_days: int,
        target_plan: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a user discount.

        Args:
            user_id: User ID
            discount_percent: Discount percentage
            valid_days: Valid for N days
            target_plan: Target plan

        Returns:
            Created discount record
        """
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(days=valid_days)

        result = self.client.table("user_discounts").insert({
            "user_id": user_id,
            "discount_percent": discount_percent,
            "expires_at": expires_at.isoformat(),
            "target_plan": target_plan,
        }).execute()

        return result.data[0] if result.data else None

    async def mark_discount_used(self, discount_id: str) -> bool:
        """
        Mark a discount as used.

        Args:
            discount_id: Discount record ID

        Returns:
            True if successfully marked, False otherwise
        """
        result = self.client.table("user_discounts").update({
            "is_used": True,
            "used_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", discount_id).execute()

        return len(result.data) > 0 if result.data else False

"""
User Repository Extended - Additional methods for services/db migration.

@module infrastructure.repositories.user_repository_extended
@version 1.0.0

Extends SupabaseUserRepository with additional methods needed for
backward compatibility with services/db/users.py functions.
"""

import logging
import random
import string
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from core.database import DatabaseClient, retry_on_network_error

logger = logging.getLogger(__name__)


class SupabaseUserRepositoryExtended:
    """
    Extended user repository with additional methods for profiles table.

    This repository works directly with the "profiles" table and provides
    all methods needed to replace services/db/users.py functions.
    """

    def __init__(self, client: DatabaseClient):
        """
        Initialize repository with database client.

        Args:
            client: Supabase database client
        """
        self.client = client

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

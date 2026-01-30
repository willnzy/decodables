"""
User Repository Implementation - Supabase data access for identity domain.

@module infrastructure.repositories.user_repository
@version 2.0.0 (AsyncClient Migration - Phase 5)

Implements IUserRepository using Supabase PostgreSQL.
Inherits from BaseRepository for soft/hard delete support.

v2.0 Changes:
- Removed run_in_threadpool wrappers
- All database calls now use native async/await with AsyncClient
- Updated retry decorators to async version
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
import logging

from domains.identity.repository import IUserRepository
from domains.identity.aggregates.user_profile import UserProfile
from domains.identity.value_objects import UserTier, OnboardingStep, UserPreferences
from domains.identity.exceptions import (
    UserNotFoundException,
    UserAlreadyExistsException,
)
from core.database import retry_on_network_error_async
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class SupabaseUserRepository(BaseRepository[UserProfile], IUserRepository):
    """
    Supabase implementation of user repository.

    Inherits soft/hard delete operations from BaseRepository.
    """

    @property
    def table_name(self) -> str:
        """Table name for user profiles."""
        return "profiles"

    async def get_by_id(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by user ID."""
        try:
            result = await self.client.table("profiles").select("*").eq("id", user_id).single().execute()

            if not result.data:
                return None

            return self._map_to_entity(result.data)

        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None

    async def get_by_email(self, email: str) -> Optional[UserProfile]:
        """Get user profile by email."""
        try:
            result = await self.client.table("profiles").select("*").eq("email", email).single().execute()

            if not result.data:
                return None

            return self._map_to_entity(result.data)

        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            return None

    async def save(self, user_profile: UserProfile) -> UserProfile:
        """Persist user profile (upsert)."""
        try:
            data = self._map_to_row(user_profile)
            result = await self.client.table("profiles").upsert(data, on_conflict="id").execute()

            if not result.data:
                raise Exception("Failed to save user - no data returned")

            return self._map_to_entity(result.data[0])

        except Exception as e:
            logger.error(f"Failed to save user {user_profile.user_id}: {e}")
            raise

    async def create(self, user_profile: UserProfile) -> UserProfile:
        """Create a new user profile."""
        # Check if exists
        if await self.exists(user_profile.user_id):
            raise UserAlreadyExistsException(user_profile.user_id)

        try:
            # Generate user_code if not provided
            if not user_profile.user_code:
                user_profile.user_code = await self.generate_user_code()

            data = self._map_to_row(user_profile)
            result = await self.client.table("profiles").insert(data).execute()

            if not result.data:
                raise Exception("Failed to create user - no data returned")

            return self._map_to_entity(result.data[0])

        except Exception as e:
            logger.error(f"Failed to create user {user_profile.user_id}: {e}")
            raise

    async def create_or_get(
        self,
        user_profile: UserProfile,
        source: str,
        signup_bonus: int = 0,
    ) -> Tuple[UserProfile, bool]:
        """
        Create user or get existing (idempotent operation).

        Uses database-level atomic operation (RPC) to ensure thread-safety
        and avoid race conditions between Webhook and JIT creation.

        Business Pattern: Stripe Idempotency Pattern
        Reference: https://stripe.com/docs/api/idempotent_requests

        Args:
            user_profile: The UserProfile to create
            source: Creation source ('webhook' or 'jit')
            signup_bonus: Signup bonus credits — 调用方应从 TierService 获取后传入

        Returns:
            Tuple of (UserProfile, was_created)
            - was_created=True: User was newly created by this call
            - was_created=False: User already existed

        Implementation:
        - Calls PostgreSQL RPC function create_user_idempotent()
        - RPC uses SELECT FOR UPDATE to prevent race conditions
        - First call wins, subsequent calls return existing user
        - All attempts are logged to user_creation_logs table
        """
        try:
            # Call idempotent RPC function
            result = await self.client.rpc('create_user_idempotent', {
                'p_user_id': user_profile.user_id,
                'p_email': user_profile.email,
                'p_source': source,
                'p_username': user_profile.username,
                'p_first_name': user_profile.first_name,
                'p_last_name': user_profile.last_name,
                'p_avatar_url': user_profile.avatar_url,
                'p_display_name': user_profile.display_name,
                'p_signup_bonus': signup_bonus,
            }).execute()
            
            if not result.data:
                raise Exception("RPC create_user_idempotent returned no data")
            
            # Parse result
            row = result.data[0]
            profile = self._map_to_entity(row['user_profile'])
            was_created = row['was_created']
            created_by = row['created_by']
            
            # Log result
            if was_created:
                logger.info(
                    f"✅ User {user_profile.user_id} created via {source}",
                    extra={
                        "user_id": user_profile.user_id,
                        "source": source,
                        "action": "created",
                        "email": user_profile.email
                    }
                )
                
                # ✅ Sentry: 捕获成功创建事件（INFO 级别）
                try:
                    from infrastructure.monitoring.sentry_helpers import SentryMonitoring, SentryLevel
                    SentryMonitoring.capture_user_creation_event(
                        event_type="created",
                        user_id=user_profile.user_id,
                        source=source,
                        level=SentryLevel.INFO,
                        extra_context={"email": user_profile.email}
                    )
                except Exception:
                    pass
            else:
                logger.info(
                    f"ℹ️ User {user_profile.user_id} already exists "
                    f"(created by {created_by}, attempted via {source})",
                    extra={
                        "user_id": user_profile.user_id,
                        "source": source,
                        "created_by": created_by,
                        "action": "duplicate_attempt"
                    }
                )
                
                # ✅ Sentry: 捕获重复创建尝试（INFO 级别）
                try:
                    from infrastructure.monitoring.sentry_helpers import capture_duplicate_creation
                    capture_duplicate_creation(user_profile.user_id, source, created_by)
                except Exception:
                    pass
            
            return profile, was_created
            
        except Exception as rpc_error:
            logger.error(
                f"❌ RPC create_user_idempotent failed for {user_profile.user_id}: {rpc_error}",
                extra={
                    "user_id": user_profile.user_id,
                    "source": source,
                    "error": str(rpc_error),
                    "fallback": "attempting_graceful_degradation"
                },
                exc_info=True
            )
            
            # ✅ Graceful Degradation: Fallback to application-level logic
            try:
                logger.info(
                    f"🔄 Attempting fallback for user {user_profile.user_id}...",
                    extra={"user_id": user_profile.user_id, "source": source}
                )
                
                # 1. Try to get existing user
                existing = await self.get_by_id(user_profile.user_id)
                if existing:
                    logger.info(
                        f"✅ Fallback: User {user_profile.user_id} found (already exists)",
                        extra={
                            "user_id": user_profile.user_id,
                            "fallback": "get_by_id_success"
                        }
                    )
                    return existing, False  # User already exists
                
                # 2. Try to create user
                try:
                    # Generate user_code if not provided
                    if not user_profile.user_code:
                        user_profile.user_code = await self.generate_user_code()
                    
                    created = await self.create(user_profile)
                    logger.info(
                        f"✅ Fallback: User {user_profile.user_id} created successfully",
                        extra={
                            "user_id": user_profile.user_id,
                            "fallback": "create_success"
                        }
                    )
                    return created, True  # User newly created
                    
                except UserAlreadyExistsException:
                    # Race condition: user was created between get_by_id and create
                    logger.info(
                        f"ℹ️ Fallback: User {user_profile.user_id} created by another process",
                        extra={
                            "user_id": user_profile.user_id,
                            "fallback": "race_condition_handled"
                        }
                    )
                    existing = await self.get_by_id(user_profile.user_id)
                    if existing:
                        return existing, False
                    else:
                        raise Exception("User exists but could not be retrieved")
                
            except Exception as fallback_error:
                logger.error(
                    f"❌ Fallback also failed for {user_profile.user_id}: {fallback_error}",
                    extra={
                        "user_id": user_profile.user_id,
                        "source": source,
                        "rpc_error": str(rpc_error),
                        "fallback_error": str(fallback_error)
                    },
                    exc_info=True
                )
                
                # ✅ Sentry: 捕获关键错误（使用统一的辅助函数）
                try:
                    from infrastructure.monitoring.sentry_helpers import capture_creation_error
                    capture_creation_error(
                        user_id=user_profile.user_id,
                        source=source,
                        error=rpc_error,
                        fallback_attempted=True,
                        fallback_success=False
                    )
                except Exception:
                    pass  # Don't let Sentry errors break the flow
                
                # Re-raise original RPC error
                raise rpc_error

    async def update(self, user_profile: UserProfile) -> UserProfile:
        """Update existing user profile."""
        try:
            data = self._map_to_row(user_profile)
            data["updated_at"] = datetime.utcnow().isoformat()

            result = await self.client.table("profiles").update(data).eq("user_id", user_profile.user_id).execute()

            if not result.data:
                raise UserNotFoundException(user_profile.user_id)

            return self._map_to_entity(result.data[0])

        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to update user {user_profile.user_id}: {e}")
            raise

    async def delete(self, user_id: str) -> bool:
        """
        Delete a user profile (soft delete).

        Uses BaseRepository.soft_delete() for soft deletion.
        For hard delete, use hard_delete() method.
        """
        return await self.soft_delete(user_id)

    # Note: exists() method inherited from BaseRepository

    async def get_by_tier(
        self,
        tier: UserTier,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserProfile]:
        """Get users by subscription tier."""
        try:
            result = await self.client.table("profiles").select("*").eq("tier", tier.value).range(offset, offset + limit - 1).execute()

            return [self._map_to_entity(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get users by tier {tier}: {e}")
            return []

    async def get_users_needing_onboarding(
        self,
        limit: int = 100
    ) -> List[UserProfile]:
        """Get users who haven't completed onboarding."""
        try:
            result = await self.client.table("profiles").select("*").neq("onboarding_step", OnboardingStep.COMPLETED.value).limit(limit).execute()

            return [self._map_to_entity(row) for row in result.data]

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

            result = await self.client.table("profiles").update(update_data).eq("user_id", user_id).execute()

            if not result.data:
                raise UserNotFoundException(user_id)

            return self._map_to_entity(result.data[0])

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
            # Update onboarding step
            await self.client.table("profiles").update({
                "onboarding_step": step.value,
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", user_id).execute()

            # Fetch updated data
            result = await self.client.table("profiles").select("*").eq(
                "id", user_id
            ).single().execute()

            if not result.data:
                raise UserNotFoundException(user_id)

            return self._map_to_entity(result.data)

        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to update onboarding for user {user_id}: {e}")
            raise

    def _map_to_entity(self, row: dict) -> UserProfile:
        """Map database row to UserProfile."""
        from domains.identity.value_objects import UserRole
        
        preferences = UserPreferences.from_dict(row.get("preferences", {})) \
            if row.get("preferences") else UserPreferences()

        # Parse role with fallback to 'user'
        role_value = row.get("role", "user")
        try:
            role = UserRole(role_value)
        except ValueError:
            role = UserRole.USER

        return UserProfile(
            user_id=row["id"],  # profiles.id is the Clerk user_id
            email=row["email"],
            user_code=row.get("user_code"),
            username=row.get("username"),
            first_name=row.get("first_name"),
            last_name=row.get("last_name"),
            display_name=row.get("display_name"),
            avatar_url=row.get("avatar_url"),
            role=role,  # User role (user/admin)
            tier=UserTier(row.get("tier", "t1")),
            subscription_status=row.get("subscription_status"),
            onboarding_step=OnboardingStep(row.get("onboarding_step", "not_started")),
            preferences=preferences,
            stripe_customer_id=row.get("stripe_customer_id"),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                if row.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
                if row.get("updated_at") else datetime.utcnow(),
        )

    def _map_to_row(self, profile: UserProfile) -> dict:
        """Map UserProfile to database row."""
        return {
            "id": profile.user_id,  # profiles.id is the primary key
            "email": profile.email,
            "user_code": profile.user_code,
            "username": profile.username,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "display_name": profile.display_name,
            "avatar_url": profile.avatar_url,
            "role": profile.role.value if hasattr(profile.role, 'value') else profile.role,  # user/admin
            "tier": profile.tier.value,
            "subscription_status": profile.subscription_status,
            "onboarding_step": profile.onboarding_step.value,
            "preferences": profile.preferences.to_dict(),
            "stripe_customer_id": profile.stripe_customer_id,
        }

    # Extended Methods

    @retry_on_network_error_async()
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

        result = await self.client.table("profiles").select("*").eq("id", user_id).execute()
        return result.data[0] if result.data else None

    async def generate_user_code(self) -> str:
        """
        Generate unique 26-digit user code with registration timestamp and user count.

        Format: YYMMDDHHMMSS + mmmm + UUUUUUU + RRR
        Example: 26010914305278900123456789
        - 260109: Registration date (2026-01-09) [6 digits]
        - 143052: Registration time (14:30:52) [6 digits]
        - 7890: Milliseconds (0.1ms precision) [4 digits]
        - 0123456: Total user count [7 digits, zero-padded]
        - 789: Random digits for uniqueness [3 digits]

        The user_code allows admins to quickly identify:
        1. When the user registered (date + time with 0.1ms precision)
        2. Business growth metrics (user count at registration time)
        3. Makes user management and analytics easier

        Returns:
            Unique user code (26 digits: 6 + 6 + 4 + 7 + 3)

        See: docs/shared/USER-ID-SYSTEM.md for full documentation
        """
        from datetime import datetime, timezone
        import random

        now = datetime.now(timezone.utc)

        # Date part (YYMMDD - 6 digits)
        date_part = now.strftime("%y%m%d")

        # Time part (HHMMSS - 6 digits)
        time_part = now.strftime("%H%M%S")

        # Milliseconds (4 digits, 0.1ms precision: 0000-9999)
        ms_part = f"{now.microsecond // 100:04d}"

        # Get total user count (7 digits, zero-padded)
        result = await self.client.table("profiles").select("id", count="exact").execute()
        user_count = (result.count or 0) if hasattr(result, 'count') else 0
        count_part = f"{user_count + 1:07d}"  # +1 for the user being created

        # Random 3 digits (000-999) for additional uniqueness
        random_part = f"{random.randint(0, 999):03d}"

        # Combine: 6 + 6 + 4 + 7 + 3 = 26 digits (NO separators)
        code = f"{date_part}{time_part}{ms_part}{count_part}{random_part}"

        # Verify uniqueness (extremely rare collision, but check anyway)
        existing = await self.client.table("profiles").select("id").eq("user_code", code).execute()
        if existing.data:
            # Recursive retry with new random suffix (collision is near-impossible)
            return await self.generate_user_code()

        return code

    @retry_on_network_error_async()
    async def create_profile(
        self,
        user_id: str,
        email: str,
        username: str,
        avatar_url: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        timezone_str: str = "UTC",
        signup_bonus: int = 0,
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
            signup_bonus: Signup bonus credits — 必须由调用方从 TierService 获取后传入，不硬编码

        Returns:
            Created profile dict
        """
        user_code = await self.generate_user_code()

        data = {
            "id": user_id,
            "email": email,
            "username": username,
            "avatar_url": avatar_url,
            "first_name": first_name,
            "last_name": last_name,
            "tier": "t1",
            "credits_monthly": 0,
            "credits_permanent": signup_bonus,
            "user_code": user_code,
            "timezone": timezone_str,
        }

        result = await self.client.table("profiles").insert(data).execute()

        # Note: Credit transaction logging should be done by caller
        return result.data[0] if result.data else None

    @retry_on_network_error_async()
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

        Fix P0-011: Reset credits_monthly to 0 when downgrading to free tier
        """
        update_data = {"tier": tier, "subscription_status": subscription_status}
        if stripe_customer_id:
            update_data["stripe_customer_id"] = stripe_customer_id

        # P0-011 fix: Reset monthly credits when downgrading to free tier
        # WS4: Also clear cancel/downgrade schedule flags
        if tier == "t1":
            update_data["credits_monthly"] = 0
            update_data["cancel_at_period_end"] = False
            update_data["cancel_at"] = None
            update_data["pending_tier_change"] = None

        result = await self.client.table("profiles").update(update_data).eq("id", user_id).execute()
        return result.data[0] if result.data else None

    @retry_on_network_error_async()
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

        result = await self.client.table("profiles").update(update_data).eq("id", user_id).execute()
        return result.data[0] if result.data else None

    @retry_on_network_error_async()
    async def update_timezone(self, user_id: str, tz: str) -> Optional[Dict[str, Any]]:
        """
        Update user timezone.

        Args:
            user_id: User ID
            tz: Timezone string

        Returns:
            Updated profile dict
        """
        result = await self.client.table("profiles").update({"timezone": tz}).eq("id", user_id).execute()
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
            result = await self.client.table("profiles").select("timezone").eq("id", user_id).execute()
            if result.data:
                return result.data[0].get("timezone") or "UTC"
        except:
            pass
        return "UTC"

    @retry_on_network_error_async()  # v3.26 (REPO-HIGH-1): Added retry decorator
    async def search_users(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search users by email, username, or user_code.

        Args:
            query: Search query
            limit: Maximum number of results (default: 20)

        Returns:
            List of matching profiles

        v3.26 (REPO-HIGH-1): Added @retry_on_network_error decorator
        v3.26 (USER-MEDIUM-1): Added configurable limit parameter
        """
        result = await self.client.table("profiles").select("id, email, username, user_code, tier").or_(
            f"email.ilike.%{query}%,username.ilike.%{query}%,user_code.ilike.%{query}%"
        ).limit(limit).execute()
        return result.data or []

    @retry_on_network_error_async()  # v3.26 (REPO-HIGH-3): Added retry decorator + pagination
    async def get_users_by_tier(self, tier: str, offset: int = 0, limit: int = 100) -> List[str]:
        """
        Get user IDs for a specific tier with pagination.

        Args:
            tier: Tier name
            offset: Number of records to skip (default: 0)
            limit: Maximum number of records (default: 100)

        Returns:
            List of user IDs

        v3.26 (REPO-HIGH-3): Added pagination support (offset/limit) to prevent OOM
        v3.26 (REPO-HIGH-1): Added @retry_on_network_error decorator
        """
        result = await self.client.table("profiles").select("id").eq("tier", tier).range(offset, offset + limit - 1).execute()
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
        q = self.client.table("user_discounts").select("*").eq(
            "user_id", user_id
        ).eq("is_used", False).gte("expires_at", datetime.now(timezone.utc).isoformat())

        if target_plan:
            q = q.eq("target_plan", target_plan)

        result = await q.order("discount_percent", desc=True).limit(1).execute()
        return result.data[0] if result.data else None

    @retry_on_network_error_async()  # v3.26 (REPO-HIGH-2): Added retry decorator
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

        v3.26 (REPO-HIGH-2): Added @retry_on_network_error decorator
        """
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(days=valid_days)

        result = await self.client.table("user_discounts").insert({
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
        result = await self.client.table("user_discounts").update({
            "is_used": True,
            "used_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", discount_id).execute()

        return len(result.data) > 0 if result.data else False

    @retry_on_network_error_async()
    async def update_monthly_credits(self, user_id: str, credits: int) -> None:
        """
        Update user's monthly credits.

        Args:
            user_id: User ID
            credits: Monthly credits amount

        Raises:
            Exception if update fails
        """
        await self.client.table("profiles").update({
            "credits_monthly": credits
        }).eq("id", user_id).execute()

    async def get_by_stripe_customer_id(self, stripe_customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Look up a user profile by Stripe customer ID.

        Used by checkout flow to bind existing Stripe customer to new sessions.

        Args:
            stripe_customer_id: Stripe customer ID (e.g. 'cus_xxx')

        Returns:
            Profile dict or None if not found
        """
        try:
            result = await self.client.table("profiles").select("*").eq(
                "stripe_customer_id", stripe_customer_id
            ).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"[UserRepo] Failed to get user by stripe_customer_id {stripe_customer_id}: {e}")
            return None

    async def update_subscription_status(self, user_id: str, status: str) -> bool:
        """
        Update only the subscription_status field (without changing tier).

        Used for invoice.payment_failed → 'past_due', etc.

        Args:
            user_id: User ID
            status: New subscription status ('active', 'past_due', 'canceled', 'inactive')

        Returns:
            True if update succeeded
        """
        try:
            await self.client.table("profiles").update({
                "subscription_status": status
            }).eq("id", user_id).execute()
            return True
        except Exception as e:
            logger.error(f"[UserRepo] Failed to update subscription_status for {user_id}: {e}")
            return False

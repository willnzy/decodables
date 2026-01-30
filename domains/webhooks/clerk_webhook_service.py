"""
Clerk Webhook Service

Handles Clerk authentication webhook events.

@version 2.0.0 (AsyncClient Migration - Phase 10)

Architecture: API → ClerkWebhookService → Repositories

v2.0.0 Changes:
- Migrated to AsyncClient for all database operations
- Removed get_supabase_client() usage
- All direct DB calls now use self.db_client (AsyncClient)
"""

import logging
from typing import Dict, Any
from svix.webhooks import Webhook, WebhookVerificationError

from config import CLERK_WEBHOOK_SECRET
from infrastructure.repositories import (
    SupabaseUserRepository,
    SupabaseCreditRepository,
)

logger = logging.getLogger(__name__)


class ClerkWebhookService:
    """
    Clerk Webhook Service - Handles Clerk authentication events.

    This service processes Clerk webhook events for user management,
    including user creation, profile updates, and session tracking.

    Architecture: API → ClerkWebhookService → Repositories

    v2.0.0: Migrated to AsyncClient
    v1.0.0: Created for DDD compliance
    """

    def __init__(
        self,
        user_repo: SupabaseUserRepository,
        credit_repo: SupabaseCreditRepository,
        db_client = None,  # AsyncClient for direct database operations
        tier_service = None,  # WS2: TierService for dynamic signup bonus configuration
        activity_log_repo = None,  # WS2: ActivityLogRepository for unified activity logging
    ):
        """
        Initialize Clerk Webhook Service.

        Args:
            user_repo: User repository for profile operations
            credit_repo: Credit repository for signup bonus
            db_client: AsyncClient for direct database operations (activity logs, RPC calls)
            tier_service: TierService for dynamic tier/credits configuration
            activity_log_repo: ActivityLogRepository for activity logging
        """
        self.user_repo = user_repo
        self.credit_repo = credit_repo
        self.db_client = db_client or user_repo.client  # Use repo's client if not provided
        self.tier_service = tier_service
        self.activity_log_repo = activity_log_repo

    def verify_signature(self, payload: bytes, headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Verify Clerk webhook signature using Svix.

        Args:
            payload: Raw request body
            headers: Request headers

        Returns:
            Verified event dictionary

        Raises:
            ValueError: If CLERK_WEBHOOK_SECRET is not configured
            WebhookVerificationError: If signature verification fails
        """
        if not CLERK_WEBHOOK_SECRET:
            raise ValueError("Missing CLERK_WEBHOOK_SECRET")

        wh = Webhook(CLERK_WEBHOOK_SECRET)
        return wh.verify(payload, headers)

    async def handle_event(self, event: Dict[str, Any]) -> Dict[str, str]:
        """
        Route and handle Clerk webhook event.

        Args:
            event: Verified Clerk webhook event

        Returns:
            Dict with status and optional reason
        """
        event_type = event.get("type")
        data = event.get("data", {})

        if event_type == "user.created":
            return await self._handle_user_created(data)
        elif event_type == "user.updated":
            return await self._handle_user_updated(data)
        elif event_type == "session.created":
            return await self._handle_session_created(event, data)
        elif event_type in ["session.ended", "session.removed", "session.revoked"]:
            return await self._handle_session_ended(event_type, data)

        return {"status": "processed"}

    async def _handle_user_created(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Handle user.created event (Primary Path for User Creation).

        Architecture: Webhook-First Pattern
        - This is the preferred way to create users (95% of cases)
        - Uses idempotent create_or_get() to handle JIT race conditions
        - ✅ Signup bonus (50 credits) is granted by the RPC function
        - ❌ DO NOT call _grant_signup_bonus() here (would duplicate credits)

        Args:
            data: User data from Clerk

        Returns:
            Dict with status ('processed', 'duplicate') and was_created flag
        """
        user_id = data["id"]
        email = data["email_addresses"][0]["email_address"]
        username = data.get("username")
        image_url = data.get("image_url")
        first_name = data.get("first_name")
        last_name = data.get("last_name")

        # Create UserProfile using DDD aggregate (complete data from Clerk)
        from domains.identity.aggregates import UserProfile
        
        user_profile = UserProfile.create_new(
            user_id=user_id,
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            avatar_url=image_url,
            display_name=username or first_name or email.split("@")[0]
        )
        
        # Idempotent create: safe even if JIT already created the user
        # Returns (profile, was_created) - was_created=False if JIT beat us
        profile, was_created = await self.user_repo.create_or_get(
            user_profile,
            source='webhook'
        )
        
        if was_created:
            # Webhook successfully created user (normal case)
            logger.info(
                f"✅ Webhook created user {user_id}. "
                f"Signup bonus (50 credits) was granted by RPC."
            )
            
            # ✅ HOTFIX: 注册奖励已在 create_user_idempotent() RPC 中发放
            # 无需再次调用 _grant_signup_bonus()（会导致重复发放 100 credits）
            
            status_result = {"status": "processed", "was_created": True}
        else:
            # User already existed (JIT created first in race condition)
            # This is fine - the race condition was handled gracefully
            logger.info(
                f"ℹ️ User {user_id} already exists (likely JIT created first). "
                f"Signup bonus was already granted by JIT path."
            )
            
            status_result = {"status": "duplicate", "was_created": False, "reason": "jit_created"}
        
        # Note: Signup bonus is granted in create_user_idempotent() RPC
        # by setting credits_permanent=50, so no need to grant again

        # v3.33: Create default workspace and apply preset tags for new users
        if was_created:
            try:
                await self._create_workspace_and_preset_tags(user_id)
            except Exception as e:
                logger.warning(f"Failed to create workspace/preset tags for user {user_id}: {e}")
                # Don't fail the webhook - user is created, workspace can be created on-demand

        # Log signup event
        if self.activity_log_repo:
            await self.activity_log_repo.log_activity(
                user_id=user_id,
                action="user_signup",
                metadata={
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "method": "clerk"
                },
            )

        # ✅ Phase 4 - Task 9: Log webhook operation to audit trail
        try:
            from infrastructure.logging.activity_logger import log_webhook_operation
            await log_webhook_operation(
                operation_type="webhook_user_create",
                source="clerk",
                target_user_id=user_id,
                details=f"User created via Clerk: {email}",
                metadata={
                    "email": email,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to log webhook operation: {e}")

        return {"status": "processed"}

    # WS2: _grant_signup_bonus() REMOVED — dead code (line 113: "DO NOT call", line 156: "无需再次调用")
    # Signup bonus is granted by create_user_idempotent RPC (p_signup_bonus parameter)

    async def _create_workspace_and_preset_tags(self, user_id: str) -> None:
        """
        Create default workspace and apply preset tags for a new user.

        v3.33: Phase 1 - Workspace + Tag System

        This method:
        1. Creates a default personal workspace for the user
        2. Applies default preset tag groups to the workspace

        Args:
            user_id: Clerk user_id of the new user
        """
        from container import get_container

        try:
            container = get_container()

            # 1. Create default workspace
            workspace_service = await container.get_workspace_service()
            workspace = await workspace_service.get_or_create_default(user_id)
            logger.info(f"✅ Created default workspace {workspace.id} for user {user_id}")

            # 2. Apply preset tags (if enabled in config)
            config_service = await container.get_config_service()
            enable_presets = await config_service.get_bool("tag.enable_preset_groups", True)

            if enable_presets:
                tag_service = await container.get_tag_service()
                tags = await tag_service.apply_default_presets(workspace.id, user_id)
                logger.info(
                    f"✅ Applied {len(tags)} preset tags to workspace {workspace.id} for user {user_id}"
                )

        except Exception as e:
            logger.error(f"Failed to create workspace/preset tags for user {user_id}: {e}")
            raise

    async def _handle_user_updated(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Handle user.updated event.

        Syncs profile updates from Clerk to Supabase.
        Also detects tier changes in public_metadata.

        Args:
            data: Updated user data from Clerk

        Returns:
            Dict with status 'processed'
        """
        user_id = data.get("id")
        new_avatar = data.get("image_url")
        new_username = data.get("username")
        new_first_name = data.get("first_name")
        new_last_name = data.get("last_name")

        # Sync updates to Supabase (including name fields)
        await self.user_repo.update_profile(
            user_id,
            avatar_url=new_avatar,
            username=new_username,
            first_name=new_first_name,
            last_name=new_last_name
        )

        # ✅ Phase 4 - Task 9: Check for tier changes in public_metadata
        tier_changed = False
        old_tier = None
        new_tier = None

        # Note: Clerk sends full event with both data and previous_data in the webhook
        # The data parameter here only contains the current user data
        # Tier change detection would need access to the full event object
        # For now, we'll just log profile updates. Tier changes are primarily
        # handled via Stripe webhooks, not Clerk.

        # Log profile update
        if self.activity_log_repo:
            await self.activity_log_repo.log_activity(
                user_id=user_id,
                action="profile_updated",
                metadata={
                    "avatar_changed": new_avatar is not None,
                    "username_changed": new_username is not None,
                    "name_changed": new_first_name is not None or new_last_name is not None
                },
            )

        logger.info(f"✅ Updated profile for user {user_id}")
        return {"status": "processed"}

    async def _handle_session_created(
        self,
        event: Dict[str, Any],
        data: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Handle session.created event (user login).

        v3.31: 先检查用户是否存在，避免外键约束失败
        (session.created 可能在 user.created 完成之前到达)

        Args:
            event: Full event data
            data: Session data

        Returns:
            Dict with status 'processed'
        """
        user_id = data.get("user_id")
        if user_id:
            try:
                # v3.31: 先检查用户是否存在，避免外键约束失败
                user_check = await self.db_client.table("profiles").select("id").eq("id", user_id).execute()
                if not user_check.data:
                    logger.info(f"User {user_id} not found in profiles, skipping login log (user.created may still be processing)")
                    return {"status": "processed"}
                
                if self.activity_log_repo:
                    await self.activity_log_repo.log_activity(
                        user_id=user_id,
                        action="user_login",
                        metadata={
                            "client_ip": event.get("event_attributes", {}).get("http_request", {}).get("client_ip"),
                            "user_agent": event.get("event_attributes", {}).get("http_request", {}).get("user_agent")
                        },
                    )
            except Exception as e:
                logger.warning(f"Failed to log login: {e}")

        return {"status": "processed"}

    async def _handle_session_ended(
        self,
        event_type: str,
        data: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Handle session.ended/removed/revoked events (user logout).

        Args:
            event_type: Type of session end event
            data: Session data

        Returns:
            Dict with status 'processed'
        """
        user_id = data.get("user_id")
        if user_id:
            if self.activity_log_repo:
                await self.activity_log_repo.log_activity(
                    user_id=user_id,
                    action="user_logout",
                    metadata={"reason": event_type},
                )

        return {"status": "processed"}

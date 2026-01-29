"""
Dependencies Module
FastAPI dependency injection functions

@module dependencies
"""

import jwt
from fastapi import Header, Depends, Request
from infrastructure.repositories import SupabaseUserRepository
from core.database import get_async_db_client
from config import CLERK_PEM_PUBLIC_KEY, CLERK_FRONTEND_API, CLERK_ALLOWED_ORIGINS, TEST_JWT_PUBLIC_KEY
from core.exceptions import UnauthorizedException, ForbiddenException
from domains.identity.exceptions import UserNotFoundException
from domains.shared import access_control

# Aliases for clarity in dependencies
AdminRequiredException = ForbiddenException
MembershipRequiredException = ForbiddenException


def _get_allowed_origins() -> set:
    """
    Get the set of allowed origins for azp verification.

    Combines CLERK_ALLOWED_ORIGINS (comma-separated) with CLERK_FRONTEND_API
    for backwards compatibility.

    Returns:
        Set of allowed origin URLs, or empty set if not configured (permissive mode)
    """
    origins = set()

    # Parse CLERK_ALLOWED_ORIGINS (comma-separated)
    if CLERK_ALLOWED_ORIGINS:
        for origin in CLERK_ALLOWED_ORIGINS.split(","):
            origin = origin.strip()
            if origin:
                origins.add(origin)

    # Legacy: Also accept CLERK_FRONTEND_API
    if CLERK_FRONTEND_API:
        origins.add(CLERK_FRONTEND_API)

    return origins


async def get_current_user(authorization: str = Header(None)):
    """
    Verify Bearer Token and return user profile.
    
    Production: Validates JWT signature using Clerk's public key.
    Development: May fall back to insecure mode if key not configured.
    
    If user doesn't exist in database, creates profile immediately (JIT creation).
    This ensures new users get their 50 signup bonus credits instantly.
    
    Raises:
        UnauthorizedException: If token is invalid
    
    Returns:
        dict: User profile from database
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedException(message="Missing authentication token")
    
    token = authorization.split(" ")[1]
    payload = None
    
    # Production mode: Verify JWT signature + audience/authorized party
    # Supports dual public keys: Clerk (real users) + Test (integration testing)
    if CLERK_PEM_PUBLIC_KEY or TEST_JWT_PUBLIC_KEY:
        payload = None
        last_error = None

        # List of public keys to try (Clerk first, then test key)
        public_keys_to_try = []
        if CLERK_PEM_PUBLIC_KEY:
            public_keys_to_try.append(("clerk", CLERK_PEM_PUBLIC_KEY))
        if TEST_JWT_PUBLIC_KEY:
            public_keys_to_try.append(("test", TEST_JWT_PUBLIC_KEY))

        for key_name, public_key in public_keys_to_try:
            try:
                # v3.27.2: Complete JWT Verification with aud + azp
                #
                # Security layers:
                # 1. RS256 Signature - Cryptographic proof token came from Clerk
                # 2. Expiration (exp) - Automatic by PyJWT, prevents replay attacks
                # 3. Audience (aud) - Verifies token was issued for this API (if configured in Clerk)
                # 4. Authorized Party (azp) - Verifies which frontend origin requested the token
                #
                # Reference: https://clerk.com/docs/backend-requests/handling/manual-jwt

                # Check if token has 'aud' claim for proper verification
                # First decode without verification to inspect claims
                unverified = jwt.decode(token, options={"verify_signature": False})
                token_has_aud = "aud" in unverified

                if token_has_aud and CLERK_FRONTEND_API and key_name == "clerk":
                    # Token has 'aud' claim - use standard JWT audience verification
                    payload = jwt.decode(
                        token,
                        public_key,
                        algorithms=["RS256"],
                        audience=CLERK_FRONTEND_API,
                        options={"verify_aud": True}
                    )
                else:
                    # No 'aud' claim or test key - decode without audience verification
                    payload = jwt.decode(
                        token,
                        public_key,
                        algorithms=["RS256"],
                        options={"verify_aud": False}
                    )

                # Additionally verify azp (Authorized Party) if configured
                # This provides defense-in-depth by checking frontend origin
                # Skip azp check for test tokens
                if key_name == "clerk":
                    allowed_origins = _get_allowed_origins()
                    if allowed_origins:
                        token_azp = payload.get("azp")
                        if token_azp and token_azp not in allowed_origins:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(
                                f"[Security] Token azp '{token_azp}' not in allowed origins. "
                                f"Allowed: {allowed_origins}"
                            )
                            raise UnauthorizedException(
                                message="Invalid token: unauthorized origin"
                            )

                # Signature verified successfully
                break

            except jwt.ExpiredSignatureError:
                raise UnauthorizedException(message="Token expired")
            except jwt.InvalidTokenError as e:
                last_error = e
                continue  # Try next public key

        if payload is None:
            raise UnauthorizedException(message=f"Invalid token: {str(last_error)}")

        user_id = payload.get("sub")
    else:
        # Development mode: Decode without verification (UNSAFE)
        # ⚠️ WARNING: This mode should NEVER be used in production!
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            "[Security] JWT verification is DISABLED! "
            "CLERK_PEM_PUBLIC_KEY is not configured. "
            "This is ONLY acceptable in local development."
        )
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            user_id = payload.get("sub")
        except Exception:
            raise UnauthorizedException(message="Invalid token format")
    
    if not user_id:
        raise UnauthorizedException(message="Invalid token: no user_id")
    
    # ✅ 修复：验证 user_id 格式（Clerk user_id 应该以 "user_" 开头）
    import logging
    import asyncio
    logger = logging.getLogger(__name__)
    
    if not user_id.startswith("user_"):
        logger.warning(
            f"⚠️ Unexpected user_id format: {user_id}. "
            f"Expected Clerk format 'user_xxx'. This may indicate a configuration issue.",
            extra={
                "user_id": user_id,
                "action": "unexpected_user_id_format",
                "jwt_claims_keys": list(payload.keys()) if payload else []
            }
        )

    # Get user profile from database using repository
    db_client = await get_async_db_client()
    user_repo = SupabaseUserRepository(db_client)
    
    # ✅ 修复：增加重试机制，防止偶发的连接问题导致误触发 JIT
    profile = await user_repo.get_by_id(user_id)
    
    if profile is None:
        # 第一次查询返回 None，可能是真的不存在，也可能是连接问题
        # 短暂等待后重试一次
        await asyncio.sleep(0.1)
        profile = await user_repo.get_by_id(user_id)
        
        if profile is not None:
            # 重试成功，说明之前可能是连接问题
            logger.info(
                f"ℹ️ User {user_id} found on retry (initial query may have had connection issue)",
                extra={"user_id": user_id, "action": "found_on_retry"}
            )

    # JIT (Just-In-Time) user creation: if user doesn't exist, create immediately
    # This ensures new users get their 50 signup bonus credits instantly,
    # without waiting for the Clerk webhook to be processed
    #
    # Architecture: Webhook-First with Graceful Fallback
    # - Primary path: Webhook creates user (95% of cases)
    # - Fallback path: JIT creates user if webhook hasn't arrived yet (5% safety net)
    # - Uses idempotent create_or_get() to handle race conditions safely
    if not profile:
        # ✅ 修复：增强日志，记录 JWT 中的字段信息，帮助诊断问题
        jwt_email = payload.get("email") or payload.get("primary_email")
        jwt_username = payload.get("username")
        
        logger.warning(
            f"⚠️ User {user_id} not found in database after retry, triggering JIT fallback.",
            extra={
                "user_id": user_id,
                "action": "jit_fallback_triggered",
                "jwt_has_email": bool(jwt_email),
                "jwt_has_username": bool(jwt_username),
                "jwt_claims_keys": list(payload.keys()) if payload else [],
            }
        )
        
        # ✅ 修复：如果 JWT 中缺少 email，记录更严重的警告
        if not jwt_email:
            logger.error(
                f"🚨 JIT creating user {user_id} WITHOUT email! "
                f"Please configure Clerk sessionClaims to include 'email' field. "
                f"Available JWT claims: {list(payload.keys()) if payload else []}"
            )
        
        # ✅ Sentry: 捕获 JIT Fallback 事件（需要关注）
        try:
            from infrastructure.monitoring.sentry_helpers import capture_jit_fallback
            email = payload.get("email") or payload.get("primary_email") or "unknown"
            capture_jit_fallback(user_id, email, reason="webhook_not_arrived")
        except Exception:
            pass  # Don't let Sentry errors break the flow
        
        # Extract user info from JWT payload
        # Clerk JWT typically includes these fields in sessionClaims
        email = payload.get("email") or payload.get("primary_email") or ""
        username = payload.get("username")
        first_name = payload.get("first_name")
        last_name = payload.get("last_name")
        avatar_url = payload.get("image_url") or payload.get("picture")

        # Create user profile with factory method (includes all fields now)
        from domains.identity.aggregates import UserProfile
        
        user_profile = UserProfile.create_new(
            user_id=user_id,
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            avatar_url=avatar_url,
            display_name=username or first_name or email.split("@")[0] if email else None
        )
        
        # Idempotent create: safe even if webhook creates user simultaneously
        # Returns (profile, was_created) - was_created=True if we created it
        profile, was_created = await user_repo.create_or_get(user_profile, source='jit')
        
        if was_created:
            # JIT successfully created user (webhook hadn't arrived)
            logger.info(
                f"✅ JIT created user {user_id} (webhook fallback worked)",
                extra={
                    "user_id": user_id,
                    "source": "jit",
                    "action": "created",
                    "email": email
                }
            )
            
            # Optional: Send alert to monitor webhook health
            # This helps track if webhooks are consistently delayed
            try:
                # You can integrate with Sentry/PagerDuty/Slack here
                logger.warning(
                    f"[ALERT] JIT Fallback Triggered for user {user_id}",
                    extra={
                        "severity": "warning",
                        "user_id": user_id,
                        "email": email
                    }
                )
            except Exception:
                pass  # Don't fail user request if alerting fails
        else:
            # Webhook created user while we were preparing JIT create
            # This is the happy path - race condition handled gracefully
            logger.info(
                f"ℹ️ User {user_id} was created by webhook during JIT attempt",
                extra={
                    "user_id": user_id,
                    "action": "race_handled_gracefully"
                }
            )

    return profile


async def require_admin(user = Depends(get_current_user)):
    """
    Admin permission guard - checks profiles.role = 'admin'.

    Raises:
        AdminRequiredException: If user is not an admin

    Returns:
        dict: User info dict for admin operations
    """
    # Check role from UserProfile
    user_role = getattr(user, 'role', None)
    
    # Handle both UserRole enum and string
    if user_role is None:
        raise AdminRequiredException()
    
    role_value = user_role.value if hasattr(user_role, 'value') else str(user_role)
    
    if role_value != 'admin':
        raise AdminRequiredException()
    
    # Return dict for compatibility with existing admin endpoints
    return {
        "id": user.user_id,
        "email": user.email,
        "role": role_value,
    }


async def require_member(user = Depends(get_current_user)):
    """
    Member permission guard (Starter/Pro only).

    Raises:
        MembershipRequiredException: If user is not a member

    Returns:
        UserProfile: User profile (confirmed member)
    """
    # Convert UserProfile to dict for access_control check
    user_dict = {
        "tier": user.tier.value if hasattr(user.tier, 'value') else user.tier,
        "subscription_status": user.subscription_status,
    }
    if not access_control.is_member(user_dict):
        raise MembershipRequiredException()
    return user


async def require_pro(user = Depends(get_current_user)):
    """
    Pro tier permission guard.

    Raises:
        MembershipRequiredException: If user is not Pro

    Returns:
        UserProfile: User profile (confirmed Pro)
    """
    # Convert UserProfile to dict for access_control check
    tier_value = user.tier.value if hasattr(user.tier, 'value') else user.tier
    user_dict = {
        "tier": tier_value,
        "subscription_status": user.subscription_status,
    }
    # Accept both t3 (Pro) and t4 (Enterprise)
    if not access_control.is_member(user_dict) or tier_value not in ("t3", "t4"):
        raise MembershipRequiredException("Pro features")
    return user


async def optional_user(authorization: str = Header(None)):
    """
    Optional user authentication.
    Returns user if authenticated, None otherwise.
    Does not raise exceptions for missing/invalid tokens.

    Returns:
        dict | None: User profile or None
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    try:
        return await get_current_user(authorization)
    except (UnauthorizedException, UserNotFoundException):
        # Expected authentication failures - return None
        return None
    except Exception as e:
        # Unexpected errors - log and return None
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[Auth] Unexpected error in optional_user: {e}", exc_info=True)
        return None


# Alias for backward compatibility
get_current_user_optional = optional_user


# ============================================================================
# UserWithWorkspace - User Context with Workspace (v3.33)
# ============================================================================

from dataclasses import dataclass
from domains.identity.aggregates import UserProfile
from domains.workspace import WorkspaceService


@dataclass
class UserWithWorkspace:
    """
    User context with their default workspace.

    Used by APIs that need workspace_id for data isolation.
    Workspace is created automatically on first access (lazy initialization).

    @version 1.0.0 (v3.33 Workspace + Tag Phase 2.5)
    """
    user: UserProfile
    workspace_id: str

    @property
    def user_id(self) -> str:
        """Convenience property to access user_id."""
        return self.user.user_id


async def get_current_user_with_workspace(
    request: Request,
    user: UserProfile = Depends(get_current_user),
) -> UserWithWorkspace:
    """
    Get current user with their active workspace.

    Workspace resolution order:
    1. X-Workspace-Id header (if provided and valid)
    2. Default workspace (fallback, auto-created if needed)

    The X-Workspace-Id header allows the frontend to specify which workspace
    the user is currently viewing, enabling data isolation per workspace.

    @version 2.0.0 (v3.45 Workspace data isolation)

    Args:
        request: FastAPI request (for reading X-Workspace-Id header)
        user: Current authenticated user (from get_current_user)

    Returns:
        UserWithWorkspace: User with their active workspace_id
    """
    from container import get_container

    container = get_container()
    workspace_service = await container.get_workspace_service()

    # Check for explicit workspace selection via header
    requested_workspace_id = request.headers.get("X-Workspace-Id")

    if requested_workspace_id:
        # Validate: user must own or be a member of this workspace
        workspace = await workspace_service.get_by_id(requested_workspace_id)
        if workspace and workspace.owner_id == user.user_id:
            return UserWithWorkspace(user=user, workspace_id=workspace.id)

        # Check membership (user might be a member, not owner)
        try:
            member_service = await container.get_member_service()
            await member_service._verify_membership(requested_workspace_id, user.user_id)
            return UserWithWorkspace(user=user, workspace_id=requested_workspace_id)
        except (ValueError, Exception):
            # Invalid workspace or not a member — fall back to default
            pass

    # Fallback: use default workspace (auto-created if needed)
    workspace = await workspace_service.get_or_create_default(user.user_id)
    return UserWithWorkspace(user=user, workspace_id=workspace.id)


# ============================================================================
# Analytics Service Dependency
# ============================================================================

from functools import lru_cache
from domains.analytics import AnalyticsService, IAnalyticsRepository
from infrastructure.repositories.analytics_events_repository import (
    SupabaseAnalyticsEventsRepository
)


@lru_cache()
def get_analytics_service() -> AnalyticsService:
    """
    Get Analytics Service singleton instance.

    This service provides a unified interface for analytics event tracking:
    - Frontend batch events (process_and_save_events)
    - Backend server-side tracking (track_event, track_ai_generation, etc.)

    Uses dependency injection with Repository pattern for clean architecture.

    v3.26: Simplified to use sync client directly (removed asyncio.run).
    For async contexts, the Repository handles async operations internally.

    Returns:
        AnalyticsService: Singleton instance
    """
    # Use sync client for initialization (Repository handles async internally)
    from core.database import supabase
    repository: IAnalyticsRepository = SupabaseAnalyticsEventsRepository(supabase)
    return AnalyticsService(repository)


# Global singleton for non-FastAPI contexts
# (e.g., background tasks, webhooks, domain services)
analytics_service = None

def get_global_analytics_service() -> AnalyticsService:
    """
    Get global analytics service instance (non-async initialization).
    
    Use this in contexts where FastAPI dependency injection is not available:
    - Background tasks
    - Webhook handlers
    - Domain services
    
    Returns:
        AnalyticsService: Global singleton instance
    """
    global analytics_service
    if analytics_service is None:
        from core.database import supabase
        repository = SupabaseAnalyticsEventsRepository(supabase)
        analytics_service = AnalyticsService(repository)
    return analytics_service


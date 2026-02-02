"""
Dependencies Module
FastAPI dependency injection functions

Self-hosted auth: HS256 JWT verification via TokenService.

@module dependencies
"""

import logging
from uuid import UUID

from fastapi import Header, Depends, Request
from infrastructure.repositories import SupabaseUserRepository
from core.database import get_async_db_client
from core.exceptions import UnauthorizedException, ForbiddenException
from domains.identity.exceptions import UserNotFoundException
from domains.shared import access_control

logger = logging.getLogger(__name__)

# Aliases for clarity in dependencies
AdminRequiredException = ForbiddenException
MembershipRequiredException = ForbiddenException


async def get_current_user(authorization: str = Header(None)):
    """
    Verify self-hosted JWT access token and return user profile.

    Uses TokenService (HS256) to verify the token, then looks up the user
    profile from the database. Supports dual-key rotation via
    AUTH_JWT_SECRET + AUTH_JWT_SECRET_OLD.

    No JIT user creation — users must register via /auth/register first.

    Raises:
        UnauthorizedException: If token is missing, invalid, or expired
        UnauthorizedException: If user profile not found in database

    Returns:
        UserProfile: User profile entity from database
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedException(message="Missing authentication token")

    token = authorization.split(" ")[1]

    # Verify JWT using self-hosted TokenService (HS256 + dual-key rotation)
    from container import get_container
    from domains.auth.exceptions import (
        TokenExpiredException,
        TokenInvalidException,
    )

    container = get_container()
    token_service = await container.get_token_service()

    try:
        payload = token_service.verify_access_token(token)
    except TokenExpiredException:
        raise UnauthorizedException(message="Token expired")
    except TokenInvalidException as e:
        raise UnauthorizedException(message=f"Invalid token: {e.message}")

    user_id = str(payload.sub)  # UUID → string for profile lookup

    # Look up user profile from database
    db_client = await get_async_db_client()
    user_repo = SupabaseUserRepository(db_client)
    profile = await user_repo.get_by_id(user_id)

    if profile is None:
        logger.warning(
            f"Authenticated user not found in profiles: {user_id[:8]}...",
            extra={"user_id_prefix": user_id[:8], "action": "user_not_found"},
        )
        raise UnauthorizedException(message="User profile not found")

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


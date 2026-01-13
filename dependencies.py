"""
Dependencies Module
FastAPI dependency injection functions

@module dependencies
"""

import jwt
from fastapi import Header, Depends
from infrastructure.repositories import SupabaseUserRepository
from core.database import get_async_db_client
from config import CLERK_PEM_PUBLIC_KEY
from core.exceptions import UnauthorizedException, ForbiddenException
from domains.identity.exceptions import UserNotFoundException
from domains.shared import access_control

# Aliases for clarity in dependencies
AdminRequiredException = ForbiddenException
MembershipRequiredException = ForbiddenException


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
    
    # Production mode: Verify JWT signature
    if CLERK_PEM_PUBLIC_KEY:
        try:
            payload = jwt.decode(
                token, 
                CLERK_PEM_PUBLIC_KEY, 
                algorithms=["RS256"], 
                options={"verify_aud": False}
            )
            user_id = payload.get("sub")
        except jwt.ExpiredSignatureError:
            raise UnauthorizedException(message="Token expired")
        except jwt.InvalidTokenError as e:
            raise UnauthorizedException(message=f"Invalid token: {str(e)}")
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

    # Get user profile from database using repository
    db_client = await get_async_db_client()
    user_repo = SupabaseUserRepository(db_client)
    profile = await user_repo.get_by_id(user_id)

    # JIT (Just-In-Time) user creation: if user doesn't exist, create immediately
    # This ensures new users get their 50 signup bonus credits instantly,
    # without waiting for the Clerk webhook to be processed
    #
    # Architecture: Webhook-First with Graceful Fallback
    # - Primary path: Webhook creates user (95% of cases)
    # - Fallback path: JIT creates user if webhook hasn't arrived yet (5% safety net)
    # - Uses idempotent create_or_get() to handle race conditions safely
    if not profile:
        import logging
        logger = logging.getLogger(__name__)
        
        # Log JIT fallback trigger (helps monitor webhook health)
        logger.warning(
            f"⚠️ User {user_id} not found in database, triggering JIT fallback. "
            f"This indicates potential webhook delivery issue.",
            extra={
                "user_id": user_id,
                "action": "jit_fallback_triggered",
                "email": payload.get("email", "unknown")
            }
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
    Admin permission guard.

    Note: Admin system is not fully implemented in UserProfile.
    This function currently rejects all requests.

    Raises:
        AdminRequiredException: Always raised (admin not implemented)

    Returns:
        UserProfile: User profile (never returns)
    """
    # TODO: Implement proper admin check via UserProfile or separate admin table
    raise AdminRequiredException()


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


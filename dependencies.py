"""
Dependencies Module
FastAPI dependency injection functions

@module dependencies
"""

import jwt
from fastapi import Header, Depends
from infrastructure.repositories import SupabaseUserRepository
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
    user_repo = SupabaseUserRepository()
    profile = await user_repo.get_by_id(user_id)

    # JIT (Just-In-Time) user creation: if user doesn't exist, create immediately
    # This ensures new users get their 50 signup bonus credits instantly,
    # without waiting for the Clerk webhook to be processed
    if not profile:
        # Extract user info from JWT payload
        # Clerk JWT typically includes these fields in sessionClaims
        email = payload.get("email") or payload.get("primary_email") or ""
        username = payload.get("username") or payload.get("name") or ""
        avatar_url = payload.get("image_url") or payload.get("picture") or ""
        first_name = payload.get("first_name") or ""
        last_name = payload.get("last_name") or ""

        # Create user profile with factory method
        from domains.identity.aggregates import UserProfile
        # Construct display_name from available info
        display_name = username or f"{first_name} {last_name}".strip() or email.split("@")[0]
        user_profile = UserProfile.create_new(
            user_id=user_id,
            email=email,
            display_name=display_name or None
        )
        # Set avatar_url if available
        if avatar_url:
            user_profile.avatar_url = avatar_url
        await user_repo.create(user_profile)

        # Fetch the newly created profile
        profile = await user_repo.get_by_id(user_id)

        if not profile:
            raise UserNotFoundException(user_id)

    return profile


async def require_admin(user: dict = Depends(get_current_user)):
    """
    Admin permission guard.
    
    Raises:
        AdminRequiredException: If user is not admin
    
    Returns:
        dict: User profile (confirmed admin)
    """
    if user.get("role") != "admin":
        raise AdminRequiredException()
    return user


async def require_member(user: dict = Depends(get_current_user)):
    """
    Member permission guard (Starter/Pro only).

    Raises:
        MembershipRequiredException: If user is not a member

    Returns:
        dict: User profile (confirmed member)
    """
    if not access_control.is_member(user):
        raise MembershipRequiredException()
    return user


async def require_pro(user: dict = Depends(get_current_user)):
    """
    Pro tier permission guard.

    Raises:
        MembershipRequiredException: If user is not Pro

    Returns:
        dict: User profile (confirmed Pro)
    """
    if not access_control.is_member(user) or user.get("tier") != "pro":
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


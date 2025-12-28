"""
Dependencies Module
FastAPI dependency injection functions

@module dependencies
"""

import jwt
from fastapi import HTTPException, Header, Depends
from db_service import get_user_profile, is_member
from config import CLERK_PEM_PUBLIC_KEY


async def get_current_user(authorization: str = Header(None)):
    """
    Verify Bearer Token and return user profile.
    
    Production: Validates JWT signature using Clerk's public key.
    Development: May fall back to insecure mode if key not configured.
    
    Raises:
        HTTPException: 401 if token is invalid or user not found
    
    Returns:
        dict: User profile from database
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Token")
    
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
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid Token: {str(e)}")
    else:
        # Development mode: Decode without verification (UNSAFE)
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            user_id = payload.get("sub")
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid Token format")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid Token: no user_id")
    
    # Get user profile from database
    profile = get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=401, detail="User not found in database")
    
    return profile


async def require_admin(user: dict = Depends(get_current_user)):
    """
    Admin permission guard.
    
    Raises:
        HTTPException: 403 if user is not admin
    
    Returns:
        dict: User profile (confirmed admin)
    """
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_member(user: dict = Depends(get_current_user)):
    """
    Member permission guard (Starter/Pro only).
    
    Raises:
        HTTPException: 403 if user is not a member
    
    Returns:
        dict: User profile (confirmed member)
    """
    if not is_member(user):
        raise HTTPException(status_code=403, detail="Membership required")
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
    except HTTPException:
        return None


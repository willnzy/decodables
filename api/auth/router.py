"""
Auth API Router — Public authentication endpoints.

All endpoints are public (no auth required) except:
- POST /auth/change-password (requires auth)
- POST /auth/logout-all (requires auth)
- GET  /auth/sessions (requires auth)
- DELETE /auth/sessions/{id} (requires auth)
- DELETE /auth/account (requires auth)
- POST /auth/resend-verification (requires auth)
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import ValidationError

from container import get_container
from domains.auth.exceptions import (
    AccountDisabledException,
    AccountLockedException,
    DisposableEmailException,
    EmailAlreadyExistsException,
    EmailNotVerifiedException,
    InvalidCredentialsException,
    InvalidVerificationTokenException,
    SessionNotFoundException,
    TokenExpiredException,
    TokenReuseDetectedException,
    TokenRevokedException,
    WeakPasswordException,
)
from domains.auth.service import AuthService
from domains.auth.value_objects import DeviceInfo
from domains.identity.constants import SIGNUP_BONUS_CREDITS
from infrastructure.rate_limiter import limiter

from .schemas import (
    AuthTokenResponse,
    ChangePasswordRequest,
    DeleteAccountRequest,
    ErrorResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    ResetPasswordRequest,
    SessionInfo,
    SessionListResponse,
    SuccessResponse,
    UserInfo,
    VerifyEmailRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ===================================================================
# Dependency Injection
# ===================================================================

async def get_auth_service() -> AuthService:
    """Get AuthService from container."""
    container = get_container()
    return await container.get_auth_service()


def _get_device_info(request: Request) -> DeviceInfo:
    """Extract device information from the HTTP request."""
    return DeviceInfo.from_request(
        user_agent=request.headers.get("user-agent"),
        ip_address=_get_client_ip(request),
    )


def _get_client_ip(request: Request) -> Optional[str]:
    """Get client IP, respecting X-Forwarded-For for proxied requests."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


# ===================================================================
# Auth-Required Dependency (uses self-hosted JWT)
# ===================================================================

async def get_current_auth_user_id(request: Request) -> UUID:
    """
    Extract and verify user_id from self-hosted JWT access token.

    This is for auth-protected endpoints within the auth module.
    Uses TokenService for JWT verification.
    """
    from domains.auth.token_service import TokenService
    from domains.auth.exceptions import TokenInvalidException

    authorization = request.headers.get("authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise TokenInvalidException(message="Missing authentication token")

    token = authorization.split(" ")[1]

    container = get_container()
    token_service: TokenService = await container.get_token_service()
    payload = token_service.verify_access_token(token)
    return payload.sub


# ===================================================================
# Public Endpoints
# ===================================================================

@router.post(
    "/register",
    response_model=AuthTokenResponse,
    responses={422: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
@limiter.limit("5/hour")
async def register(
    request: Request,
    body: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    """
    Register a new user account.

    Creates auth_users + profiles atomically, sends verification email,
    returns access + refresh tokens.
    """
    device_info = _get_device_info(request)

    result = await auth_service.register(
        email=body.email,
        password=body.password,
        display_name=body.display_name,
        device_info=device_info,
        signup_bonus=SIGNUP_BONUS_CREDITS,
    )

    return AuthTokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type=result["token_type"],
        user=UserInfo(**result["user"]),
    )


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    """
    Authenticate with email and password.

    Returns access + refresh tokens on success.
    """
    device_info = _get_device_info(request)

    result = await auth_service.login(
        email=body.email,
        password=body.password,
        device_info=device_info,
    )

    return AuthTokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type=result["token_type"],
        user=UserInfo(**result["user"]),
    )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    responses={401: {"model": ErrorResponse}},
)
@limiter.limit("30/minute")
async def refresh_token(
    request: Request,
    body: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> RefreshTokenResponse:
    """
    Refresh access token using a refresh token.

    With rotate=true (default), the old refresh token is revoked
    and a new one is issued.
    """
    device_info = _get_device_info(request)

    result = await auth_service.refresh_token(
        refresh_token=body.refresh_token,
        device_info=device_info,
        rotate=body.rotate,
    )

    return RefreshTokenResponse(
        access_token=result["access_token"],
        refresh_token=result.get("refresh_token"),
        token_type=result.get("token_type", "bearer"),
    )


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    body: LogoutRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """Logout current session by revoking the refresh token."""
    await auth_service.logout(refresh_token=body.refresh_token)
    return SuccessResponse(message="Logged out successfully")


@router.post(
    "/verify-email",
    response_model=SuccessResponse,
    responses={400: {"model": ErrorResponse}},
)
async def verify_email(
    body: VerifyEmailRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """Verify email address using the token from the verification link."""
    await auth_service.verify_email(
        token=body.token,
        email=body.email,
    )
    return SuccessResponse(message="Email verified successfully")


@router.post(
    "/forgot-password",
    response_model=SuccessResponse,
)
@limiter.limit("3/hour")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """
    Request password reset email.

    Always returns success (prevents email enumeration).
    """
    await auth_service.request_password_reset(email=body.email)
    return SuccessResponse(
        message="If an account exists with this email, a reset link has been sent."
    )


@router.post(
    "/reset-password",
    response_model=SuccessResponse,
    responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def reset_password(
    body: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """Reset password using the token from the reset email."""
    await auth_service.reset_password(
        token=body.token,
        email=body.email,
        new_password=body.new_password,
    )
    return SuccessResponse(message="Password has been reset. Please sign in.")


# ===================================================================
# Authenticated Endpoints
# ===================================================================

@router.post(
    "/change-password",
    response_model=SuccessResponse,
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def change_password(
    body: ChangePasswordRequest,
    user_id: UUID = Depends(get_current_auth_user_id),
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """Change password (requires current password verification)."""
    await auth_service.change_password(
        user_id=user_id,
        current_password=body.current_password,
        new_password=body.new_password,
        revoke_other_sessions=body.revoke_other_sessions,
    )
    return SuccessResponse(message="Password changed successfully")


@router.post("/logout-all", response_model=SuccessResponse)
async def logout_all(
    user_id: UUID = Depends(get_current_auth_user_id),
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """Logout from all devices."""
    await auth_service.logout_all(user_id=user_id)
    return SuccessResponse(message="Logged out from all devices")


@router.post(
    "/resend-verification",
    response_model=SuccessResponse,
)
async def resend_verification(
    user_id: UUID = Depends(get_current_auth_user_id),
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """Resend email verification link."""
    await auth_service.resend_verification_email(user_id=user_id)
    return SuccessResponse(message="Verification email sent")


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    user_id: UUID = Depends(get_current_auth_user_id),
    auth_service: AuthService = Depends(get_auth_service),
) -> SessionListResponse:
    """List all active sessions (multi-device management)."""
    sessions = await auth_service.get_sessions(user_id=user_id)
    return SessionListResponse(
        sessions=[SessionInfo(**s) for s in sessions],
        total=len(sessions),
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=SuccessResponse,
    responses={404: {"model": ErrorResponse}},
)
async def revoke_session(
    session_id: UUID,
    user_id: UUID = Depends(get_current_auth_user_id),
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """Revoke a specific session (kick a device)."""
    await auth_service.revoke_session(
        user_id=user_id,
        session_id=session_id,
    )
    return SuccessResponse(message="Session revoked")


@router.delete(
    "/account",
    response_model=SuccessResponse,
    responses={401: {"model": ErrorResponse}},
)
async def delete_account(
    body: DeleteAccountRequest,
    user_id: UUID = Depends(get_current_auth_user_id),
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """
    Delete user account permanently.

    Requires password verification. This is irreversible.
    """
    await auth_service.delete_account(
        user_id=user_id,
        password=body.password,
    )
    return SuccessResponse(message="Account deleted")

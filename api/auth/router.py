"""
Auth API Router — Public and authenticated endpoints.

Registration (3-step OTP):
  POST /auth/register/send-otp
  POST /auth/register/verify-otp
  POST /auth/register/complete

Unified OTP (change-password / delete-account / forgot-password):
  POST /auth/otp/send
  POST /auth/otp/verify

Password reset:
  POST /auth/forgot-password/reset

All other endpoints:
  POST /auth/login
  POST /auth/refresh
  POST /auth/logout
  POST /auth/logout-all           (auth required)
  POST /auth/change-password      (auth required)
  POST /auth/delete-account       (auth required)
  GET  /auth/sessions             (auth required)
  DELETE /auth/sessions/{id}      (auth required)
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from container import get_container
from domains.auth.constants import (
    OTP_PURPOSE_CHANGE_PASSWORD,
    OTP_PURPOSE_DELETE_ACCOUNT,
    OTP_PURPOSE_FORGOT_PASSWORD,
)
from domains.auth.exceptions import TokenInvalidException
from domains.auth.service import AuthService
from domains.auth.token_service import TokenService
from domains.auth.value_objects import DeviceInfo
from domains.identity.constants import SIGNUP_BONUS_CREDITS
from infrastructure.rate_limiter import limiter

from .schemas import (
    AuthTokenResponse,
    ChangePasswordRequest,
    CompleteRegistrationRequest,
    DeleteAccountRequest,
    ErrorResponse,
    ForgotPasswordResetRequest,
    LoginRequest,
    LogoutRequest,
    OtpSentResponse,
    OtpVerifiedResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    SendOtpRequest,
    SendRegistrationOtpRequest,
    SessionInfo,
    SessionListResponse,
    SuccessResponse,
    UserInfo,
    VerifyOtpRequest,
    VerifyRegistrationOtpRequest,
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


async def get_token_service() -> TokenService:
    """Get TokenService from container."""
    container = get_container()
    return await container.get_token_service()


def _get_device_info(request: Request) -> DeviceInfo:
    """Extract device information from the HTTP request."""
    return DeviceInfo.from_request(
        user_agent=request.headers.get("user-agent"),
        ip_address=_get_client_ip(request),
    )


def _get_client_ip(request: Request) -> Optional[str]:
    """Get client IP from trusted proxy headers.

    Priority:
    1. CF-Connecting-IP (Cloudflare)
    2. X-Real-IP (Railway/Nginx)
    3. X-Forwarded-For rightmost hop (closest to server, most trusted)
    4. Direct connection IP
    """
    # Cloudflare
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()

    # Railway / Nginx
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # X-Forwarded-For — rightmost entry is added by the closest proxy
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ips = [ip.strip() for ip in forwarded.split(",")]
        return ips[-1] if ips else None

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
    authorization = request.headers.get("authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise TokenInvalidException(message="Missing authentication token")

    token = authorization.split(" ")[1]

    container = get_container()
    token_service: TokenService = await container.get_token_service()
    payload = token_service.verify_access_token(token)
    return payload.sub


# ===================================================================
# Registration (3-step OTP)
# ===================================================================

@router.post(
    "/register/send-otp",
    response_model=OtpSentResponse,
    responses={
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
@limiter.limit("5/hour")
async def register_send_otp(
    request: Request,
    body: SendRegistrationOtpRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> OtpSentResponse:
    """
    Registration step 1: Send OTP verification code to email.

    Validates email, checks for restorable accounts, sends 6-digit OTP.
    If a restorable soft-deleted account exists, returns has_restorable_account=true.
    """
    result = await auth_service.send_registration_otp(email=body.email)

    return OtpSentResponse(
        success=True,
        message="Verification code sent",
        has_restorable_account=result.get("has_restorable_account", False),
    )


@router.post(
    "/register/verify-otp",
    response_model=OtpVerifiedResponse,
    responses={400: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
@limiter.limit("10/hour")
async def register_verify_otp(
    request: Request,
    body: VerifyRegistrationOtpRequest,
    auth_service: AuthService = Depends(get_auth_service),
    token_service: TokenService = Depends(get_token_service),
) -> OtpVerifiedResponse:
    """
    Registration step 2: Verify OTP code.

    Returns a short-lived register_token (JWT, 15 min) for step 3.
    """
    result = await auth_service.verify_registration_otp(
        email=body.email,
        otp_code=body.otp_code,
    )

    # Wrap user_id in a short-lived JWT for secure handoff to step 3
    register_token = token_service.create_purpose_token(
        user_id=UUID(result["user_id"]),
        purpose="register",
        expire_minutes=15,
    )

    return OtpVerifiedResponse(
        success=True,
        register_token=register_token,
    )


@router.post(
    "/register/complete",
    response_model=AuthTokenResponse,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
@limiter.limit("5/hour")
async def register_complete(
    request: Request,
    body: CompleteRegistrationRequest,
    auth_service: AuthService = Depends(get_auth_service),
    token_service: TokenService = Depends(get_token_service),
) -> AuthTokenResponse:
    """
    Registration step 3: Set password and create profile.

    Requires register_token from step 2.
    With restore_account=true, restores a previously deleted account.
    """
    # Verify the register_token JWT
    user_id = token_service.verify_purpose_token(
        token=body.register_token,
        expected_purpose="register",
    )

    device_info = _get_device_info(request)

    if body.restore_account:
        # Restore flow: look up email from the pending user, then restore
        email = await auth_service.get_pending_user_email(user_id)
        if email is None:
            raise TokenInvalidException(message="Invalid register token")

        result = await auth_service.restore_account(
            email=email,
            password=body.password,
            device_info=device_info,
        )
    else:
        # Normal registration completion
        result = await auth_service.complete_registration(
            user_id=str(user_id),
            password=body.password,
            display_name=body.display_name,
            device_info=device_info,
            signup_bonus=SIGNUP_BONUS_CREDITS,
        )

    return AuthTokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type=result.get("token_type", "bearer"),
        user=UserInfo(**result["user"]),
    )


# ===================================================================
# Login & Token Management
# ===================================================================

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
        token_type=result.get("token_type", "bearer"),
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


# ===================================================================
# Unified OTP (change-password / delete-account / forgot-password)
# ===================================================================

@router.post(
    "/otp/send",
    response_model=OtpSentResponse,
    responses={429: {"model": ErrorResponse}},
)
@limiter.limit("3/hour")
async def otp_send(
    request: Request,
    body: SendOtpRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> OtpSentResponse:
    """
    Send OTP for password change, account deletion, or password reset.

    purpose="forgot_password": public, email required in body.
    purpose="change_password"|"delete_account": auth required, email from JWT.
    """
    if body.purpose == OTP_PURPOSE_FORGOT_PASSWORD:
        # Public: use email from request body
        if not body.email:
            raise TokenInvalidException(
                message="Email is required for forgot_password"
            )
        result = await auth_service.send_password_reset_otp(email=body.email)
        return OtpSentResponse(
            success=True,
            message=result.get(
                "message",
                "If an account exists with this email, a verification code has been sent.",
            ),
        )

    # Authenticated purposes: extract user_id from JWT
    auth_user_id = await get_current_auth_user_id(request)

    if body.purpose == OTP_PURPOSE_CHANGE_PASSWORD:
        await auth_service.send_change_password_otp(user_id=auth_user_id)
    elif body.purpose == OTP_PURPOSE_DELETE_ACCOUNT:
        await auth_service.send_delete_account_otp(user_id=auth_user_id)

    return OtpSentResponse(
        success=True,
        message="Verification code sent",
    )


@router.post(
    "/otp/verify",
    response_model=OtpVerifiedResponse,
    responses={400: {"model": ErrorResponse}},
)
@limiter.limit("10/hour")
async def otp_verify(
    request: Request,
    body: VerifyOtpRequest,
    auth_service: AuthService = Depends(get_auth_service),
    token_service: TokenService = Depends(get_token_service),
) -> OtpVerifiedResponse:
    """
    Verify OTP code for change-password, delete-account, or forgot-password.

    Returns an otp_verified_token (JWT, 10 min) for the subsequent action.
    """
    if body.purpose == OTP_PURPOSE_FORGOT_PASSWORD:
        # Public: use email from body
        if not body.email:
            raise TokenInvalidException(
                message="Email is required for forgot_password"
            )
        result = await auth_service.verify_password_reset_otp(
            email=body.email,
            otp_code=body.otp_code,
        )
        target_user_id = UUID(result["user_id"])
    else:
        # Authenticated: extract user_id from JWT
        auth_user_id = await get_current_auth_user_id(request)
        await auth_service.verify_authenticated_otp(
            user_id=auth_user_id,
            otp_code=body.otp_code,
            expected_purpose=body.purpose,
        )
        target_user_id = auth_user_id

    # Create short-lived purpose token
    otp_verified_token = token_service.create_purpose_token(
        user_id=target_user_id,
        purpose=f"otp_verified_{body.purpose}",
        expire_minutes=10,
    )

    return OtpVerifiedResponse(
        success=True,
        otp_verified_token=otp_verified_token,
    )


# ===================================================================
# Password Reset (forgot-password)
# ===================================================================

@router.post(
    "/forgot-password/reset",
    response_model=SuccessResponse,
    responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
@limiter.limit("5/hour")
async def forgot_password_reset(
    request: Request,
    body: ForgotPasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service),
    token_service: TokenService = Depends(get_token_service),
) -> SuccessResponse:
    """
    Reset password using otp_verified_token from /auth/otp/verify.

    Revokes all existing sessions after reset.
    """
    user_id = token_service.verify_purpose_token(
        token=body.otp_verified_token,
        expected_purpose="otp_verified_forgot_password",
    )

    await auth_service.reset_password(
        user_id=str(user_id),
        new_password=body.new_password,
    )

    return SuccessResponse(message="Password has been reset. Please sign in.")


# ===================================================================
# Authenticated Endpoints
# ===================================================================

@router.post(
    "/change-password",
    response_model=SuccessResponse,
    responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
@limiter.limit("5/hour")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    user_id: UUID = Depends(get_current_auth_user_id),
    auth_service: AuthService = Depends(get_auth_service),
    token_service: TokenService = Depends(get_token_service),
) -> SuccessResponse:
    """
    Change password (requires OTP verification + current password).

    The otp_verified_token proves the user verified their email via OTP.
    """
    # Verify the OTP-verified token
    token_user_id = token_service.verify_purpose_token(
        token=body.otp_verified_token,
        expected_purpose="otp_verified_change_password",
    )

    # Ensure token belongs to the authenticated user
    if token_user_id != user_id:
        raise TokenInvalidException(
            message="Token does not match authenticated user"
        )

    await auth_service.change_password(
        user_id=user_id,
        current_password=body.current_password,
        new_password=body.new_password,
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


@router.post(
    "/delete-account",
    response_model=SuccessResponse,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}},
)
@limiter.limit("1/hour")
async def delete_account(
    request: Request,
    body: DeleteAccountRequest,
    user_id: UUID = Depends(get_current_auth_user_id),
    auth_service: AuthService = Depends(get_auth_service),
    token_service: TokenService = Depends(get_token_service),
) -> SuccessResponse:
    """
    Delete user account.

    Requires otp_verified_token from /auth/otp/verify with purpose=delete_account.
    """
    # Verify the OTP-verified token
    token_user_id = token_service.verify_purpose_token(
        token=body.otp_verified_token,
        expected_purpose="otp_verified_delete_account",
    )

    # Ensure token belongs to the authenticated user
    if token_user_id != user_id:
        raise TokenInvalidException(
            message="Token does not match authenticated user"
        )

    await auth_service.delete_account(user_id=user_id)

    return SuccessResponse(message="Account deleted")

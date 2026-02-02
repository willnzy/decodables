"""
Auth API Pydantic schemas — Request and Response models.

3-step OTP registration flow:
  1. POST /auth/register/send-otp      → SendRegistrationOtpRequest
  2. POST /auth/register/verify-otp    → VerifyRegistrationOtpRequest
  3. POST /auth/register/complete      → CompleteRegistrationRequest

Unified OTP flow (change-password / delete-account / forgot-password):
  1. POST /auth/otp/send               → SendOtpRequest
  2. POST /auth/otp/verify             → VerifyOtpRequest

All error responses follow the unified format:
{ "error": str, "message"?: str, "details"?: object }
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


# ===================================================================
# Request Models — Registration (3-step OTP)
# ===================================================================

class SendRegistrationOtpRequest(BaseModel):
    """POST /auth/register/send-otp — Step 1."""
    email: EmailStr


class VerifyRegistrationOtpRequest(BaseModel):
    """POST /auth/register/verify-otp — Step 2."""
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)


class CompleteRegistrationRequest(BaseModel):
    """POST /auth/register/complete — Step 3."""
    register_token: str
    password: str = Field(..., min_length=8, max_length=128)
    display_name: Optional[str] = Field(None, max_length=100)
    restore_account: bool = False


# ===================================================================
# Request Models — Login & Token
# ===================================================================

class LoginRequest(BaseModel):
    """POST /auth/login"""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """POST /auth/refresh"""
    refresh_token: str
    rotate: bool = True


class LogoutRequest(BaseModel):
    """POST /auth/logout"""
    refresh_token: str


# ===================================================================
# Request Models — Unified OTP (change-password / delete / forgot)
# ===================================================================

class SendOtpRequest(BaseModel):
    """
    POST /auth/otp/send

    purpose="forgot_password": public, email required.
    purpose="change_password"|"delete_account": auth required, email from JWT.
    """
    purpose: str = Field(
        ...,
        pattern=r"^(change_password|delete_account|forgot_password)$",
    )
    email: Optional[EmailStr] = None


class VerifyOtpRequest(BaseModel):
    """
    POST /auth/otp/verify

    email required for forgot_password; ignored for authenticated purposes.
    """
    purpose: str = Field(
        ...,
        pattern=r"^(change_password|delete_account|forgot_password)$",
    )
    otp_code: str = Field(..., min_length=6, max_length=6)
    email: Optional[EmailStr] = None


# ===================================================================
# Request Models — Password Reset (forgot-password)
# ===================================================================

class ForgotPasswordResetRequest(BaseModel):
    """POST /auth/forgot-password/reset"""
    otp_verified_token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ===================================================================
# Request Models — Authenticated Actions
# ===================================================================

class ChangePasswordRequest(BaseModel):
    """POST /auth/change-password"""
    otp_verified_token: str
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class DeleteAccountRequest(BaseModel):
    """POST /auth/delete-account"""
    otp_verified_token: str


# ===================================================================
# Response Models
# ===================================================================

class UserInfo(BaseModel):
    """Minimal user information included in auth responses."""
    id: str
    email: str
    email_verified: bool = False
    display_name: Optional[str] = None
    tier: Optional[str] = None
    role: Optional[str] = None


class AuthTokenResponse(BaseModel):
    """
    Standard auth response with tokens.

    Used by register/complete and login endpoints.
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserInfo


class RefreshTokenResponse(BaseModel):
    """
    Token refresh response.

    When rotate=True, includes new refresh_token.
    When rotate=False, only returns new access_token.
    """
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class OtpSentResponse(BaseModel):
    """Response for OTP send endpoints."""
    success: bool = True
    message: str = "Verification code sent"
    has_restorable_account: Optional[bool] = None


class OtpVerifiedResponse(BaseModel):
    """Response for OTP verify endpoints. Returns a temporary token."""
    success: bool = True
    register_token: Optional[str] = None
    otp_verified_token: Optional[str] = None


class SessionInfo(BaseModel):
    """Single session for device management listing."""
    id: str
    device_name: Optional[str] = None
    ip_address: Optional[str] = None
    is_current: bool = False
    last_used_at: Optional[str] = None
    created_at: Optional[str] = None
    expires_at: Optional[str] = None


class SessionListResponse(BaseModel):
    """GET /auth/sessions response."""
    sessions: List[SessionInfo]
    total: int


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """
    Unified error response format.

    Machine-readable error code + human-readable message.
    """
    error: str
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

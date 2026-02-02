"""
Auth API Pydantic schemas — Request and Response models.

All error responses follow the unified format:
{ "error": str, "message"?: str, "details"?: object }
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


# ===================================================================
# Request Models
# ===================================================================

class RegisterRequest(BaseModel):
    """POST /auth/register"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: Optional[str] = Field(None, max_length=100)


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


class VerifyEmailRequest(BaseModel):
    """POST /auth/verify-email"""
    token: str
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    """POST /auth/forgot-password"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """POST /auth/reset-password"""
    token: str
    email: EmailStr
    new_password: str = Field(..., min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    """POST /auth/change-password"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    revoke_other_sessions: bool = True


class DeleteAccountRequest(BaseModel):
    """DELETE /auth/account"""
    password: str


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

    Used by register and login endpoints.
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

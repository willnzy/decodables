"""
Auth domain exceptions.

Domain-specific exceptions for authentication operations.
All inherit from core AppException for consistent error handling.
"""

from typing import Any, Optional

from core.exceptions import AppException, ErrorCode


# ---------------------------------------------------------------------------
# Base Auth Exception
# ---------------------------------------------------------------------------

class AuthException(AppException):
    """Base exception for all auth domain errors."""

    status_code = 400
    default_code = ErrorCode.AUTH_UNAUTHORIZED
    default_message = "Authentication error"


# ---------------------------------------------------------------------------
# Credential Errors
# ---------------------------------------------------------------------------

class InvalidCredentialsException(AuthException):
    """Invalid email or password during login."""

    status_code = 401
    default_code = ErrorCode.AUTH_UNAUTHORIZED
    default_message = "Invalid email or password"


class WeakPasswordException(AuthException):
    """Password does not meet strength requirements."""

    status_code = 422
    default_code = ErrorCode.VALIDATION_ERROR
    default_message = "Password does not meet strength requirements"

    def __init__(self, errors: list[str] | None = None, **kwargs: Any) -> None:
        super().__init__(
            details={"password_errors": errors or []},
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Account State Errors
# ---------------------------------------------------------------------------

class AccountLockedException(AuthException):
    """Account is temporarily locked due to too many failed login attempts."""

    status_code = 403
    default_code = ErrorCode.AUTH_FORBIDDEN
    default_message = "Account is temporarily locked. Please try again later."

    def __init__(self, retry_after_seconds: int = 0, **kwargs: Any) -> None:
        super().__init__(
            details={
                "error": "account_locked",
                "retry_after": retry_after_seconds,
            },
            **kwargs,
        )


class AccountDisabledException(AuthException):
    """Account has been disabled by admin."""

    status_code = 403
    default_code = ErrorCode.AUTH_FORBIDDEN
    default_message = "Account has been disabled"


class EmailNotVerifiedException(AuthException):
    """User's email address has not been verified."""

    status_code = 403
    default_code = ErrorCode.AUTH_FORBIDDEN
    default_message = "Email address not verified. Please check your inbox."


class EmailAlreadyExistsException(AuthException):
    """Email address is already registered."""

    status_code = 409
    default_code = ErrorCode.RESOURCE_ALREADY_EXISTS
    default_message = "An account with this email already exists"


# ---------------------------------------------------------------------------
# Token Errors
# ---------------------------------------------------------------------------

class TokenExpiredException(AuthException):
    """Access or refresh token has expired."""

    status_code = 401
    default_code = ErrorCode.AUTH_TOKEN_EXPIRED
    default_message = "Token has expired. Please sign in again."


class TokenInvalidException(AuthException):
    """Token is malformed or signature verification failed."""

    status_code = 401
    default_code = ErrorCode.AUTH_TOKEN_INVALID
    default_message = "Invalid token"


class TokenRevokedException(AuthException):
    """Refresh token has been revoked (e.g., by logout or rotation)."""

    status_code = 401
    default_code = ErrorCode.AUTH_TOKEN_INVALID
    default_message = "Session has been revoked. Please sign in again."


class TokenReuseDetectedException(AuthException):
    """
    Reuse of a rotated refresh token detected — potential token theft.

    When detected, all sessions in the token family are revoked for security.
    """

    status_code = 401
    default_code = ErrorCode.AUTH_TOKEN_INVALID
    default_message = "Security alert: suspicious session activity detected. All sessions have been revoked."


# ---------------------------------------------------------------------------
# OTP Errors
# ---------------------------------------------------------------------------

class OtpExpiredException(AuthException):
    """OTP code has expired."""

    status_code = 400
    default_code = ErrorCode.VALIDATION_ERROR
    default_message = "Verification code has expired. Please request a new one."


class OtpInvalidException(AuthException):
    """OTP code is invalid (wrong code)."""

    status_code = 400
    default_code = ErrorCode.VALIDATION_ERROR
    default_message = "Invalid verification code"

    def __init__(self, remaining_attempts: int = 0, **kwargs: Any) -> None:
        super().__init__(
            details={"remaining_attempts": remaining_attempts},
            **kwargs,
        )


class OtpMaxAttemptsException(AuthException):
    """Maximum OTP verification attempts exceeded."""

    status_code = 429
    default_code = ErrorCode.VALIDATION_ERROR
    default_message = "Too many failed attempts. Please request a new code."


class OtpCooldownException(AuthException):
    """OTP send cooldown not yet elapsed."""

    status_code = 429
    default_code = ErrorCode.VALIDATION_ERROR
    default_message = "Please wait before requesting a new code"

    def __init__(self, retry_after_seconds: int = 0, **kwargs: Any) -> None:
        super().__init__(
            details={"retry_after": retry_after_seconds},
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Account Restore Errors
# ---------------------------------------------------------------------------

class AccountRestorableException(AuthException):
    """
    Account was soft-deleted but is within the restore window.

    This is raised during registration to signal the frontend
    should show a restore prompt instead of creating a new account.
    """

    status_code = 409
    default_code = ErrorCode.RESOURCE_ALREADY_EXISTS
    default_message = "A previously deleted account exists for this email and can be restored"

    def __init__(self, restore_deadline: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(
            details={
                "has_restorable_account": True,
                "restore_deadline": restore_deadline,
            },
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Session Errors
# ---------------------------------------------------------------------------

class SessionNotFoundException(AuthException):
    """Session not found or does not belong to the user."""

    status_code = 404
    default_code = ErrorCode.RESOURCE_NOT_FOUND
    default_message = "Session not found"


# ---------------------------------------------------------------------------
# OAuth Errors
# ---------------------------------------------------------------------------

class OAuthException(AuthException):
    """Error during OAuth authentication flow."""

    status_code = 400
    default_code = ErrorCode.AUTH_UNAUTHORIZED
    default_message = "OAuth authentication failed"

    def __init__(
        self,
        provider: Optional[str] = None,
        reason: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        context: dict[str, Any] = {}
        if provider:
            context["provider"] = provider
        if reason:
            context["reason"] = reason
        super().__init__(context=context, **kwargs)


# ---------------------------------------------------------------------------
# Disposable Email Error
# ---------------------------------------------------------------------------

class DisposableEmailException(AuthException):
    """Registration attempted with a disposable/temporary email address."""

    status_code = 422
    default_code = ErrorCode.VALIDATION_ERROR
    default_message = "Please use a valid email address"

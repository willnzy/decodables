"""
Identity Domain Exceptions.

@module domains.identity.exceptions
@version 1.0.0
"""

from core.exceptions import DomainException


class IdentityException(DomainException):
    """Base exception for identity domain."""

    def __init__(self, message: str, code: str = "IDENTITY_ERROR"):
        super().__init__(message, code)


class UserNotFoundException(IdentityException):
    """Raised when a user is not found."""

    def __init__(self, user_id: str):
        super().__init__(
            message=f"User not found: {user_id}",
            code="USER_NOT_FOUND"
        )
        self.user_id = user_id
        self.status_code = 404


class UserAlreadyExistsException(IdentityException):
    """Raised when trying to create a user that already exists."""

    def __init__(self, user_id: str):
        super().__init__(
            message=f"User already exists: {user_id}",
            code="USER_ALREADY_EXISTS"
        )
        self.user_id = user_id
        self.status_code = 409


class InvalidUserDataException(IdentityException):
    """Raised when user data is invalid."""

    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"Invalid user data for field '{field}': {reason}",
            code="INVALID_USER_DATA"
        )
        self.field = field
        self.reason = reason
        self.status_code = 400


class TierUpgradeException(IdentityException):
    """Raised when tier upgrade fails."""

    def __init__(self, user_id: str, from_tier: str, to_tier: str, reason: str):
        super().__init__(
            message=f"Failed to upgrade user {user_id} from {from_tier} to {to_tier}: {reason}",
            code="TIER_UPGRADE_FAILED"
        )
        self.user_id = user_id
        self.from_tier = from_tier
        self.to_tier = to_tier
        self.reason = reason
        self.status_code = 400


class OnboardingException(IdentityException):
    """Raised when onboarding operation fails."""

    def __init__(self, user_id: str, step: str, reason: str):
        super().__init__(
            message=f"Onboarding failed for user {user_id} at step {step}: {reason}",
            code="ONBOARDING_FAILED"
        )
        self.user_id = user_id
        self.step = step
        self.reason = reason
        self.status_code = 400

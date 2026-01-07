"""
Identity Domain Exceptions.

@module domains.identity.exceptions
@version 1.0.0
"""

from core.exceptions import AppException, ErrorCode


class IdentityException(AppException):
    """Base exception for identity domain."""
    pass


class UserNotFoundException(IdentityException):
    """Raised when a user is not found."""
    status_code = 404
    default_code = ErrorCode.RESOURCE_NOT_FOUND
    default_message = "User not found"

    def __init__(self, user_id: str = None, **kwargs):
        message = "User not found"
        if user_id:
            message = f"User not found: {user_id}"

        super().__init__(
            message=message,
            context={"user_id": user_id},
            **kwargs
        )


class UserAlreadyExistsException(IdentityException):
    """Raised when trying to create a user that already exists."""
    status_code = 409
    default_code = ErrorCode.RESOURCE_ALREADY_EXISTS
    default_message = "User already exists"

    def __init__(self, user_id: str = None, **kwargs):
        message = "User already exists"
        if user_id:
            message = f"User already exists: {user_id}"

        super().__init__(
            message=message,
            context={"user_id": user_id},
            **kwargs
        )


class InvalidUserDataException(IdentityException):
    """Raised when user data is invalid."""
    status_code = 400
    default_code = ErrorCode.VALIDATION_ERROR
    default_message = "Invalid user data"

    def __init__(self, field: str = None, reason: str = None, **kwargs):
        message = "Invalid user data"
        if field and reason:
            message = f"Invalid user data for field '{field}': {reason}"

        super().__init__(
            message=message,
            context={"field": field, "reason": reason},
            **kwargs
        )


class TierUpgradeException(IdentityException):
    """Raised when tier upgrade fails."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Tier upgrade failed"

    def __init__(
        self,
        user_id: str = None,
        from_tier: str = None,
        to_tier: str = None,
        reason: str = None,
        **kwargs
    ):
        message = "Tier upgrade failed"
        if user_id and from_tier and to_tier:
            message = f"Failed to upgrade user {user_id} from {from_tier} to {to_tier}"
            if reason:
                message += f": {reason}"

        super().__init__(
            message=message,
            context={
                "user_id": user_id,
                "from_tier": from_tier,
                "to_tier": to_tier,
                "reason": reason,
            },
            **kwargs
        )


class OnboardingException(IdentityException):
    """Raised when onboarding operation fails."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Onboarding failed"

    def __init__(
        self,
        user_id: str = None,
        step: str = None,
        reason: str = None,
        **kwargs
    ):
        message = "Onboarding failed"
        if user_id and step:
            message = f"Onboarding failed for user {user_id} at step {step}"
            if reason:
                message += f": {reason}"

        super().__init__(
            message=message,
            context={"user_id": user_id, "step": step, "reason": reason},
            **kwargs
        )

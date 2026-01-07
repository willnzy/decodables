"""
Exceptions - Backward Compatibility Layer

This module re-exports all exceptions from the new core.exceptions
structure for backward compatibility.

@module exceptions
@version 3.26
@deprecated Use core.exceptions directly for new code
"""

# Re-export everything from core.exceptions for backward compatibility
from core.exceptions import *

# Import specific domain exceptions that were in old exceptions/
from domains.billing.exceptions import (
    InsufficientCreditsException,
    InvalidAmountException,
    CreditOperationFailedException,
)
from domains.creation.exceptions import (
    ProjectNotFoundException,
    AssetNotFoundException,
)
from domains.identity.exceptions import (
    UserNotFoundException,
    UserAlreadyExistsException,
)
from domains.marketplace.exceptions import (
    ListingNotFoundException,
    PurchaseFailedException,
)

# Make them available at module level
__all__ = [
    # Core exceptions
    'AppException',
    'ErrorCode',
    'ErrorResponse',
    'UnauthorizedException',
    'TokenExpiredException',
    'TokenInvalidException',
    'ForbiddenException',
    'NotFoundException',
    'ResourceAlreadyExistsException',
    'ResourceConflictException',
    'ValidationException',
    'FileTooLargeException',
    'InvalidFileTypeException',
    'RateLimitException',
    'InternalServerException',
    'InvalidOperationException',
    # Domain exceptions (for backward compatibility)
    'InsufficientCreditsException',
    'InvalidAmountException',
    'CreditOperationFailedException',
    'ProjectNotFoundException',
    'AssetNotFoundException',
    'UserNotFoundException',
    'UserAlreadyExistsException',
    'ListingNotFoundException',
    'PurchaseFailedException',
    # Marketplace-specific (backward compatibility)
    'InvalidTiersException',
    'CannotEditPendingException',
]

# Aliases for backward compatibility
AdminRequiredException = ForbiddenException  # Old name
MembershipRequiredException = ForbiddenException  # User needs paid membership

# Marketplace-specific exceptions (backward compatibility)
class InvalidTiersException(ValidationException):
    """Invalid tier configuration in marketplace listing."""
    def __init__(self):
        super().__init__(
            message="Invalid tier configuration",
            error_code=ErrorCode.VALIDATION_ERROR
        )

class CannotEditPendingException(InvalidOperationException):
    """Cannot edit listing in pending status."""
    def __init__(self):
        super().__init__(
            message="Cannot edit listing while in pending status",
            error_code=ErrorCode.INVALID_OPERATION
        )

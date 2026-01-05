"""
Exceptions Package - Unified error handling

@package exceptions
@version 3.24
"""

from .base import (
    ErrorCode,
    ErrorResponse,
    AppException,
)

from .auth import (
    UnauthorizedException,
    TokenExpiredException,
    TokenInvalidException,
    ForbiddenException,
    AdminRequiredException,
    MembershipRequiredException,
    TierRequiredException,
)

from .resource import (
    NotFoundException,
    ProjectNotFoundException,
    ListingNotFoundException,
    UserNotFoundException,
    ResourceAlreadyExistsException,
)

from .billing import (
    InsufficientCreditsException,
    PaymentFailedException,
    AlreadyPurchasedException,
)

from .ai import (
    AIGenerationException,
    AIProviderTimeoutException,
    AIProviderErrorException,
    ContentPolicyViolationException,
)

from .marketplace import (
    ListingNotApprovedException,
    ListingNotPublicException,
    CannotEditPendingException,
    SelfPurchaseException,
)

from .validation import (
    ValidationException,
    InvalidTiersException,
    PriceLimitException,
    FileTooLargeException,
    InvalidFileTypeException,
)

from .general import (
    RateLimitException,
    ExportFailedException,
    InternalServerException,
    InvalidOperationException,
)

__all__ = [
    # Base
    'ErrorCode', 'ErrorResponse', 'AppException',
    # Auth
    'UnauthorizedException', 'TokenExpiredException', 'TokenInvalidException',
    'ForbiddenException', 'AdminRequiredException', 'MembershipRequiredException',
    'TierRequiredException',
    # Resource
    'NotFoundException', 'ProjectNotFoundException', 'ListingNotFoundException',
    'UserNotFoundException', 'ResourceAlreadyExistsException',
    # Billing
    'InsufficientCreditsException', 'PaymentFailedException', 'AlreadyPurchasedException',
    # AI
    'AIGenerationException', 'AIProviderTimeoutException', 'AIProviderErrorException',
    'ContentPolicyViolationException',
    # Marketplace
    'ListingNotApprovedException', 'ListingNotPublicException',
    'CannotEditPendingException', 'SelfPurchaseException',
    # Validation
    'ValidationException', 'InvalidTiersException', 'PriceLimitException',
    'FileTooLargeException', 'InvalidFileTypeException',
    # General
    'RateLimitException', 'ExportFailedException', 'InternalServerException',
    'InvalidOperationException',
]

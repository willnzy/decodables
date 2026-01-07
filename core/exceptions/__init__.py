"""
Core Exceptions - Framework-level exception handling.

This module contains ONLY framework-level exceptions.
Business-specific exceptions should go to:
- domains/billing/exceptions.py (InsufficientCreditsException, etc.)
- domains/marketplace/exceptions.py (ListingNotApprovedException, etc.)
- shared/ai/exceptions.py (AIGenerationException, etc.)

@package core.exceptions
@version 1.0.0
"""

from .base import ErrorCode, ErrorResponse, AppException
from .auth import (
    UnauthorizedException,
    TokenExpiredException,
    TokenInvalidException,
    ForbiddenException,
)
from .resource import (
    NotFoundException,
    ResourceAlreadyExistsException,
    ResourceConflictException,
)
from .validation import (
    ValidationException,
    FileTooLargeException,
    InvalidFileTypeException,
)
from .general import (
    RateLimitException,
    InternalServerException,
    InvalidOperationException,
)

__all__ = [
    # Base
    'ErrorCode',
    'ErrorResponse',
    'AppException',
    # Auth (framework-level, no business logic)
    'UnauthorizedException',
    'TokenExpiredException',
    'TokenInvalidException',
    'ForbiddenException',
    # Resource (generic, business-specific go to domains/)
    'NotFoundException',
    'ResourceAlreadyExistsException',
    'ResourceConflictException',
    # Validation (generic)
    'ValidationException',
    'FileTooLargeException',
    'InvalidFileTypeException',
    # General
    'RateLimitException',
    'InternalServerException',
    'InvalidOperationException',
]

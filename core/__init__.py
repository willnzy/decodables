"""
Core Layer - Framework level code, 100% reusable across projects.

This layer contains:
- auth/: Authentication abstractions and providers
- cache/: Caching service abstractions
- database/: Database client and transaction management
- exceptions/: Unified exception handling (framework-level only)
- middleware/: HTTP middleware (logging, request_id, error_handler)
- utils/: Common utility functions

@package core
@version 1.0.0

Design Principles:
- NO business logic here
- All code should be reusable in any FastAPI project
- Business-specific exceptions go to domains/*/exceptions.py
"""

from .exceptions import (
    ErrorCode,
    ErrorResponse,
    AppException,
    # Auth exceptions
    UnauthorizedException,
    ForbiddenException,
    # Resource exceptions
    NotFoundException,
    ResourceAlreadyExistsException,
    # Validation exceptions
    ValidationException,
    # General exceptions
    RateLimitException,
    InternalServerException,
)

from .cache import (
    ICacheProvider,
    MemoryCacheProvider,
    RedisCacheProvider,
    CacheService,
    cache_service,
)

from .database import (
    get_db_client,
    is_db_available,
    DatabaseConfig,
    retry_on_network_error,
)

from .auth import (
    IAuthProvider,
    AuthResult,
    JWTConfig,
    decode_jwt,
    AuthContext,
    get_auth_context,
)

from .middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    setup_logging,
    get_request_id,
    add_cors_headers,
)

from .utils import (
    utc_now,
    format_iso,
    parse_iso,
    md5_hash,
    sha256_hash,
    generate_token,
    slugify,
    truncate,
    PaginationParams,
    PaginatedResponse,
)

__all__ = [
    # Base
    'ErrorCode',
    'ErrorResponse',
    'AppException',
    # Auth
    'UnauthorizedException',
    'ForbiddenException',
    # Resource
    'NotFoundException',
    'ResourceAlreadyExistsException',
    # Validation
    'ValidationException',
    # General
    'RateLimitException',
    'InternalServerException',
    # Cache
    'ICacheProvider',
    'MemoryCacheProvider',
    'RedisCacheProvider',
    'CacheService',
    'cache_service',
    # Database
    'get_db_client',
    'is_db_available',
    'DatabaseConfig',
    'retry_on_network_error',
    # Auth
    'IAuthProvider',
    'AuthResult',
    'JWTConfig',
    'decode_jwt',
    'AuthContext',
    'get_auth_context',
    # Middleware
    'RequestIDMiddleware',
    'RequestLoggingMiddleware',
    'setup_logging',
    'get_request_id',
    'add_cors_headers',
    # Utils
    'utc_now',
    'format_iso',
    'parse_iso',
    'md5_hash',
    'sha256_hash',
    'generate_token',
    'slugify',
    'truncate',
    'PaginationParams',
    'PaginatedResponse',
]

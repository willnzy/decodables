"""
Core Middleware Layer - Framework level HTTP middleware.

This module provides:
- RequestIDMiddleware: Request ID generation and tracking
- RequestLoggingMiddleware: Request/Response logging
- setup_logging: Structured logging configuration
- Context utilities: request_id, user_id context variables

@package core.middleware
@version 1.0.0

Design Principles:
- NO business logic here
- All code should be reusable in any FastAPI project
- Business-specific middleware goes to shared/ or app-level
"""

from .request_id import (
    RequestIDMiddleware,
    get_request_id,
    get_user_id,
    set_user_id,
)
from .logging import (
    RequestLoggingMiddleware,
    RequestContextFilter,
    setup_logging,
)
from .cors import add_cors_headers
from .file_upload import (
    validate_file_size,
    create_file_size_validator,
    MAX_UPLOAD_SIZE_MB,
    MAX_UPLOAD_SIZE_BYTES,
)

__all__ = [
    # Request ID
    'RequestIDMiddleware',
    'get_request_id',
    'get_user_id',
    'set_user_id',
    # Logging
    'RequestLoggingMiddleware',
    'RequestContextFilter',
    'setup_logging',
    # CORS
    'add_cors_headers',
    # File Upload (P3-005)
    'validate_file_size',
    'create_file_size_validator',
    'MAX_UPLOAD_SIZE_MB',
    'MAX_UPLOAD_SIZE_BYTES',
]

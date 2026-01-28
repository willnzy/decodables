"""
Core Database Layer - Framework level database abstractions.

This module provides:
- get_db_client: Get sync database client instance (legacy)
- get_async_db_client: Get async database client instance (NEW - recommended)
- retry_on_network_error: Decorator for automatic retry
- DatabaseConfig: Configuration dataclass
- run_sync: Run sync DB calls in thread pool (for legacy code)

@package core.database
@version 2.0.0

Design Principles:
- NO business logic here (no domain-specific queries)
- All code should be reusable in any FastAPI project
- Domain-specific database operations go to infrastructure/repositories/

Async Best Practice (v2.0):
- NEW: Use get_async_db_client() for native async/await operations
- LEGACY: Use get_db_client() + run_in_threadpool() for old code
- Migration in progress: Moving from sync to async client
- Reference: https://fastapi.tiangolo.com/async/
"""

from .client import (
    get_db_client,
    get_async_db_client,  # NEW: Async client for native async/await
    close_async_db_client,  # NEW: Cleanup function
    create_task_async_client,  # NEW: Non-singleton client for scheduled tasks
    is_db_available,
    DatabaseConfig,
    DatabaseClient,
)
from .retry import (
    retry_on_network_error,
    retry_on_network_error_async,
    is_retryable_error,
    RetryConfig,
)
from .async_utils import (
    run_sync,
    async_wrap,
    run_sync_safe,
)
from .dependencies import (
    get_async_db,  # FastAPI dependency for async client
    require_async_db,  # FastAPI dependency (required)
    get_db,  # Alias for backward compatibility
    require_db,  # Alias for backward compatibility
)

# Alias for compatibility with infrastructure layer
get_supabase_client = get_db_client
get_database_client = get_db_client

# Backward compatibility: Export singleton client instance
supabase = get_db_client()

__all__ = [
    # Client (Sync - Legacy)
    'get_db_client',
    'get_supabase_client',  # Alias
    'get_database_client',  # Alias for infrastructure layer
    'supabase',  # Singleton instance for backward compatibility
    # Client (Async - NEW, recommended)
    'get_async_db_client',
    'close_async_db_client',
    'create_task_async_client',  # Non-singleton for scheduled tasks
    # FastAPI Dependencies (NEW, recommended for route handlers)
    'get_async_db',
    'require_async_db',
    'get_db',  # Alias for backward compatibility
    'require_db',  # Alias for backward compatibility
    # Client utilities
    'is_db_available',
    'DatabaseConfig',
    'DatabaseClient',  # Type alias for type hints
    # Retry
    'retry_on_network_error',
    'retry_on_network_error_async',
    'is_retryable_error',
    'RetryConfig',
    # Async utilities (for legacy sync client)
    'run_sync',
    'async_wrap',
    'run_sync_safe',
]

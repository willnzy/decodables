"""
Core Database Layer - Framework level database abstractions.

This module provides:
- get_db_client: Get database client instance
- retry_on_network_error: Decorator for automatic retry
- DatabaseConfig: Configuration dataclass
- run_sync: Run sync DB calls in thread pool (FastAPI best practice)

@package core.database
@version 1.1.0

Design Principles:
- NO business logic here (no domain-specific queries)
- All code should be reusable in any FastAPI project
- Domain-specific database operations go to infrastructure/repositories/

Async Best Practice:
- Supabase Python SDK is synchronous
- Use run_sync() or run_in_threadpool() for DB calls in async handlers
- This prevents blocking the event loop
- Reference: https://fastapi.tiangolo.com/async/
"""

from .client import (
    get_db_client,
    is_db_available,
    DatabaseConfig,
    DatabaseClient,
)
from .retry import (
    retry_on_network_error,
    is_retryable_error,
    RetryConfig,
)
from .async_utils import (
    run_sync,
    async_wrap,
    run_sync_safe,
)

# Alias for compatibility with infrastructure layer
get_supabase_client = get_db_client
get_database_client = get_db_client

# Backward compatibility: Export singleton client instance
supabase = get_db_client()

__all__ = [
    # Client
    'get_db_client',
    'get_supabase_client',  # Alias
    'get_database_client',  # Alias for infrastructure layer
    'supabase',  # Singleton instance for backward compatibility
    'is_db_available',
    'DatabaseConfig',
    'DatabaseClient',  # Type alias for type hints
    # Retry
    'retry_on_network_error',
    'is_retryable_error',
    'RetryConfig',
    # Async utilities (FastAPI best practice)
    'run_sync',
    'async_wrap',
    'run_sync_safe',
]

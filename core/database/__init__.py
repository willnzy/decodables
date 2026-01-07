"""
Core Database Layer - Framework level database abstractions.

This module provides:
- get_db_client: Get database client instance
- retry_on_network_error: Decorator for automatic retry
- DatabaseConfig: Configuration dataclass

@package core.database
@version 1.0.0

Design Principles:
- NO business logic here (no domain-specific queries)
- All code should be reusable in any FastAPI project
- Domain-specific database operations go to infrastructure/repositories/
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

# Alias for compatibility with infrastructure layer
get_supabase_client = get_db_client

# Backward compatibility: Export singleton client instance
supabase = get_db_client()

__all__ = [
    # Client
    'get_db_client',
    'get_supabase_client',  # Alias
    'supabase',  # Singleton instance for backward compatibility
    'is_db_available',
    'DatabaseConfig',
    'DatabaseClient',  # Type alias for type hints
    # Retry
    'retry_on_network_error',
    'is_retryable_error',
    'RetryConfig',
]

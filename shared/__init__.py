"""
Shared Layer - Cross-cutting concerns and service abstractions.

This layer provides:
- Abstract interfaces for external services (AI, Payment, Storage)
- Standardized types and responses
- Provider-agnostic implementations
- Shared utilities (cache keys, etc.)

The shared layer sits between core/domains and infrastructure,
enabling dependency inversion and testability.

@module shared
@version 1.0.0
"""

# Re-export all shared modules for convenient importing
from . import ai
from . import payment
from . import storage
from . import cache_keys

__all__ = [
    "ai",
    "payment",
    "storage",
    "cache_keys",
]

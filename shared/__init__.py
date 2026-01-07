"""
Shared Layer - Cross-cutting concerns and service abstractions.

This layer provides:
- Abstract interfaces for external services (AI, Payment, Storage, Analytics)
- Standardized types and responses for service interactions
- Provider-agnostic implementations enabling dependency inversion

Note:
- This is the "service abstraction" layer in v2 architecture
- Business-specific cache keys have been moved to infrastructure/cache/
- For cache abstractions (ICacheProvider), see core/cache/

@module shared
@version 1.0.0
"""

# Re-export all shared modules for convenient importing
from . import ai
from . import payment
from . import storage

__all__ = [
    "ai",
    "payment",
    "storage",
]

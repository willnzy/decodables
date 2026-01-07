"""
Infrastructure Cache Module - Business-specific cache implementations.

This module provides:
- Business-specific cache key definitions (keys.py)
- Cache key namespaces for different domains (config, experiment, ai, rate_limit, stats)
- TTL configurations for different cache types

Note:
- For cache abstractions (ICacheProvider, Redis/Memory), see core/cache/
- This module contains business-specific cache key naming conventions

@package infrastructure.cache
@version 1.0.0
"""

from .keys import (
    # Constants
    PREFIX,
    # Namespaces
    CacheNamespace,
    # TTL Configuration
    CacheTTL,
    # Key Builder Functions
    config_key,
    config_all_key,
    experiment_key,
    ai_cache_key,
    rate_limit_key,
    stats_key,
)

__all__ = [
    # Constants
    "PREFIX",
    # Namespaces
    "CacheNamespace",
    # TTL Configuration
    "CacheTTL",
    # Key Builders
    "config_key",
    "config_all_key",
    "experiment_key",
    "ai_cache_key",
    "rate_limit_key",
    "stats_key",
]

"""
Cache Keys Module - Business-specific cache key definitions.

Naming Convention:
- All keys start with "md:" prefix (Make Decodables)
- Followed by namespace (config, experiment, ai, rl, stats)
- Then specific identifier

Examples:
- md:config:rate_limit.payment.checkout
- md:experiment:hero_button_test
- md:rl:ip:192.168.1.1

Note:
- This module is in infrastructure/ because it contains business-specific cache keys
- core/cache/ provides the caching abstraction (ICacheProvider, Redis/Memory implementations)
- infrastructure/cache/ defines business-specific cache key naming and TTL configurations

@module infrastructure.cache.keys
@version 1.0.0
"""

# Global prefix for all keys
PREFIX = "md:"


class CacheNamespace:
    """Cache key namespaces."""
    CONFIG = f"{PREFIX}config:"          # System configs
    EXPERIMENT = f"{PREFIX}experiment:"  # A/B experiments
    AI = f"{PREFIX}ai:"                  # AI response caching
    RATE_LIMIT = f"{PREFIX}rl:"          # Rate limiting
    STATS = f"{PREFIX}stats:"            # Aggregated statistics


class CacheTTL:
    """
    Default TTL values (in seconds).

    Note:
    - These are defaults, can be overridden per-call
    - 0 means no caching (useful for images)
    """
    CONFIG = 60          # 1 minute - configs can change frequently
    EXPERIMENT = 60      # 1 minute - experiments need quick updates
    AI_TEXT = 86400      # 24 hours - text results are stable
    AI_IMAGE = 0         # No caching - images are unique per request
    STATS = 300          # 5 minutes - aggregated stats
    RATE_LIMIT = 60      # 1 minute - rate limit windows


# ==========================================
# Key Builder Functions
# ==========================================

def config_key(key: str) -> str:
    """
    Build config cache key.

    Args:
        key: Config key (e.g., "rate_limit.payment.checkout")

    Returns:
        Full cache key (e.g., "md:config:rate_limit.payment.checkout")
    """
    return f"{CacheNamespace.CONFIG}{key}"


def config_all_key(group: str = None) -> str:
    """
    Build key for all configs cache.

    Args:
        group: Optional group filter

    Returns:
        Full cache key (e.g., "md:config:__all__" or "md:config:__all__:rate_limit")
    """
    if group:
        return f"{CacheNamespace.CONFIG}__all__:{group}"
    return f"{CacheNamespace.CONFIG}__all__"


def experiment_key(experiment_key_str: str) -> str:
    """
    Build experiment cache key.

    Args:
        experiment_key_str: Experiment key (e.g., "hero_button_test")

    Returns:
        Full cache key (e.g., "md:experiment:hero_button_test")
    """
    return f"{CacheNamespace.EXPERIMENT}{experiment_key_str}"


def ai_cache_key(prompt_hash: str, ai_type: str = "text") -> str:
    """
    Build AI result cache key.

    Args:
        prompt_hash: Hash of the prompt
        ai_type: Type of AI (text/image)

    Returns:
        Full cache key (e.g., "md:ai:text:abc123def")
    """
    return f"{CacheNamespace.AI}{ai_type}:{prompt_hash}"


def rate_limit_key(identifier: str, limit_type: str = "ip") -> str:
    """
    Build rate limit cache key.

    Args:
        identifier: IP address, user ID, or API key
        limit_type: Type of rate limit (ip/user/api)

    Returns:
        Full cache key (e.g., "md:rl:ip:192.168.1.1")
    """
    return f"{CacheNamespace.RATE_LIMIT}{limit_type}:{identifier}"


def stats_key(stat_type: str, period: str = "daily") -> str:
    """
    Build aggregated stats cache key.

    Args:
        stat_type: Type of stat (users/projects/revenue)
        period: Time period (hourly/daily/weekly/monthly)

    Returns:
        Full cache key (e.g., "md:stats:users:daily")
    """
    return f"{CacheNamespace.STATS}{stat_type}:{period}"

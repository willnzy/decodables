"""
Cache Keys Module
缓存键命名规范

Naming Convention:
- All keys start with "md:" prefix (Make Decodables)
- Followed by namespace (config, experiment, ai, rl, stats)
- Then specific identifier

Examples:
- md:config:rate_limit.payment.checkout
- md:experiment:hero_button_test
- md:rl:ip:192.168.1.1
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
        experiment_key_str: Experiment identifier
        
    Returns:
        Full cache key (e.g., "md:experiment:hero_button_test")
    """
    return f"{CacheNamespace.EXPERIMENT}{experiment_key_str}"


def experiment_list_key(status: str = None) -> str:
    """
    Build key for experiment list cache.
    
    Args:
        status: Optional status filter
        
    Returns:
        Full cache key
    """
    if status:
        return f"{CacheNamespace.EXPERIMENT}__list__:{status}"
    return f"{CacheNamespace.EXPERIMENT}__list__"


def ai_result_key(hash_key: str) -> str:
    """
    Build AI result cache key.
    
    Args:
        hash_key: Hash of prompt + model + params
        
    Returns:
        Full cache key
    """
    return f"{CacheNamespace.AI}{hash_key}"


def stats_key(stat_type: str, date: str = None) -> str:
    """
    Build stats cache key.
    
    Args:
        stat_type: Type of stats
        date: Optional date string
        
    Returns:
        Full cache key
    """
    if date:
        return f"{CacheNamespace.STATS}{stat_type}:{date}"
    return f"{CacheNamespace.STATS}{stat_type}"


def rate_limit_key(identifier: str, endpoint: str) -> str:
    """
    Build rate limit cache key.
    
    Args:
        identifier: User/IP identifier
        endpoint: Endpoint name
        
    Returns:
        Full cache key
    """
    return f"{CacheNamespace.RATE_LIMIT}{endpoint}:{identifier}"

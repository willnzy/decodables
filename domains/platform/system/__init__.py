"""
System Domain - Configuration and cache management.

@module domains.platform.system
@version 3.30

This domain handles:
- System configuration management (CRUD)
- Config group management
- Config audit logs
- Cache management (Redis)
- Cache invalidation
"""

from domains.platform.system.service import (
    # Config management (7)
    get_configs,
    get_config_groups,
    create_config,
    update_config,
    delete_config,
    get_config_audit,
    invalidate_config_cache,
    # Cache management (4)
    get_cache_status,
    list_cache_keys,
    delete_cache_key,
    clear_all_cache,
)

__all__ = [
    # Config management
    "get_configs",
    "get_config_groups",
    "create_config",
    "update_config",
    "delete_config",
    "get_config_audit",
    "invalidate_config_cache",
    # Cache management
    "get_cache_status",
    "list_cache_keys",
    "delete_cache_key",
    "clear_all_cache",
]

"""
Database Config - System configuration operations

@module services.db.config
@version 3.24
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from .core import supabase, retry_on_network_error

logger = logging.getLogger(__name__)

# Config cache
_config_cache = {}
_config_ttl = 300  # 5 minutes


def _get_cached_config(key: str) -> Optional[str]:
    """Get config from cache."""
    cached = _config_cache.get(key)
    if cached:
        value, timestamp = cached
        if (datetime.now(timezone.utc).timestamp() - timestamp) < _config_ttl:
            return value
    return None


def _set_cached_config(key: str, value):
    """Set config in cache."""
    _config_cache[key] = (value, datetime.now(timezone.utc).timestamp())


def _invalidate_config_cache(key: str = None):
    """Invalidate config cache."""
    if key:
        _config_cache.pop(key, None)
    else:
        _config_cache.clear()


@retry_on_network_error()
def get_system_config(key: str, default_value: str = None) -> Optional[str]:
    """Get system configuration value."""
    if not supabase:
        return default_value
    
    # Check cache
    cached = _get_cached_config(key)
    if cached is not None:
        return cached
    
    result = supabase.table("system_configs").select("value")\
        .eq("key", key).eq("is_active", True).execute()
    
    if result.data:
        value = result.data[0].get("value")
        _set_cached_config(key, value)
        return value
    
    return default_value


@retry_on_network_error()
def get_all_system_configs(group: str = None, include_inactive: bool = False):
    """Get all system configurations."""
    if not supabase:
        return []
    
    query = supabase.table("system_configs").select("*")
    
    if group:
        query = query.eq("config_group", group)
    if not include_inactive:
        query = query.eq("is_active", True)
    
    result = query.order("config_group").order("key").execute()
    return result.data or []


@retry_on_network_error()
def get_configs_by_group(group: str):
    """Get configs by group as dict."""
    if not supabase:
        return {}
    
    result = supabase.table("system_configs").select("key, value")\
        .eq("config_group", group).eq("is_active", True).execute()
    
    return {row["key"]: row["value"] for row in (result.data or [])}


# ==========================================
# Admin Config Operations
# ==========================================

@retry_on_network_error()
def admin_get_system_configs(group: str = None, page: int = 1, limit: int = 50):
    """Admin get system configs with pagination."""
    if not supabase:
        return {"items": [], "total": 0}
    
    offset = (page - 1) * limit
    query = supabase.table("system_configs").select("*", count="exact")
    
    if group:
        query = query.eq("config_group", group)
    
    result = query.order("config_group").order("key").range(offset, offset + limit - 1).execute()
    
    return {"items": result.data or [], "total": result.count or 0}


@retry_on_network_error()
def admin_get_config_groups():
    """Get distinct config groups."""
    if not supabase:
        return []
    
    result = supabase.table("system_configs").select("config_group").execute()
    groups = set(row.get("config_group") for row in (result.data or []) if row.get("config_group"))
    return sorted(list(groups))


@retry_on_network_error()
def admin_create_system_config(key: str, value: str, group: str, description: str = None,
                               value_type: str = "string", admin_id: str = None):
    """Create system config."""
    if not supabase:
        return None
    
    result = supabase.table("system_configs").insert({
        "key": key,
        "value": value,
        "config_group": group,
        "description": description,
        "value_type": value_type,
        "is_active": True,
        "created_by": admin_id,
    }).execute()
    
    _invalidate_config_cache(key)
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def admin_update_system_config(key: str, value: str = None, description: str = None,
                               is_active: bool = None, admin_id: str = None):
    """Update system config."""
    if not supabase:
        return None
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if value is not None:
        update_data["value"] = value
    if description is not None:
        update_data["description"] = description
    if is_active is not None:
        update_data["is_active"] = is_active
    if admin_id:
        update_data["updated_by"] = admin_id
    
    result = supabase.table("system_configs").update(update_data).eq("key", key).execute()
    
    _invalidate_config_cache(key)
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def admin_delete_system_config(key: str, admin_id: str = None):
    """Delete system config."""
    if not supabase:
        return None
    
    # Log before delete
    if admin_id:
        _log_config_audit(key, "delete", None, None, admin_id)
    
    result = supabase.table("system_configs").delete().eq("key", key).execute()
    
    _invalidate_config_cache(key)
    
    return {"success": True}


def _log_config_audit(key: str, action: str, old_value, new_value, admin_id: str):
    """Log config audit."""
    if not supabase:
        return
    
    try:
        supabase.table("config_audit_logs").insert({
            "config_key": key,
            "action": action,
            "old_value": str(old_value) if old_value else None,
            "new_value": str(new_value) if new_value else None,
            "admin_id": admin_id,
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to log config audit: {e}")


@retry_on_network_error()
def admin_get_config_audit_logs(config_key: str = None, page: int = 1, limit: int = 50):
    """Get config audit logs."""
    if not supabase:
        return []
    
    offset = (page - 1) * limit
    query = supabase.table("config_audit_logs").select("*")
    
    if config_key:
        query = query.eq("config_key", config_key)
    
    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return result.data or []


def invalidate_config_cache_api():
    """API endpoint to invalidate config cache."""
    _invalidate_config_cache()
    return {"success": True}


# ==========================================
# Backward-compatible aliases
# ==========================================

def get_public_configs():
    """
    Get all public system configurations.
    Alias for get_all_system_configs with default parameters.
    """
    return get_all_system_configs(group=None, include_inactive=False)


def get_config_by_key(key: str, default_value: str = None):
    """
    Get a single config by key.
    Alias for get_system_config.
    """
    return get_system_config(key, default_value)


def get_config_group(group: str):
    """
    Get all configs in a group.
    Alias for get_configs_by_group.
    """
    return get_configs_by_group(group)

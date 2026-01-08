"""
Config API - Public configuration endpoints (v2).

@module api.user.config
@version 2.1.0

Changes in v2.1.0:
- C-P0-1: Added whitelist for public configs (security fix)
- Non-whitelisted configs now return 403

Endpoints:
- GET /api/v2/user/config - Get all public configs
- GET /api/v2/user/config/{key} - Get single public config
- GET /api/v2/user/config/group/{group_name} - Get public config group
"""

import logging
import re
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from infrastructure.repositories import SupabaseConfigRepository
from core.database import get_database_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["user-config-v2"])


# ==========================================
# Public Config Whitelist (C-P0-1 fix)
# ==========================================

# Only these configs are accessible via public API
# All other configs require admin access
PUBLIC_CONFIG_WHITELIST = {
    # Feature flags (UI needs these)
    "FEATURE_AI_GENERATION",
    "FEATURE_MARKETPLACE",
    "FEATURE_OCR",
    "FEATURE_ZIP_EXPORT",
    "FEATURE_ASYNC_GENERATION",
    "FEATURE_STORY_GENERATION",
    # UI configuration
    "MAX_UPLOAD_FILE_SIZE_MB",
    "MAX_LISTING_PRICE",
    "MIN_LISTING_PRICE",
    "SUPPORTED_IMAGE_FORMATS",
    "SUPPORTED_EXPORT_FORMATS",
    # Public pricing info (not internal costs)
    "CREDITS_PER_IMAGE",
    "CREDITS_PER_SMART_SCAN",
    # Rate limit info (user-facing)
    "rate_limit.generation.limit",
    "rate_limit.generation.window",
}

# Pattern-based whitelist (for prefixes)
PUBLIC_CONFIG_PATTERNS = [
    r"^FEATURE_",  # All feature flags
    r"^UI_",       # All UI configs
]


def is_config_public(key: str) -> bool:
    """Check if a config key is accessible via public API."""
    # Check exact match
    if key in PUBLIC_CONFIG_WHITELIST:
        return True

    # Check patterns
    for pattern in PUBLIC_CONFIG_PATTERNS:
        if re.match(pattern, key):
            return True

    return False


# ==========================================
# Response Models
# ==========================================

class ConfigResponse(BaseModel):
    """Single config response."""
    key: str
    value: Any
    description: Optional[str] = None


class ConfigGroupResponse(BaseModel):
    """Config group response."""
    group: str
    configs: List[Dict[str, Any]]


# ==========================================
# Endpoints
# ==========================================

@router.get("")
async def list_configs() -> Dict[str, Any]:
    """
    Get all public configurations.

    Only returns configs in the public whitelist.
    Sensitive configs are not exposed.
    """
    db = get_database_client()
    config_repo = SupabaseConfigRepository(db)
    configs = await config_repo.get_all()

    # v2.1.0: Filter to only public configs
    public_configs = {
        c["key"]: c for c in configs
        if is_config_public(c.get("key", ""))
    }
    return public_configs


@router.get("/group/{group_name}")
async def get_group(group_name: str) -> ConfigGroupResponse:
    """
    Get all configurations in a group.

    Only returns configs in the public whitelist.
    """
    db = get_database_client()
    config_repo = SupabaseConfigRepository(db)
    configs = await config_repo.get_all(group=group_name)

    # v2.1.0: Filter to only public configs
    public_configs = [c for c in configs if is_config_public(c.get("key", ""))]
    return ConfigGroupResponse(group=group_name, configs=public_configs)


@router.get("/{key}")
async def get_config(key: str) -> Dict[str, Any]:
    """
    Get a single configuration by key.

    Returns 403 if config is not in public whitelist.
    """
    # v2.1.0: C-P0-1 fix - check whitelist first
    if not is_config_public(key):
        logger.warning(f"[Config] Blocked access to non-public config: {key}")
        raise HTTPException(403, "Access denied")

    db = get_database_client()
    config_repo = SupabaseConfigRepository(db)
    value = await config_repo.get_by_key(key)
    if not value:
        raise HTTPException(404, f"Config not found: {key}")
    return {"key": key, "value": value}

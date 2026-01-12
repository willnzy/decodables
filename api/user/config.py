"""
Config API - Public configuration endpoints (v2).

@module api.user.config
@version 2.2.0

Changes in v2.2.0:
- Added dependency injection for ConfigService (DDD compliance)
- API now calls Service → Repository (perfect DDD architecture)
- Removed direct Repository instantiation from endpoints

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

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from domains.platform.config_service import ConfigService
from infrastructure.repositories import SupabaseConfigRepository
from core.database.dependencies import get_async_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["user-config-v2"])


# ==========================================
# Dependency Injection
# ==========================================

async def get_config_service(db = Depends(get_async_db)) -> ConfigService:
    """
    Dependency injection factory for ConfigService (AsyncClient).

    Returns:
        ConfigService instance with Repository injected
    """
    config_repo = SupabaseConfigRepository(db)
    return ConfigService(config_repo)


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
    r"^FEATURE_",   # All feature flags
    r"^UI_",        # All UI configs
    r"^LANDING_",   # Landing page content (CMS-Lite)
    r"^SITE_",      # Site public info (name, contact, social)
    r"^PRICING_",   # Pricing display info (features, tiers)
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


class AllConfigsResponse(BaseModel):
    """Response for all public configs (P2-002)."""
    configs: Dict[str, Dict[str, Any]]

    class Config:
        # Allow arbitrary dict keys
        extra = "allow"


class SingleConfigResponse(BaseModel):
    """Response for single config (P2-002)."""
    key: str
    value: Any


# ==========================================
# Endpoints
# ==========================================

@router.get("")
async def list_configs(
    config_service: ConfigService = Depends(get_config_service),
) -> AllConfigsResponse:  # P2-002: Return Pydantic model instead of Dict[str, Any]
    """
    Get all public configurations.

    Only returns configs in the public whitelist.
    Sensitive configs are not exposed.
    """
    # v2.2.0: Use ConfigService (DDD compliance)
    configs = await config_service.get_all_configs()

    # v2.1.0: Filter to only public configs
    public_configs = {
        c["key"]: c for c in configs
        if is_config_public(c.get("key", ""))
    }

    # P2-002: Return Pydantic model instead of raw dict
    return AllConfigsResponse(configs=public_configs)


@router.get("/group/{group_name}")
async def get_group(
    group_name: str,
    config_service: ConfigService = Depends(get_config_service),
) -> ConfigGroupResponse:
    """
    Get all configurations in a group.

    Only returns configs in the public whitelist.
    """
    # v2.2.0: Use ConfigService (DDD compliance)
    configs = await config_service.get_all_configs(category=group_name)

    # v2.1.0: Filter to only public configs
    public_configs = [c for c in configs if is_config_public(c.get("key", ""))]
    return ConfigGroupResponse(group=group_name, configs=public_configs)


@router.get("/{key}")
async def get_config(
    key: str,
    config_service: ConfigService = Depends(get_config_service),
) -> SingleConfigResponse:  # P2-002: Return Pydantic model instead of Dict[str, Any]
    """
    Get a single configuration by key.

    Returns 403 if config is not in public whitelist.
    """
    # v2.1.0: C-P0-1 fix - check whitelist first
    if not is_config_public(key):
        logger.warning(f"[Config] Blocked access to non-public config: {key}")
        raise HTTPException(403, "Access denied")

    # v2.2.0: Use ConfigService (DDD compliance)
    # ConfigService.get_config() returns parsed value (dict or primitive)
    config = await config_service.get_config(key, use_cache=True)
    if not config:
        raise HTTPException(404, f"Config not found: {key}")

    # P2-002: Return Pydantic model instead of raw dict
    return SingleConfigResponse(key=key, value=config)

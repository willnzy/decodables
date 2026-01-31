"""
Config API - Public configuration endpoints (v2).

@module api.user.config
@version 2.4.0 (Container DI Migration)

Changes in v2.4.0:
- Container DI Migration
  - Migrated to Container-based dependency injection
  - Removed direct infrastructure.repositories imports
  - Removed get_async_db dependency from DI function
  - Architecture: API → Container → Service → Repository

Changes in v2.3.0:
- GET /group/{group_name} now returns nested JSON structure
- Example: tier.t1.display_name -> configs.t1.display_name
- No query parameter needed, this is the new default format

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
- GET /api/v2/user/config/group/{group_name} - Get public config group (nested JSON)
"""

import logging
import re
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, ConfigDict

from domains.platform.config_service import ConfigService
from infrastructure.rate_limiter import limiter
from container import get_container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["user-config-v2"])


# ==========================================
# Dependency Injection
# ==========================================

async def get_config_service() -> ConfigService:
    """
    Dependency injection factory for ConfigService via Container.

    WHY Container-based DI?
    - Centralized service instantiation
    - Testable (mock injection)
    - Follows DIP (Dependency Inversion Principle)
    """
    container = get_container()
    return await container.get_config_service()


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

# Pattern-based whitelist (for prefixes) — precompiled for performance
PUBLIC_CONFIG_PATTERNS = [
    re.compile(r"^FEATURE_"),   # All feature flags
    re.compile(r"^UI_"),        # All UI configs
    re.compile(r"^LANDING_"),   # Landing page content (CMS-Lite)
    re.compile(r"^SITE_"),      # Site public info (name, contact, social)
    re.compile(r"^PRICING_"),   # Pricing display info (features, tiers)
    re.compile(r"^tier\."),     # Tier configuration (monthly_credits, features, etc.)
    re.compile(r"^credits\."),  # Credit costs configuration
    re.compile(r"^CREDITS_"),   # Credit-related uppercase configs
    re.compile(r"^T[23]_"),     # T2/T3 plan configs (pricing, credits)
]

# Valid group names for the /group/{group_name} endpoint
VALID_CONFIG_GROUPS = {
    "tier", "credits", "feature", "feature_flag", "ui", "landing", "site", "pricing",
    "rate_limit", "FEATURE", "FEATURE_FLAG", "UI", "LANDING", "SITE", "PRICING", "CREDITS",
}


def is_config_public(key: str) -> bool:
    """Check if a config key is accessible via public API."""
    # Check exact match
    if key in PUBLIC_CONFIG_WHITELIST:
        return True

    # Check precompiled patterns
    for pattern in PUBLIC_CONFIG_PATTERNS:
        if pattern.match(key):
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
    """Config group response - nested JSON format.

    v2.3.0: Changed from flat array to nested object.
    Example: tier.t1.display_name -> configs.t1.display_name
    """
    group: str
    configs: Dict[str, Any]  # Nested structure instead of flat list


class AllConfigsResponse(BaseModel):
    """Response for all public configs (P2-002)."""
    model_config = ConfigDict(extra="allow")

    configs: Dict[str, Dict[str, Any]]


class SingleConfigResponse(BaseModel):
    """Response for single config (P2-002)."""
    key: str
    value: Any


# ==========================================
# Endpoints
# ==========================================

@router.get("")
@limiter.limit("200/minute")
async def list_configs(
    request: Request,
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
@limiter.limit("200/minute")
async def get_group(
    request: Request,
    group_name: str,
    config_service: ConfigService = Depends(get_config_service),
) -> ConfigGroupResponse:
    """
    Get all configurations in a group as nested JSON.

    v2.3.0: Returns nested structure instead of flat array.
    Example: tier.t1.display_name -> configs.t1.display_name

    Only returns configs in the public whitelist.
    """
    # Validate group_name against allowed set
    if group_name not in VALID_CONFIG_GROUPS:
        raise HTTPException(404, f"Config group not found: {group_name}")

    # v2.2.0: Use ConfigService (DDD compliance)
    configs = await config_service.get_all_configs(category=group_name)

    # v2.1.0: Filter to only public configs
    public_configs = [c for c in configs if is_config_public(c.get("key", ""))]

    # v2.3.0: Convert flat list to nested JSON structure
    # tier.t1.display_name -> { t1: { display_name: value } }
    nested_configs: Dict[str, Any] = {}
    for config in public_configs:
        key = config.get("key", "")
        value = config.get("value")

        # Remove group prefix (e.g., "tier." from "tier.t1.display_name")
        if key.startswith(f"{group_name}."):
            key = key[len(group_name) + 1:]

        # Split remaining key by dots and build nested structure
        parts = key.split(".")
        current = nested_configs
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the final value
        if parts:
            current[parts[-1]] = value

    return ConfigGroupResponse(group=group_name, configs=nested_configs)


@router.get("/{key}")
@limiter.limit("200/minute")
async def get_config(
    request: Request,
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

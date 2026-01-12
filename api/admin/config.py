"""
Admin Config Router - System configuration and rate limits for admins

@module api.admin.config
@version 3.26

Changes:
- v3.26: Complete DDD architecture refactor
  - CFG-CRITICAL-1: Migrated to Repository pattern
  - CFG-CRITICAL-2: Activated ConfigRepository
  - CFG-HIGH-1: Added Pydantic response models
  - CFG-HIGH-2: Added query limits in Repository
  - CFG-HIGH-3: Removed module-level Supabase, use dependency injection
  - CFG-HIGH-4: Unified error handling with try-except
  - CFG-MEDIUM-2: Full async/await support
  - CFG-MEDIUM-3: Enhanced audit logging
  - CFG-LOW-2: Adjusted rate limits (60→30/minute for queries)
- v3.25: Security improvements
  - Added rate limiting to all endpoints
  - Added config_key length validation
  - Added category parameter validation
  - Added preset validation using field_validator

Endpoints:
- GET /config - Get all configs
- GET /config/{config_key} - Get single config
- PUT /config - Update single config
- PUT /config/batch - Batch update configs
- GET /rate-limits - Get current rate limits
- POST /rate-limits/preset - Apply rate limit preset
- GET /rate-limits/presets - Get available presets
- POST /config/cache/clear - Clear config cache
"""

import json
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Depends, Query, Path
from pydantic import BaseModel, Field, field_validator

from domains.platform.config_service import RATE_LIMIT_PRESETS, ConfigService
from domains.platform.config_repository import ConfigRepository
from infrastructure.rate_limiter import limiter
from core.database import get_async_db_client
from dependencies import require_admin

# Import response models
from api.admin.config_models import (
    AllConfigsResponse, SingleConfigResponse, ConfigUpdateResponse,
    BatchConfigUpdateResponse, RateLimitsResponse, RateLimitPresetsResponse,
    RateLimitPresetApplyResponse, CacheClearResponse,
    ConfigEntry, RateLimitConfig, RateLimitPresetInfo
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["admin-config-v2"])


# ==========================================
# Constants
# ==========================================

VALID_CONFIG_CATEGORIES = {"rate_limit", "feature_flags", "system", "ai", "storage", "payment"}
VALID_RATE_LIMIT_PRESETS = set(RATE_LIMIT_PRESETS.keys())


# ==========================================
# Request Models
# ==========================================

class ConfigUpdateRequest(BaseModel):
    """Request model for updating a single config."""
    config_key: str = Field(..., min_length=1, max_length=200, description="Configuration key")
    config_value: dict = Field(..., description="Configuration value (JSON object)")


class BatchConfigUpdateRequest(BaseModel):
    """Request model for batch updating configs."""
    updates: List[dict] = Field(..., max_length=100, description="List of config updates")


class RateLimitPresetRequest(BaseModel):
    """Request model for applying rate limit preset."""
    preset: str = Field(..., description="Preset name")

    @field_validator("preset")
    @classmethod
    def validate_preset(cls, v: str) -> str:
        """Validate preset is a valid option."""
        if v not in VALID_RATE_LIMIT_PRESETS:
            raise ValueError(f"Invalid preset. Must be one of: {', '.join(VALID_RATE_LIMIT_PRESETS)}")
        return v


# ==========================================
# Helper Functions
# ==========================================

def _get_config_service() -> ConfigService:
    """Get ConfigService instance with injected repository."""
    from infrastructure.repositories.config_repository import SupabaseConfigRepository
    db = await get_async_db_client()
    config_repo = SupabaseConfigRepository(db)
    return ConfigService(config_repo)


# ==========================================
# Config Endpoints
# ==========================================

@router.get("/config", response_model=AllConfigsResponse)
@limiter.limit("30/minute")  # CFG-LOW-2: Reduced from 60 to 30
async def get_all_configs(
    request: Request,
    category: Optional[str] = Query(None, max_length=50, description="Filter by config category"),
    admin: dict = Depends(require_admin)
):
    """
    Get all system configurations with optional category filtering.

    Retrieves all configuration key-value pairs from the system_configs table.
    Used for viewing current system settings, feature flags, rate limits, and other
    configurable parameters. Supports filtering by category for focused queries.

    Args:
        category: Optional category filter (max 50 chars)
            Valid values:
                - "rate_limit": Rate limiting configurations
                - "feature_flags": Feature flag settings
                - "system": System-wide settings
                - "ai": AI service configurations
                - "storage": Storage settings
                - "payment": Payment gateway settings
            If not specified, returns all configurations across all categories

    Returns:
        AllConfigsResponse containing:
            - configs: List of configuration entries including:
                - key: Configuration key (e.g., "rate_limit.api.max_requests")
                - value: Configuration value (JSON object)
                - category: Configuration category
                - description: Human-readable description
                - is_active: Whether config is currently active
                - updated_at: Last update timestamp
            - total: Total number of configurations returned

    Raises:
        400: Invalid category value (not in VALID_CONFIG_CATEGORIES)
        401: Unauthorized (not admin)
        500: Database error

    Security:
        - Admin role required
        - Rate limit: 30 requests per minute
        - Category validated against VALID_CONFIG_CATEGORIES enum
        - Read-only operation (no data modification)

    Example:
        GET /api/v2/admin/config?category=rate_limit

        Response:
        {
            "configs": [
                {
                    "key": "rate_limit.api.max_requests",
                    "value": {"limit": 100, "window": "minute"},
                    "category": "rate_limit",
                    "description": "Maximum API requests per minute",
                    "is_active": true,
                    "updated_at": "2026-01-10T10:30:00Z"
                },
                {
                    "key": "rate_limit.global.enabled",
                    "value": {"enabled": true},
                    "category": "rate_limit",
                    "description": "Global rate limiting toggle",
                    "is_active": true,
                    "updated_at": "2026-01-09T15:20:00Z"
                }
            ],
            "total": 2
        }
    """
    try:
        # Validate category if provided
        if category and category not in VALID_CONFIG_CATEGORIES:
            raise HTTPException(
                400,
                f"Invalid category. Must be one of: {', '.join(VALID_CONFIG_CATEGORIES)}"
            )

        config_service = _get_config_service()
        logger.info(f"[Admin {admin.get('id')}] Queried all configs (category={category})")

        configs = await config_service.get_all_configs(category)

        return AllConfigsResponse(
            configs=[ConfigEntry(**config) for config in configs],
            total=len(configs)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] Get all configs failed: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(500, "Failed to retrieve configurations")


@router.get("/config/{config_key}", response_model=SingleConfigResponse)
@limiter.limit("30/minute")  # CFG-LOW-2
async def get_config(
    request: Request,
    config_key: str = Path(..., max_length=200, description="Configuration key"),
    admin: dict = Depends(require_admin)
):
    """
    Get a single system configuration by key.

    Retrieves a specific configuration value by its unique key. Useful for checking
    individual settings without loading all configurations. Returns 404 if the key
    doesn't exist in the system_configs table.

    Args:
        config_key: Configuration key to retrieve (max 200 chars)
            Examples:
                - "rate_limit.api.max_requests"
                - "feature_flags.new_editor.enabled"
                - "ai.fal.api_key"
                - "payment.stripe.webhook_secret"
            Key format: {category}.{subcategory}.{setting}

    Returns:
        SingleConfigResponse containing:
            - key: Configuration key (echoed back)
            - value: Configuration value (JSON object)
                Structure varies by config type, e.g.:
                - Rate limits: {"limit": 100, "window": "minute", "enabled": true}
                - Feature flags: {"enabled": true, "rollout_percentage": 50}
                - API keys: {"key": "sk_...", "environment": "production"}
            - is_active: Whether this config is currently active
            - updated_at: Last update timestamp (or null if not tracked)

    Raises:
        404: Configuration key not found
        401: Unauthorized (not admin)
        400: config_key exceeds 200 chars
        500: Database error

    Security:
        - Admin role required
        - Rate limit: 30 requests per minute
        - Key length validated (max 200 chars)
        - Read-only operation (no data modification)
        - Sensitive values (API keys, secrets) are returned unmasked
          (admin-only access assumed secure)

    Example:
        GET /api/v2/admin/config/rate_limit.api.max_requests

        Response:
        {
            "key": "rate_limit.api.max_requests",
            "value": {
                "limit": 100,
                "window": "minute",
                "enabled": true
            },
            "is_active": true,
            "updated_at": "2026-01-10T10:30:00Z"
        }
    """
    try:
        config_service = _get_config_service()
        logger.info(f"[Admin {admin.get('id')}] Queried config: {config_key}")

        config = await config_service.get_config(config_key)

        if config is None:
            raise HTTPException(404, f"Configuration '{config_key}' not found")

        return SingleConfigResponse(
            key=config_key,
            value=config,
            is_active=True,
            updated_at=None  # TODO: Add timestamp support
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] Get config failed: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(500, "Failed to retrieve configuration")


@router.put("/config", response_model=ConfigUpdateResponse)
@limiter.limit("10/minute")
async def update_config(
    request: Request,
    data: ConfigUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """Update a single system configuration."""
    try:
        config_service = _get_config_service()
        logger.info(f"[Admin {admin.get('id')}] Updating config: {data.config_key}")

        # Get old value for audit trail
        old_value = await config_service.get_config(data.config_key)

        success = await config_service.set_config(
            data.config_key,
            data.config_value,
            admin.get("id")
        )

        if not success:
            raise HTTPException(500, "Failed to update configuration")

        # ✅ Phase 3 - Task 9: Log configuration change to audit trail
        try:
            from core.database import get_async_db_client
            from infrastructure.repositories.admin_repository import SupabaseAdminUsersRepository

            admin_repo = SupabaseAdminUsersRepository(await get_async_db_client())
            await admin_repo.admin_log_operation(
                admin_id=admin["id"],
                operation_type="config_update",
                target_type="system_config",
                target_id=data.config_key,
                details=f"Config '{data.config_key}' updated",
                metadata={
                    "old_value": old_value,
                    "new_value": data.config_value,
                },
                source="api",
            )
        except Exception as e:
            logger.warning(f"Failed to log config update: {e}")

        logger.info(f"[Admin {admin.get('id')}] Config updated successfully: {data.config_key}")

        return ConfigUpdateResponse(
            success=True,
            message="Configuration updated successfully",
            config_key=data.config_key
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] Update config failed: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(500, "Failed to update configuration")


@router.put("/config/batch", response_model=BatchConfigUpdateResponse)
@limiter.limit("10/minute")
async def batch_update_configs_endpoint(
    request: Request,
    data: BatchConfigUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """Batch update multiple system configurations."""
    try:
        config_service = _get_config_service()
        logger.info(f"[Admin {admin.get('id')}] Batch updating {len(data.updates)} configs")

        results = await config_service.batch_update_configs(
            data.updates,
            admin.get("id")
        )

        updated_count = sum(1 for success in results.values() if success)
        failed_count = len(results) - updated_count

        # ✅ Phase 3 - Task 9: Log each successful config change to audit trail
        try:
            from core.database import get_async_db_client
            from infrastructure.repositories.admin_repository import SupabaseAdminUsersRepository

            admin_repo = SupabaseAdminUsersRepository(await get_async_db_client())

            for update in data.updates:
                config_key = update.get("config_key")
                if config_key and results.get(config_key):
                    # Only log successful updates
                    await admin_repo.admin_log_operation(
                        admin_id=admin["id"],
                        operation_type="config_update",
                        target_type="system_config",
                        target_id=config_key,
                        details=f"Batch config update",
                        metadata={
                            "batch_size": len(data.updates),
                            "new_value": update.get("config_value"),
                        },
                        source="api",
                    )
        except Exception as e:
            logger.warning(f"Failed to log batch config update: {e}")

        logger.info(
            f"[Admin {admin.get('id')}] Batch update completed: "
            f"{updated_count} succeeded, {failed_count} failed"
        )

        return BatchConfigUpdateResponse(
            success=failed_count == 0,
            results=results,
            updated_count=updated_count,
            failed_count=failed_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] Batch update failed: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(500, "Failed to batch update configurations")


# ==========================================
# Rate Limit Endpoints
# ==========================================

@router.get("/rate-limits", response_model=RateLimitsResponse)
@limiter.limit("30/minute")  # CFG-LOW-2
async def get_rate_limits(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Get current rate limit configurations."""
    try:
        config_service = _get_config_service()
        logger.info(f"[Admin {admin.get('id')}] Queried rate limits")

        configs = await config_service.get_all_configs("rate_limit")

        rate_limits = []
        global_enabled = True

        for config in configs:
            key = config["key"]
            if key == "rate_limit.global.enabled":
                try:
                    value_dict = json.loads(config["value"])
                    global_enabled = value_dict.get("enabled", True)
                except (json.JSONDecodeError, TypeError):
                    pass
            else:
                try:
                    value_dict = json.loads(config["value"])
                    if isinstance(value_dict, dict) and "limit" in value_dict:
                        rate_limits.append(RateLimitConfig(
                            key=key,
                            limit=value_dict.get("limit", 100),
                            window=value_dict.get("window", "minute"),
                            enabled=value_dict.get("enabled", True)
                        ))
                except (json.JSONDecodeError, TypeError):
                    pass

        return RateLimitsResponse(
            rate_limits=rate_limits,
            global_enabled=global_enabled,
            total=len(rate_limits)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] Get rate limits failed: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(500, "Failed to retrieve rate limits")


@router.post("/rate-limits/preset", response_model=RateLimitPresetApplyResponse)
@limiter.limit("10/minute")
async def apply_rate_limit_preset_endpoint(
    request: Request,
    data: RateLimitPresetRequest,
    admin: dict = Depends(require_admin)
):
    """Apply a rate limit preset (strict, normal, relaxed, disabled)."""
    try:
        config_service = _get_config_service()
        logger.info(f"[Admin {admin.get('id')}] Applying rate limit preset: {data.preset}")

        success = await config_service.apply_rate_limit_preset(
            data.preset,
            admin.get("id")
        )

        if not success:
            raise HTTPException(400, f"Invalid preset: {data.preset}")

        # ✅ Phase 3 - Task 9: Log rate limit preset change to audit trail
        try:
            from core.database import get_async_db_client
            from infrastructure.repositories.admin_repository import SupabaseAdminUsersRepository

            admin_repo = SupabaseAdminUsersRepository(await get_async_db_client())
            await admin_repo.admin_log_operation(
                admin_id=admin["id"],
                operation_type="rate_limit_preset_apply",
                target_type="rate_limit",
                details=f"Applied rate limit preset: {data.preset}",
                metadata={"preset": data.preset},
                source="api",
            )
        except Exception as e:
            logger.warning(f"Failed to log rate limit preset change: {e}")

        logger.info(f"[Admin {admin.get('id')}] Rate limit preset applied: {data.preset}")

        return RateLimitPresetApplyResponse(
            success=True,
            message=f"Rate limit preset '{data.preset}' applied successfully",
            preset=data.preset
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] Apply preset failed: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(500, "Failed to apply rate limit preset")


@router.get("/rate-limits/presets", response_model=RateLimitPresetsResponse)
@limiter.limit("30/minute")  # CFG-LOW-2
async def get_rate_limit_presets(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Get available rate limit presets."""
    try:
        logger.info(f"[Admin {admin.get('id')}] Queried rate limit presets")

        presets = [
            RateLimitPresetInfo(
                name=name,
                description=preset["description"],
                multiplier=preset.get("multiplier"),
                enabled=preset.get("enabled")
            )
            for name, preset in RATE_LIMIT_PRESETS.items()
        ]

        return RateLimitPresetsResponse(
            presets=presets,
            total=len(presets)
        )

    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] Get presets failed: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(500, "Failed to retrieve rate limit presets")


# ==========================================
# Cache Management Endpoints
# ==========================================

@router.post("/config/cache/clear", response_model=CacheClearResponse)
@limiter.limit("10/minute")
async def clear_cache(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Clear all configuration cache."""
    try:
        config_service = _get_config_service()
        logger.info(f"[Admin {admin.get('id')}] Clearing config cache")  # CFG-MEDIUM-3: Added audit

        config_service.clear_config_cache()

        # ✅ Phase 3 - Task 9: Log cache clear operation to audit trail
        try:
            from core.database import get_async_db_client
            from infrastructure.repositories.admin_repository import SupabaseAdminUsersRepository

            admin_repo = SupabaseAdminUsersRepository(await get_async_db_client())
            await admin_repo.admin_log_operation(
                admin_id=admin["id"],
                operation_type="cache_clear",
                target_type="system",
                details="Configuration cache cleared",
                source="api",
            )
        except Exception as e:
            logger.warning(f"Failed to log cache clear operation: {e}")

        logger.info(f"[Admin {admin.get('id')}] Config cache cleared successfully")

        return CacheClearResponse(
            success=True,
            message="Configuration cache cleared successfully"
        )

    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] Clear cache failed: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(500, "Failed to clear config cache")

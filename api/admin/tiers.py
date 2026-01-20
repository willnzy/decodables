"""
Admin Tiers Router - Tier configuration management for admins

@module api.admin.tiers
@version 1.0.0

Endpoints (prefix: /api/v2/admin/tiers):
- GET / - Get all tier configurations
- GET /{tier_code} - Get single tier configuration
- PUT /{tier_code} - Update tier configuration

This module provides admin endpoints for managing tier configurations including:
- Display names (configurable user-facing names)
- Monthly credits allocation
- Project limits
- AI queue priorities
- Feature permissions (pdf_export, vector_tools, etc.)
- Pricing information
"""

import logging
from typing import Optional, Dict, Any, List, Union

from fastapi import APIRouter, HTTPException, Request, Depends, Path
from pydantic import BaseModel, Field, field_validator

from domains.identity.tier_service import TierService, FeatureKey
from domains.identity.constants import VALID_TIERS, TIER_LABELS
from infrastructure.rate_limiter import limiter
from infrastructure.repositories.config_repository import SupabaseConfigRepository
from container import get_container
from dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tiers", tags=["admin-tiers-v2"])


# ==========================================
# Response Models
# ==========================================

class TierFeatures(BaseModel):
    """Tier feature permissions."""
    pdf_export: Union[bool, str] = True
    zip_export: Union[bool, str] = False
    basic_editor: Union[bool, str] = True
    vector_tools: Union[bool, str] = False
    freehand_tools: Union[bool, str] = False
    clipboard_paste: Union[bool, str] = False
    platform_assets: Union[bool, str] = True
    upload_image: Union[bool, str] = True
    upload_advanced: Union[bool, str] = False
    save_assets: Union[bool, str] = False
    history_assets: Union[bool, str] = False
    browse_marketplace: Union[bool, str] = True
    purchase_marketplace: Union[bool, str] = False
    publish_marketplace: Union[bool, str] = False
    ai_features: Union[bool, str] = True
    priority_support: Optional[Union[bool, str]] = None
    api_access: Optional[Union[bool, str]] = None


class TierConfigResponse(BaseModel):
    """Single tier configuration response."""
    tier_code: str
    display_name: str
    enabled: bool = True
    monthly_credits: int
    max_projects: int
    price_original: float = 0.0
    price_current: float = 0.0
    ai_queue_priority: str
    topup_discount: float
    features: Dict[str, Any]


class TierListResponse(BaseModel):
    """List of tier configurations response."""
    tiers: List[TierConfigResponse]


# ==========================================
# Request Models
# ==========================================

class TierUpdateRequest(BaseModel):
    """Request model for updating tier configuration."""
    display_name: Optional[str] = Field(None, max_length=100)
    enabled: Optional[bool] = None
    monthly_credits: Optional[int] = Field(None, ge=0)
    max_projects: Optional[int] = Field(None, ge=1)
    price_original: Optional[float] = Field(None, ge=0)
    price_current: Optional[float] = Field(None, ge=0)
    ai_queue_priority: Optional[str] = None
    topup_discount: Optional[float] = Field(None, ge=0, le=1)
    features: Optional[Dict[str, Any]] = None

    @field_validator("ai_queue_priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("low", "normal", "high"):
            raise ValueError("ai_queue_priority must be 'low', 'normal', or 'high'")
        return v


# ==========================================
# Dependency Injection
# ==========================================

async def get_tier_service() -> TierService:
    """
    Get TierService instance via Container.
    """
    from core.database import get_async_db_client

    db = await get_async_db_client()
    config_repo = SupabaseConfigRepository(db)
    return TierService(config_repo)


# ==========================================
# Price Config Keys
# ==========================================

TIER_PRICE_KEYS = {
    "t1": {"original": "tier.t1.price_original", "current": "tier.t1.price_current"},
    "t2": {"original": "tier.t2.price_original", "current": "tier.t2.price_current"},
    "t3": {"original": "tier.t3.price_original", "current": "tier.t3.price_current"},
    "t4": {"original": "tier.t4.price_original", "current": "tier.t4.price_current"},
}

# Default prices (aligned with CLAUDE.md Tier naming system)
DEFAULT_PRICES = {
    "t1": {"original": 0.0, "current": 0.0},
    "t2": {"original": 9.9, "current": 6.9},
    "t3": {"original": 15.9, "current": 9.9},
    "t4": {"original": 0.0, "current": 0.0},  # Enterprise - TBD
}


# ==========================================
# Endpoints
# ==========================================

@router.get("", response_model=TierListResponse)
@limiter.limit("30/minute")
async def get_all_tiers(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """
    Get all tier configurations.

    Returns all tier configurations including display names, monthly credits,
    project limits, AI queue priorities, and feature permissions.

    Returns:
        TierListResponse containing:
            - tiers: List of tier configurations

    Security:
        - Admin role required
        - Rate limit: 30 requests per minute
    """
    try:
        from core.database import get_async_db_client

        tier_service = await get_tier_service()
        db = await get_async_db_client()
        config_repo = SupabaseConfigRepository(db)

        logger.info(f"[Admin {admin.get('id')}] Queried all tier configurations")

        tiers = []
        for tier_code in sorted(VALID_TIERS):
            # Get display name
            display_name = await tier_service.get_tier_display_name(tier_code)

            # Get tier config (monthly_credits, max_projects, features, etc.)
            tier_config = await tier_service.get_tier_config(tier_code)

            # Get prices from config (with fallback to defaults)
            price_keys = TIER_PRICE_KEYS.get(tier_code, {})
            try:
                price_original_str = await config_repo.get_by_key(
                    price_keys.get("original", f"tier.{tier_code}.price_original"),
                    default_value=str(DEFAULT_PRICES.get(tier_code, {}).get("original", 0.0))
                )
                price_current_str = await config_repo.get_by_key(
                    price_keys.get("current", f"tier.{tier_code}.price_current"),
                    default_value=str(DEFAULT_PRICES.get(tier_code, {}).get("current", 0.0))
                )
                price_original = float(price_original_str)
                price_current = float(price_current_str)
            except (ValueError, TypeError):
                price_original = DEFAULT_PRICES.get(tier_code, {}).get("original", 0.0)
                price_current = DEFAULT_PRICES.get(tier_code, {}).get("current", 0.0)

            # Get enabled status (default True for all except t4)
            try:
                enabled_str = await config_repo.get_by_key(
                    f"tier.{tier_code}.enabled",
                    default_value="true" if tier_code != "t4" else "false"
                )
                enabled = enabled_str.lower() in ("true", "1", "yes")
            except Exception:
                enabled = tier_code != "t4"

            tiers.append(TierConfigResponse(
                tier_code=tier_code,
                display_name=display_name,
                enabled=enabled,
                monthly_credits=tier_config.get("monthly_credits", 0),
                max_projects=tier_config.get("max_projects", 1),
                price_original=price_original,
                price_current=price_current,
                ai_queue_priority=tier_config.get("ai_queue_priority", "low"),
                topup_discount=tier_config.get("topup_discount", 1.0),
                features=tier_config.get("features", {}),
            ))

        return TierListResponse(tiers=tiers)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] Get all tiers failed: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(500, "Failed to retrieve tier configurations")


@router.get("/{tier_code}", response_model=TierConfigResponse)
@limiter.limit("30/minute")
async def get_tier(
    request: Request,
    tier_code: str = Path(..., description="Tier code (t1, t2, t3, t4)"),
    admin: dict = Depends(require_admin)
):
    """
    Get a single tier configuration by tier code.

    Args:
        tier_code: Tier code (t1, t2, t3, t4)

    Returns:
        TierConfigResponse with full tier configuration

    Raises:
        400: Invalid tier code
        404: Tier configuration not found
    """
    try:
        if tier_code not in VALID_TIERS:
            raise HTTPException(400, f"Invalid tier code: {tier_code}. Must be one of: {', '.join(sorted(VALID_TIERS))}")

        from core.database import get_async_db_client

        tier_service = await get_tier_service()
        db = await get_async_db_client()
        config_repo = SupabaseConfigRepository(db)

        logger.info(f"[Admin {admin.get('id')}] Queried tier configuration: {tier_code}")

        # Get display name
        display_name = await tier_service.get_tier_display_name(tier_code)

        # Get tier config
        tier_config = await tier_service.get_tier_config(tier_code)

        # Get prices
        price_keys = TIER_PRICE_KEYS.get(tier_code, {})
        try:
            price_original_str = await config_repo.get_by_key(
                price_keys.get("original", f"tier.{tier_code}.price_original"),
                default_value=str(DEFAULT_PRICES.get(tier_code, {}).get("original", 0.0))
            )
            price_current_str = await config_repo.get_by_key(
                price_keys.get("current", f"tier.{tier_code}.price_current"),
                default_value=str(DEFAULT_PRICES.get(tier_code, {}).get("current", 0.0))
            )
            price_original = float(price_original_str)
            price_current = float(price_current_str)
        except (ValueError, TypeError):
            price_original = DEFAULT_PRICES.get(tier_code, {}).get("original", 0.0)
            price_current = DEFAULT_PRICES.get(tier_code, {}).get("current", 0.0)

        # Get enabled status
        try:
            enabled_str = await config_repo.get_by_key(
                f"tier.{tier_code}.enabled",
                default_value="true" if tier_code != "t4" else "false"
            )
            enabled = enabled_str.lower() in ("true", "1", "yes")
        except Exception:
            enabled = tier_code != "t4"

        return TierConfigResponse(
            tier_code=tier_code,
            display_name=display_name,
            enabled=enabled,
            monthly_credits=tier_config.get("monthly_credits", 0),
            max_projects=tier_config.get("max_projects", 1),
            price_original=price_original,
            price_current=price_current,
            ai_queue_priority=tier_config.get("ai_queue_priority", "low"),
            topup_discount=tier_config.get("topup_discount", 1.0),
            features=tier_config.get("features", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] Get tier failed: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(500, "Failed to retrieve tier configuration")


@router.put("/{tier_code}", response_model=TierConfigResponse)
@limiter.limit("10/minute")
async def update_tier(
    request: Request,
    tier_code: str = Path(..., description="Tier code (t1, t2, t3, t4)"),
    data: TierUpdateRequest = None,
    admin: dict = Depends(require_admin)
):
    """
    Update a tier configuration.

    Args:
        tier_code: Tier code (t1, t2, t3, t4)
        data: Update fields (only provided fields will be updated)

    Returns:
        Updated TierConfigResponse

    Raises:
        400: Invalid tier code or invalid update data
    """
    try:
        if tier_code not in VALID_TIERS:
            raise HTTPException(400, f"Invalid tier code: {tier_code}. Must be one of: {', '.join(sorted(VALID_TIERS))}")

        from core.database import get_async_db_client

        tier_service = await get_tier_service()
        db = await get_async_db_client()
        config_repo = SupabaseConfigRepository(db)
        container = get_container()

        logger.info(f"[Admin {admin.get('id')}] Updating tier configuration: {tier_code}")

        # Update display name if provided
        if data.display_name is not None:
            await tier_service.update_tier_display_name(tier_code, data.display_name)

        # Update enabled status if provided
        if data.enabled is not None:
            await config_repo.upsert(
                key=f"tier.{tier_code}.enabled",
                value=str(data.enabled).lower(),
                value_type="boolean",
                config_group="tier",
                description=f"{TIER_LABELS.get(tier_code, tier_code)} 启用状态",
                is_active=True,
                is_editable=True
            )

        # Update monthly_credits if provided
        if data.monthly_credits is not None:
            await config_repo.upsert(
                key=f"tier.{tier_code}.monthly_credits",
                value=str(data.monthly_credits),
                value_type="integer",
                config_group="tier",
                description=f"{TIER_LABELS.get(tier_code, tier_code)} 月度积分",
                is_active=True,
                is_editable=True
            )

        # Update max_projects if provided
        if data.max_projects is not None:
            await config_repo.upsert(
                key=f"tier.{tier_code}.max_projects",
                value=str(data.max_projects),
                value_type="integer",
                config_group="tier",
                description=f"{TIER_LABELS.get(tier_code, tier_code)} 最大项目数",
                is_active=True,
                is_editable=True
            )

        # Update prices if provided
        if data.price_original is not None:
            await config_repo.upsert(
                key=f"tier.{tier_code}.price_original",
                value=str(data.price_original),
                value_type="number",
                config_group="tier",
                description=f"{TIER_LABELS.get(tier_code, tier_code)} 原价",
                is_active=True,
                is_editable=True
            )

        if data.price_current is not None:
            await config_repo.upsert(
                key=f"tier.{tier_code}.price_current",
                value=str(data.price_current),
                value_type="number",
                config_group="tier",
                description=f"{TIER_LABELS.get(tier_code, tier_code)} 现价",
                is_active=True,
                is_editable=True
            )

        # Update ai_queue_priority if provided
        if data.ai_queue_priority is not None:
            await config_repo.upsert(
                key=f"tier.{tier_code}.ai_queue_priority",
                value=data.ai_queue_priority,
                value_type="text",
                config_group="tier",
                description=f"{TIER_LABELS.get(tier_code, tier_code)} AI 队列优先级",
                is_active=True,
                is_editable=True
            )

        # Update topup_discount if provided
        if data.topup_discount is not None:
            await config_repo.upsert(
                key=f"tier.{tier_code}.topup_discount",
                value=str(data.topup_discount),
                value_type="number",
                config_group="tier",
                description=f"{TIER_LABELS.get(tier_code, tier_code)} 充值折扣",
                is_active=True,
                is_editable=True
            )

        # Update features if provided
        if data.features is not None:
            import json
            await config_repo.upsert(
                key=f"tier.{tier_code}.features",
                value=json.dumps(data.features),
                value_type="json",
                config_group="tier",
                description=f"{TIER_LABELS.get(tier_code, tier_code)} 功能权限",
                is_active=True,
                is_editable=True
            )

        # Clear tier config cache to reflect changes
        tier_service.clear_cache()
        tier_service.clear_tier_config_cache()

        # Audit logging
        try:
            admin_audit = await container.get_admin_audit_service()
            await admin_audit.admin_log_operation(
                admin_id=admin["id"],
                operation_type="tier_update",
                target_type="tier_config",
                target_id=tier_code,
                details=f"Tier '{tier_code}' configuration updated",
                metadata=data.model_dump(exclude_none=True),
                source="api",
            )
        except Exception as e:
            logger.warning(f"Failed to log tier update: {e}")

        logger.info(f"[Admin {admin.get('id')}] Tier configuration updated: {tier_code}")

        # Return updated configuration
        return await get_tier(request, tier_code, admin)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] Update tier failed: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(500, "Failed to update tier configuration")

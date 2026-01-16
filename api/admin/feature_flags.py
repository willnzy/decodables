"""
Admin Feature Flags API

@module api.admin.feature_flags
@version 3.30 (Parking Lot Fix)

Admin端点用于管理Feature Flags:
- CRUD操作
- 开关控制
- 审计日志
- 测试评估

Changes in v3.30:
- Fixed parking lot item: get_client_flags now uses correct user dependency
- Changed from buggy Depends(get_async_db_client) to Depends(get_current_user_optional)
- Handle unauthenticated users with empty context

Changes in v3.29:
- Migrated to Container-based dependency injection
- Removed direct get_async_db_client() calls in DI
- Added get_feature_flag_service() using Container pattern
- Migrated audit logging to use Container's admin_audit_service
- Architecture: API → Container → Service → Repository

Changes in v1.2.0:
- 添加 allowed_tiers 参数支持 Tier 分层筛选
- 添加 Tier 验证逻辑
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.feature_flag import feature_service, EvaluationContext
from domains.feature_flags import FeatureFlagService, FeatureFlagRepository
from dependencies import require_admin, get_current_user_optional
from container import get_container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feature-flags", tags=["Admin - Feature Flags"])


# ==================== Request Models ====================

class CreateFlagRequest(BaseModel):
    """创建Flag请求"""
    key: str = Field(..., description="Flag唯一标识", min_length=3, max_length=100)
    name: str = Field(..., description="显示名称", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="描述", max_length=1000)
    flag_type: str = Field("boolean", description="Flag类型", pattern="^(boolean|multivariate|experiment)$")
    enabled: bool = Field(False, description="是否启用")
    environments: List[str] = Field(default_factory=lambda: ["production", "staging"])
    rollout_percentage: int = Field(0, ge=0, le=100, description="灰度百分比")
    variants: Optional[List[dict]] = None
    targeting_rules: Optional[List[dict]] = None
    tags: Optional[List[str]] = None
    owner: Optional[str] = None
    # v1.2: Tier 分层筛选
    allowed_tiers: Optional[List[str]] = Field(
        default=None,
        description="允许的 Tier 列表，空数组或 null 表示不限制"
    )


class UpdateFlagRequest(BaseModel):
    """更新Flag请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    enabled: Optional[bool] = None
    environments: Optional[List[str]] = None
    rollout_percentage: Optional[int] = Field(None, ge=0, le=100)
    variants: Optional[List[dict]] = None
    targeting_rules: Optional[List[dict]] = None
    whitelist_user_ids: Optional[List[str]] = None
    blacklist_user_ids: Optional[List[str]] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    tags: Optional[List[str]] = None
    owner: Optional[str] = None
    # v1.2: Tier 分层筛选
    allowed_tiers: Optional[List[str]] = Field(
        default=None,
        description="允许的 Tier 列表，空数组表示不限制"
    )


class TestEvaluationRequest(BaseModel):
    """测试评估请求"""
    flag_key: str
    user_id: Optional[str] = None
    tier: Optional[str] = None
    email: Optional[str] = None
    environment: str = "production"
    custom: Optional[dict] = None


# ==================== 验证函数 ====================

# v1.2: 有效的 Tier 代码
VALID_TIERS = {"t1", "t2", "t3", "t4"}


def validate_allowed_tiers(tiers: Optional[List[str]]) -> None:
    """
    验证 allowed_tiers 列表

    Args:
        tiers: Tier 列表

    Raises:
        HTTPException: 如果包含无效的 Tier 代码
    """
    if not tiers:
        return  # None 或空数组是有效的

    invalid = set(t.lower() for t in tiers) - VALID_TIERS
    if invalid:
        raise HTTPException(
            400,
            f"Invalid tiers: {list(invalid)}. Valid values: {sorted(VALID_TIERS)}"
        )


# ==================== 依赖注入 ====================

async def get_feature_flag_service() -> FeatureFlagService:
    """
    获取Feature Flag Service via Container.

    WHY Container-based DI?
    - Centralized service instantiation
    - Testable (mock injection)
    - Follows DIP (Dependency Inversion Principle)
    """
    container = get_container()
    return await container.get_feature_flag_service()


# ==================== 管理端点 ====================

@router.get("")
async def list_flags(
    flag_type: Optional[str] = Query(None, description="Filter by flag type: boolean, multivariate, or experiment"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    archived: bool = Query(False, description="Include archived flags"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated, e.g., 'beta,frontend')"),
    search: Optional[str] = Query(None, description="Search in flag key or name (case-insensitive)"),
    offset: int = Query(0, ge=0, description="Number of items to skip for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of items to return (1-100)"),
    admin = Depends(require_admin),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """
    List all feature flags with optional filtering and search.

    Supports pagination, filtering by type/status/tags, and full-text search.
    Returns paginated results with total count.

    Args:
        flag_type: Filter by flag type (valid values: "boolean", "multivariate", "experiment")
        enabled: Filter by enabled status (true/false, omit for all)
        archived: Include archived flags in results (default: false)
        tags: Filter by tags, comma-separated (e.g., "beta,frontend")
        search: Search keyword for flag key or name (case-insensitive)
        offset: Skip first N items (default: 0)
        limit: Return max N items (default: 20, max: 100)

    Returns:
        Dict containing:
            - data: List of flag objects with all properties
            - pagination: Object with offset, limit, and total count

    Raises:
        401: Unauthorized (not admin)
        400: Invalid flag_type value (must be boolean/multivariate/experiment)
        500: Database error

    Security:
        - Admin role required
        - No rate limit (internal tool)

    Example:
        GET /api/v2/admin/feature-flags?enabled=true&limit=50&search=beta
    """
    tag_list = tags.split(",") if tags else None

    flags, total_count = await service.list_flags(
        flag_type=flag_type,
        enabled=enabled,
        archived=archived,
        tags=tag_list,
        search=search,
        offset=offset,
        limit=limit
    )

    return {
        "data": [flag.dict() for flag in flags],
        "pagination": {
            "offset": offset,
            "limit": limit,
            "total": total_count
        }
    }


@router.post("")
async def create_flag(
    request: CreateFlagRequest,
    admin = Depends(require_admin),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """
    Create a new feature flag.

    Creates a feature flag with the specified configuration. Flag keys must be unique
    across all environments. Supports boolean flags, multivariate flags, and A/B experiments.

    Args:
        request: Feature flag configuration
            - key: Unique identifier (3-100 chars, alphanumeric + underscore/hyphen)
            - name: Display name (1-255 chars)
            - description: Optional detailed description (max 1000 chars)
            - flag_type: Type of flag ("boolean", "multivariate", or "experiment")
            - enabled: Initial enabled state (default: false)
            - environments: Target environments (default: ["production", "staging"])
            - rollout_percentage: Gradual rollout percentage 0-100 (default: 0)
            - variants: Optional variants for multivariate flags
            - targeting_rules: Optional targeting rules (user/tier-based)
            - tags: Optional tags for categorization
            - owner: Optional owner identifier

    Returns:
        Dict containing:
            - success: true
            - data: Created flag object with all properties including:
                - id: Flag UUID
                - key: Flag identifier
                - created_at: Creation timestamp
                - created_by: Admin user_id

    Raises:
        400: Invalid request (key already exists, invalid flag_type, invalid percentage)
        401: Unauthorized (not admin)
        500: Database error

    Security:
        - Admin role required
        - Flag key uniqueness enforced at database level
        - No rate limit (internal tool)

    Example:
        POST /api/v2/admin/feature-flags
        {
            "key": "new_editor_ui",
            "name": "New Editor UI",
            "description": "Enable redesigned editor interface",
            "flag_type": "boolean",
            "enabled": false,
            "rollout_percentage": 10,
            "tags": ["frontend", "beta"]
        }
    """
    # v1.2: 验证 allowed_tiers
    validate_allowed_tiers(request.allowed_tiers)

    flag = await service.create_flag(
        key=request.key,
        name=request.name,
        admin_id=admin["user_id"],
        description=request.description,
        flag_type=request.flag_type,
        enabled=request.enabled,
        environments=request.environments,
        rollout_percentage=request.rollout_percentage,
        variants=request.variants,
        targeting_rules=request.targeting_rules,
        tags=request.tags,
        owner=request.owner,
        allowed_tiers=request.allowed_tiers or []  # v1.2: Tier 分层筛选
    )

    if not flag:
        raise HTTPException(400, "Failed to create flag (key may already exist)")

    return {
        "success": True,
        "data": flag.dict()
    }


@router.get("/{key}")
async def get_flag(
    key: str,
    admin = Depends(require_admin),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """
    Get detailed information about a specific feature flag.

    Retrieves complete flag configuration including targeting rules, variants,
    rollout status, and metadata.

    Args:
        key: Feature flag unique identifier

    Returns:
        Dict containing:
            - data: Complete flag object including:
                - id, key, name, description
                - flag_type, enabled, environments
                - rollout_percentage, variants, targeting_rules
                - created_at, updated_at, created_by
                - tags, owner

    Raises:
        404: Flag not found with the specified key
        401: Unauthorized (not admin)
        500: Database error

    Security:
        - Admin role required
        - No rate limit (internal tool)

    Example:
        GET /api/v2/admin/feature-flags/new_editor_ui
    """
    flag = await service.get_flag(key)
    if not flag:
        raise HTTPException(404, f"Flag not found: {key}")

    return {
        "data": flag.dict()
    }


@router.patch("/{key}")
async def update_flag(
    key: str,
    request: UpdateFlagRequest,
    admin = Depends(require_admin),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """
    Update an existing feature flag configuration.

    Performs partial update - only provided fields are modified. All fields are optional.
    Supports updating flag properties, targeting rules, rollout percentage, and metadata.

    Args:
        key: Feature flag unique identifier to update
        request: Update payload (all fields optional):
            - name: Display name (1-255 chars)
            - description: Detailed description (max 1000 chars)
            - enabled: Enable/disable flag
            - environments: Target environments list
            - rollout_percentage: Gradual rollout percentage (0-100)
            - variants: Variants for multivariate flags
            - targeting_rules: Targeting rules (user/tier-based)
            - whitelist_user_ids: User IDs to always enable flag
            - blacklist_user_ids: User IDs to always disable flag
            - start_at: Optional start time (ISO 8601)
            - end_at: Optional end time (ISO 8601)
            - tags: Tags for categorization
            - owner: Owner identifier

    Returns:
        Dict containing:
            - success: true
            - data: Updated flag object with all current properties

    Raises:
        400: No fields to update (empty request body)
        404: Flag not found with the specified key
        401: Unauthorized (not admin)
        500: Database error

    Security:
        - Admin role required
        - Update is atomic (all-or-nothing)
        - Audit log created for changes
        - No rate limit (internal tool)

    Example:
        PATCH /api/v2/admin/feature-flags/new_editor_ui
        {
            "enabled": true,
            "rollout_percentage": 50,
            "tags": ["frontend", "stable"]
        }
    """
    # v1.2: 验证 allowed_tiers (如果提供)
    if request.allowed_tiers is not None:
        validate_allowed_tiers(request.allowed_tiers)

    # 只传递非None的字段
    updates = {k: v for k, v in request.dict().items() if v is not None}

    if not updates:
        raise HTTPException(400, "No fields to update")

    flag = await service.update_flag(
        key=key,
        admin_id=admin["user_id"],
        **updates
    )

    if not flag:
        raise HTTPException(404, f"Flag not found: {key}")

    return {
        "success": True,
        "data": flag.dict()
    }


@router.post("/{key}/toggle")
async def toggle_flag(
    key: str,
    enabled: bool = Query(..., description="Target enabled state (true to enable, false to disable)"),
    admin = Depends(require_admin),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """
    Toggle feature flag enabled state.

    Quick endpoint to enable or disable a flag without full update payload.
    Creates audit log entry for the state change.

    Args:
        key: Feature flag unique identifier to toggle
        enabled: Target enabled state (true to enable, false to disable)

    Returns:
        Dict containing:
            - success: true
            - data: Updated flag object with new enabled state

    Raises:
        404: Flag not found with the specified key
        401: Unauthorized (not admin)
        500: Database error

    Security:
        - Admin role required
        - State change is atomic
        - Audit log created
        - No rate limit (internal tool)

    Example:
        POST /api/v2/admin/feature-flags/new_editor_ui/toggle?enabled=true
    """
    flag = await service.toggle_flag(key, enabled, admin["user_id"])

    if not flag:
        raise HTTPException(404, f"Flag not found: {key}")

    return {
        "success": True,
        "data": flag.dict()
    }


@router.delete("/{key}")
async def archive_flag(
    key: str,
    admin = Depends(require_admin),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """
    Archive a feature flag (soft delete).

    Marks the flag as archived without permanently deleting it. Archived flags
    are excluded from default listing and evaluation. Can be restored later if needed.

    Args:
        key: Feature flag unique identifier to archive

    Returns:
        Dict containing:
            - success: true
            - message: Confirmation message

    Raises:
        404: Flag not found with the specified key
        401: Unauthorized (not admin)
        409: Flag is currently in use in active experiments (cannot archive)
        500: Database error

    Security:
        - Admin role required
        - Soft delete (can be restored)
        - Audit log created
        - No rate limit (internal tool)

    Example:
        DELETE /api/v2/admin/feature-flags/deprecated_feature
    """
    success = await service.archive_flag(key, admin["user_id"])

    # ✅ v3.29: Audit logging via Container
    if success:
        try:
            container = get_container()
            admin_audit = await container.get_admin_audit_service()
            await admin_audit.admin_log_operation(
                admin_id=admin["user_id"],
                operation_type="feature_flag_delete",
                target_type="feature_flag",
                target_id=key,
                details=f"Feature flag '{key}' archived",
                source="api",
            )
        except Exception as e:
            logger.warning(f"Failed to log feature flag deletion: {e}")

    if not success:
        raise HTTPException(404, f"Flag not found: {key}")

    return {
        "success": True,
        "message": f"Flag '{key}' archived successfully"
    }


@router.post("/test-evaluation")
async def test_evaluation(
    request: TestEvaluationRequest,
    admin = Depends(require_admin)
):
    """
    Test feature flag evaluation with custom context.

    Simulates flag evaluation for given user context without affecting actual
    usage statistics. Useful for testing targeting rules and rollout logic.

    Args:
        request: Evaluation test request
            - flag_key: Flag identifier to test
            - user_id: Optional user ID for context
            - tier: Optional user tier (t1/t2/t3)
            - email: Optional user email
            - environment: Target environment (default: "production")
            - custom: Optional custom attributes dict

    Returns:
        Dict containing:
            - flag_key: Tested flag identifier
            - context: Evaluation context used
            - result: Evaluation result including:
                - enabled: Whether flag is enabled for this context
                - variant: Variant key (for multivariate flags)
                - reason: Evaluation reason (targeting_rule/rollout/default)

    Raises:
        404: Flag not found
        401: Unauthorized (not admin)
        400: Invalid environment or context
        500: Evaluation error

    Security:
        - Admin role required
        - Test mode (doesn't affect statistics)
        - No rate limit (internal tool)

    Example:
        POST /api/v2/admin/feature-flags/test-evaluation
        {
            "flag_key": "new_editor_ui",
            "user_id": "user_123",
            "tier": "t3",
            "environment": "production"
        }
    """
    context = EvaluationContext(
        user_id=request.user_id,
        tier=request.tier,
        email=request.email,
        environment=request.environment,
        custom=request.custom or {},
    )

    result = feature_service.evaluate(request.flag_key, context)

    return {
        "flag_key": request.flag_key,
        "context": context.to_dict(),
        "result": result.to_dict(),
    }


@router.get("/{key}/audit")
async def get_audit_logs(
    key: str,
    offset: int = Query(0, ge=0, description="Number of items to skip for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of items to return (1-100)"),
    admin = Depends(require_admin),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """
    Get audit log for a feature flag.

    Returns chronological history of all changes made to the flag, including
    creation, updates, toggles, and archival. Useful for compliance and debugging.

    Args:
        key: Feature flag unique identifier
        offset: Skip first N log entries (default: 0)
        limit: Return max N log entries (default: 20, max: 100)

    Returns:
        Dict containing:
            - data: List of audit log entries including:
                - timestamp: When change occurred
                - action: Type of change (created/updated/toggled/archived)
                - admin_id: Who made the change
                - changes: What was changed (before/after values)
                - metadata: Additional context
            - pagination: Object with offset, limit, and total count

    Raises:
        404: Flag not found (returns empty list, not error)
        401: Unauthorized (not admin)
        500: Database error

    Security:
        - Admin role required
        - Audit logs are immutable
        - No rate limit (internal tool)

    Example:
        GET /api/v2/admin/feature-flags/new_editor_ui/audit?limit=50
    """
    logs, total_count = await service.get_audit_logs(key, offset, limit)

    return {
        "data": logs,
        "pagination": {
            "offset": offset,
            "limit": limit,
            "total": total_count
        }
    }


# ==================== 客户端端点 (无需Admin权限) ====================

@router.get("/client/flags")
async def get_client_flags(
    user: dict = Depends(get_current_user_optional)
):
    """
    Get all feature flag states for the current user (client-side evaluation).

    v3.30: Fixed wrong dependency injection (was using get_async_db_client).

    Returns all active flags and their evaluation results based on user context.
    This endpoint is for client-side flag evaluation and doesn't require admin privileges.
    Unauthenticated users will receive flags evaluated with empty context.

    Note: In production, prefer server-side evaluation to avoid exposing
    targeting rules and rollout percentages.

    Args:
        user: Authenticated user (optional, from token)

    Returns:
        Dict containing:
            - flags: Object mapping flag keys to boolean states
            - variants: Object mapping flag keys to variant strings

    Raises:
        500: Evaluation error

    Security:
        - User authentication optional
        - Returns only evaluated results (not full config)
        - No rate limit currently (consider adding in production)

    Example:
        GET /api/v2/admin/feature-flags/client/flags
        Response:
        {
            "flags": {
                "new_editor_ui": true,
                "ai_assistant": false
            },
            "variants": {
                "ab_test_homepage": "variant_b"
            }
        }
    """
    # v3.30: Handle unauthenticated users
    context = EvaluationContext(
        user_id=user.get("id") if user else None,
        tier=user.get("tier") if user else None,
        email=user.get("email") if user else None,
    )

    flags = feature_service.get_all_flags(context)
    variants = feature_service.get_all_variants(context)

    return {
        "flags": flags,
        "variants": variants,
    }

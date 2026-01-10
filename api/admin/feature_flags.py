"""
Admin Feature Flags API

@module api.admin.feature_flags
@version 1.0.0

Admin端点用于管理Feature Flags:
- CRUD操作
- 开关控制
- 审计日志
- 测试评估
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.feature_flag import feature_service, EvaluationContext
from domains.feature_flags import FeatureFlagService, FeatureFlagRepository
from dependencies import require_admin
from core.database import get_supabase_client

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


class TestEvaluationRequest(BaseModel):
    """测试评估请求"""
    flag_key: str
    user_id: Optional[str] = None
    tier: Optional[str] = None
    email: Optional[str] = None
    environment: str = "production"
    custom: Optional[dict] = None


# ==================== 依赖注入 ====================

def get_feature_flag_service(
    supabase = Depends(get_supabase_client)
) -> FeatureFlagService:
    """获取Feature Flag Service"""
    repository = FeatureFlagRepository(supabase)
    return FeatureFlagService(repository)


# ==================== 管理端点 ====================

@router.get("")
async def list_flags(
    flag_type: Optional[str] = Query(None, description="过滤Flag类型"),
    enabled: Optional[bool] = Query(None, description="过滤启用状态"),
    archived: bool = Query(False, description="是否显示归档"),
    tags: Optional[str] = Query(None, description="标签过滤 (逗号分隔)"),
    search: Optional[str] = Query(None, description="搜索key或name"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    admin = Depends(require_admin),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """
    获取Flag列表

    支持过滤、搜索和分页
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
    """创建Flag"""
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
        owner=request.owner
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
    """获取单个Flag详情"""
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
    """更新Flag"""
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
    enabled: bool = Query(..., description="目标状态"),
    admin = Depends(require_admin),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """开关Flag"""
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
    """归档Flag (软删除)"""
    success = await service.archive_flag(key, admin["user_id"])

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
    """测试Flag评估"""
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
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    admin = Depends(require_admin),
    service: FeatureFlagService = Depends(get_feature_flag_service)
):
    """获取Flag审计日志"""
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
    user: dict = Depends(get_supabase_client)
):
    """
    获取当前用户的所有Flag状态

    (实际使用时应该通过Feature Flag Service获取)
    """
    context = EvaluationContext(
        user_id=user.get("id"),
        tier=user.get("tier"),
        email=user.get("email"),
    )

    flags = feature_service.get_all_flags(context)
    variants = feature_service.get_all_variants(context)

    return {
        "flags": flags,
        "variants": variants,
    }

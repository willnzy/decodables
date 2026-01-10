"""
Onboarding API

@module api.user.onboarding
@version 1.0.0

用户引导API endpoints:
- 获取可用引导
- 开始/完成/跳过引导
- 获取任务清单进度
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from domains.onboarding import OnboardingService, OnboardingRepository
from dependencies import get_current_user, get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["User - Onboarding"])


# ==================== Request Models ====================

class StepActionRequest(BaseModel):
    """步骤操作请求"""
    step_key: str = Field(..., description="步骤key", min_length=1, max_length=100)


# ==================== 依赖注入 ====================

def get_onboarding_service(
    supabase = Depends(get_supabase_client)
) -> OnboardingService:
    """获取Onboarding Service"""
    repository = OnboardingRepository(supabase)
    return OnboardingService(repository)


# ==================== API Endpoints ====================

@router.get("/steps")
async def get_available_steps(
    user: dict = Depends(get_current_user),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """
    获取用户可用的引导步骤列表

    返回所有符合用户层级的引导步骤及其进度
    """
    user_tier = user.get("tier", "free")

    steps = await service.get_available_steps(
        user_id=user["id"],
        user_tier=user_tier
    )

    return {
        "data": steps,
        "total": len(steps)
    }


@router.post("/steps/start")
async def start_step(
    request: StepActionRequest,
    user: dict = Depends(get_current_user),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """
    开始一个引导步骤

    创建进度记录,标记为pending状态
    """
    progress = await service.start_step(
        user_id=user["id"],
        step_key=request.step_key
    )

    if not progress:
        raise HTTPException(404, f"Step not found: {request.step_key}")

    return {
        "success": True,
        "data": progress.dict()
    }


@router.post("/steps/complete")
async def complete_step(
    request: StepActionRequest,
    user: dict = Depends(get_current_user),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """
    完成一个引导步骤

    更新进度为completed,记录完成时间
    """
    progress = await service.complete_step(
        user_id=user["id"],
        step_key=request.step_key
    )

    if not progress:
        raise HTTPException(404, f"Step not found: {request.step_key}")

    logger.info(f"User {user['id'][:8]}... completed step: {request.step_key}")

    return {
        "success": True,
        "data": progress.dict(),
        "message": f"Step '{request.step_key}' completed"
    }


@router.post("/steps/skip")
async def skip_step(
    request: StepActionRequest,
    user: dict = Depends(get_current_user),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """
    跳过一个引导步骤

    更新进度为skipped,记录跳过时间
    """
    progress = await service.skip_step(
        user_id=user["id"],
        step_key=request.step_key
    )

    if not progress:
        raise HTTPException(404, f"Step not found: {request.step_key}")

    logger.info(f"User {user['id'][:8]}... skipped step: {request.step_key}")

    return {
        "success": True,
        "data": progress.dict(),
        "message": f"Step '{request.step_key}' skipped"
    }


@router.get("/checklist")
async def get_checklist_progress(
    user: dict = Depends(get_current_user),
    service: OnboardingService = Depends(get_onboarding_service)
):
    """
    获取任务清单进度

    返回:
    - 总任务数
    - 已完成数
    - 完成百分比
    - 各步骤详情
    """
    user_tier = user.get("tier", "free")

    checklist = await service.get_checklist_progress(
        user_id=user["id"],
        user_tier=user_tier
    )

    return {
        "data": checklist
    }


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "onboarding"
    }

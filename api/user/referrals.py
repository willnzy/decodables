"""
Referrals API

@module api.user.referrals
@version 1.0.0

推荐系统API endpoints:
- 创建推荐
- 查看推荐列表
- 获取推荐统计
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from domains.referrals import ReferralService, ReferralRepository
from dependencies import get_current_user, get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/referrals", tags=["User - Referrals"])


# ==================== Request Models ====================

class CreateReferralRequest(BaseModel):
    """创建推荐请求"""
    referee_id: str = Field(..., description="被推荐人ID")
    reward_amount: int = Field(50, description="奖励积分", ge=0, le=500)


# ==================== 依赖注入 ====================

def get_referral_service(
    supabase = Depends(get_supabase_client)
) -> ReferralService:
    """获取Referral Service"""
    repository = ReferralRepository(supabase)
    return ReferralService(repository)


# ==================== API Endpoints ====================

@router.post("")
async def create_referral(
    request: CreateReferralRequest,
    user: dict = Depends(get_current_user),
    service: ReferralService = Depends(get_referral_service)
):
    """
    创建推荐记录

    当用户推荐新用户注册时调用
    """
    # 防止自我推荐
    if user["id"] == request.referee_id:
        raise HTTPException(400, "Cannot refer yourself")

    referral = await service.create_referral(
        referrer_id=user["id"],
        referee_id=request.referee_id,
        reward_amount=request.reward_amount
    )

    if not referral:
        raise HTTPException(500, "Failed to create referral")

    logger.info(f"User {user['id'][:8]}... created referral for {request.referee_id[:8]}...")

    return {
        "success": True,
        "data": referral.dict(),
        "message": f"Referral created with code: {referral.referral_code}"
    }


@router.get("")
async def get_referrals(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    service: ReferralService = Depends(get_referral_service)
):
    """
    获取用户的推荐列表

    返回该用户创建的所有推荐记录
    """
    referrals, total = await service.get_user_referrals(
        user_id=user["id"],
        offset=offset,
        limit=limit
    )

    return {
        "data": [r.dict() for r in referrals],
        "pagination": {
            "offset": offset,
            "limit": limit,
            "total": total
        }
    }


@router.get("/stats")
async def get_referral_stats(
    user: dict = Depends(get_current_user),
    service: ReferralService = Depends(get_referral_service)
):
    """
    获取推荐统计

    返回:
    - 总推荐数
    - 完成数
    - 待定数
    - 总奖励积分
    """
    stats = await service.get_referral_stats(user["id"])

    return {
        "data": stats
    }


@router.get("/code/{referral_code}")
async def get_referral_by_code(
    referral_code: str,
    user: dict = Depends(get_current_user),
    service: ReferralService = Depends(get_referral_service)
):
    """
    根据推荐码获取推荐信息

    用于验证推荐码是否有效
    """
    referral = await service.get_referral_by_code(referral_code)

    if not referral:
        raise HTTPException(404, f"Referral code not found: {referral_code}")

    return {
        "data": referral.dict()
    }


@router.post("/{referral_id}/complete")
async def complete_referral(
    referral_id: str,
    user: dict = Depends(get_current_user),
    service: ReferralService = Depends(get_referral_service)
):
    """
    完成推荐

    当被推荐人满足完成条件时调用 (如完成首个项目)
    """
    referral = await service.complete_referral(referral_id)

    if not referral:
        raise HTTPException(404, f"Referral not found: {referral_id}")

    logger.info(f"Referral {referral_id} completed")

    return {
        "success": True,
        "data": referral.dict(),
        "message": "Referral completed, reward will be granted"
    }


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "referrals"
    }

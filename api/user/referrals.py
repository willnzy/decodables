"""
Referrals API

@module api.user.referrals
@version 1.1.0 (Container DI Migration)

Changes in v1.1.0:
- Container DI Migration
  - Migrated to Container-based dependency injection
  - Removed direct get_async_db_client() calls
  - Architecture: API → Container → Service → Repository

推荐系统API endpoints:
- 创建推荐
- 查看推荐列表
- 获取推荐统计
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from domains.identity.aggregates.user_profile import UserProfile
from domains.referrals import ReferralService
from dependencies import get_current_user
from container import get_container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/referrals", tags=["User - Referrals"])


# ==================== Request Models ====================

class CreateReferralRequest(BaseModel):
    """创建推荐请求"""
    referee_id: str = Field(..., description="被推荐人ID")
    reward_amount: int = Field(50, description="奖励积分", ge=0, le=500)


# ==================== 依赖注入 ====================

async def get_referral_service() -> ReferralService:
    """
    获取Referral Service via Container.

    WHY Container-based DI?
    - Centralized service instantiation
    - Testable (mock injection)
    - Follows DIP (Dependency Inversion Principle)
    """
    container = get_container()
    return await container.get_referral_service()


# ==================== API Endpoints ====================

@router.post("")
async def create_referral(
    request: CreateReferralRequest,
    user: UserProfile = Depends(get_current_user),
    service: ReferralService = Depends(get_referral_service)
):
    """
    创建推荐记录

    当用户推荐新用户注册时调用
    """
    # 防止自我推荐
    if user.user_id == request.referee_id:
        raise HTTPException(400, "Cannot refer yourself")

    referral = await service.create_referral(
        referrer_id=user.user_id,
        referee_id=request.referee_id,
        reward_amount=request.reward_amount
    )

    if not referral:
        raise HTTPException(500, "Failed to create referral")

    logger.info(f"User {user.user_id[:8]}... created referral for {request.referee_id[:8]}...")

    return {
        "success": True,
        "data": referral.dict(),
        "message": f"Referral created with code: {referral.referral_code}"
    }


@router.get("")
async def get_referrals(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: UserProfile = Depends(get_current_user),
    service: ReferralService = Depends(get_referral_service)
):
    """
    获取用户的推荐列表

    P1-004 fix: Migrated to DDD-compliant response format.

    返回该用户创建的所有推荐记录

    Returns:
        {items, total, offset, limit, has_more} - DDD compliant pagination response
    """
    referrals, total = await service.get_user_referrals(
        user_id=user.user_id,
        offset=offset,
        limit=limit
    )

    items = [r.dict() for r in referrals]
    return {
        "items": items,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(items) < total
    }


@router.get("/stats")
async def get_referral_stats(
    user: UserProfile = Depends(get_current_user),
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
    stats = await service.get_referral_stats(user.user_id)

    return {
        "data": stats
    }


@router.get("/code/{referral_code}")
async def get_referral_by_code(
    referral_code: str,
    user: UserProfile = Depends(get_current_user),
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
    user: UserProfile = Depends(get_current_user),
    service: ReferralService = Depends(get_referral_service)
):
    """
    完成推荐

    当被推荐人满足完成条件时调用 (如完成首个项目)

    WS-06: Authorization check — only the referee (被推荐人) can complete
    a referral. This prevents any authenticated user from triggering
    reward credits by guessing referral IDs.
    """
    # WS-06: Verify the current user is the referee of this referral
    referral = await service.get_referral_by_id(referral_id)
    if not referral:
        raise HTTPException(404, "Referral not found")

    if referral.referee_id != user.user_id:
        logger.warning(
            f"[Referrals] Unauthorized complete attempt: "
            f"user={user.user_id[:8]}..., referral={referral_id}"
        )
        raise HTTPException(403, "Not authorized to complete this referral")

    result = await service.complete_referral(referral_id)

    if not result:
        raise HTTPException(500, "Failed to complete referral")

    logger.info(f"Referral {referral_id} completed by referee {user.user_id[:8]}...")

    return {
        "success": True,
        "data": result.dict(),
        "message": "Referral completed, reward will be granted"
    }


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "referrals"
    }

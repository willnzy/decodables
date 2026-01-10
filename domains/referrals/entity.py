"""
Referral Entity

@module domains.referrals.entity
@version 1.0.0
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ReferralEntity(BaseModel):
    """
    推荐实体

    Attributes:
        id: UUID
        referrer_id: 推荐人ID
        referee_id: 被推荐人ID
        referral_code: 推荐码
        status: 状态 (pending/completed/expired)
        reward_given: 是否已发放奖励
        reward_amount: 奖励积分数
        completed_at: 完成时间
        created_at: 创建时间
    """
    id: str
    referrer_id: str
    referee_id: str
    referral_code: str
    status: str  # pending/completed/expired
    reward_given: bool = False
    reward_amount: Optional[int] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

"""
Referral Service

@module domains.referrals.service
@version 1.0.0
"""

import logging
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from .entity import ReferralEntity
from .repository import ReferralRepository

logger = logging.getLogger(__name__)


class ReferralService:
    """推荐业务逻辑服务"""

    def __init__(self, repository: ReferralRepository):
        self.repository = repository

    def generate_referral_code(self, user_id: str) -> str:
        """
        生成推荐码

        格式: XXXX-XXXX (8字符,基于user_id哈希)
        """
        # 使用user_id + timestamp生成唯一哈希
        timestamp = str(int(datetime.now(timezone.utc).timestamp()))
        raw = f"{user_id}:{timestamp}"
        hash_obj = hashlib.sha256(raw.encode())
        hash_hex = hash_obj.hexdigest()[:8].upper()

        # 格式化为 XXXX-XXXX
        return f"{hash_hex[:4]}-{hash_hex[4:]}"

    async def create_referral(
        self,
        referrer_id: str,
        referee_id: str,
        reward_amount: int = 50
    ) -> Optional[ReferralEntity]:
        """
        创建推荐记录

        Args:
            referrer_id: 推荐人ID
            referee_id: 被推荐人ID
            reward_amount: 奖励积分数 (默认50)

        Returns:
            ReferralEntity or None
        """
        # 生成推荐码
        referral_code = self.generate_referral_code(referrer_id)

        return await self.repository.create(
            referrer_id=referrer_id,
            referee_id=referee_id,
            referral_code=referral_code,
            reward_amount=reward_amount
        )

    async def get_referral_by_code(
        self,
        referral_code: str
    ) -> Optional[ReferralEntity]:
        """根据推荐码获取推荐记录"""
        return await self.repository.get_by_code(referral_code)

    async def get_user_referrals(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 20
    ) -> tuple[List[ReferralEntity], int]:
        """获取用户的推荐列表"""
        return await self.repository.get_user_referrals(user_id, offset, limit)

    async def complete_referral(
        self,
        referral_id: str
    ) -> Optional[ReferralEntity]:
        """
        完成推荐 (被推荐人满足条件后调用)

        更新状态为completed,记录完成时间
        """
        return await self.repository.update_status(
            referral_id=referral_id,
            status="completed",
            reward_given=True,
            completed_at=datetime.now(timezone.utc)
        )

    async def get_referral_stats(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        获取用户推荐统计

        Returns:
            {
                "total": 10,
                "completed": 8,
                "pending": 2,
                "total_rewards": 400
            }
        """
        stats = await self.repository.get_stats(user_id)

        # 计算总奖励 (假设每个完成的推荐50积分)
        total_rewards = stats["completed"] * 50

        return {
            **stats,
            "total_rewards": total_rewards
        }

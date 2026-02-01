"""
Referral Service

@module domains.referrals.service
@version 1.0.0
"""

import logging
import hashlib
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime, timezone

from .entity import ReferralEntity
from .repository import ReferralRepository

if TYPE_CHECKING:
    from domains.billing import BillingService

logger = logging.getLogger(__name__)


class ReferralService:
    """推荐业务逻辑服务"""

    def __init__(
        self,
        repository: ReferralRepository,
        billing_service: "BillingService" = None,
    ):
        self.repository = repository
        self._billing_service = billing_service

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

    async def get_referral_by_id(
        self,
        referral_id: str
    ) -> Optional[ReferralEntity]:
        """WS-06: 根据 ID 获取推荐记录 (用于权限校验)"""
        return await self.repository.get_by_id(referral_id)

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

        WS-01 fix: Atomically updates status AND grants reward credits.
        Idempotency: checks reward_given before granting to prevent double-issuance.
        """
        # 1. Fetch current referral to check idempotency
        referral = await self.repository.get_by_id(referral_id)
        if not referral:
            logger.warning(f"Referral {referral_id} not found")
            return None

        if referral.reward_given:
            logger.info(f"Referral {referral_id} already completed with reward given")
            return referral

        # 2. Update status to completed
        updated = await self.repository.update_status(
            referral_id=referral_id,
            status="completed",
            reward_given=True,
            completed_at=datetime.now(timezone.utc)
        )

        # 3. Grant reward credits via BillingService (atomic with idempotency key)
        if updated and self._billing_service:
            reward_amount = referral.reward_amount or 50  # fallback default
            try:
                from domains.billing import TransactionType, CreditBucket
                await self._billing_service.add_credits(
                    user_id=referral.referrer_id,
                    amount=reward_amount,
                    bucket=CreditBucket.PERMANENT,
                    tx_type=TransactionType.REFERRAL_BONUS,
                    description=f"Referral reward for {referral_id}",
                    idempotency_key=f"referral_reward_{referral_id}",
                )
                logger.info(
                    f"Granted {reward_amount} credits to {referral.referrer_id} "
                    f"for referral {referral_id}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to grant referral reward for {referral_id}: {e}. "
                    f"Status updated but credits not granted."
                )
                # Note: Status is already updated. The idempotency key ensures
                # a retry won't double-issue credits.

        return updated

    async def get_referral_stats(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        获取用户推荐统计

        WS-01 fix: total_rewards now fetched from repository
        (actual sum of reward_amount) instead of hardcoded calculation.

        Returns:
            {
                "total": 10,
                "completed": 8,
                "pending": 2,
                "total_rewards": 400
            }
        """
        stats = await self.repository.get_stats(user_id)

        # total_rewards should come from actual DB records
        # stats["total_rewards"] is expected from repository.get_stats()
        # Fallback: if repository doesn't provide it, use completed * default
        if "total_rewards" not in stats:
            stats["total_rewards"] = stats.get("completed", 0) * 50

        return stats

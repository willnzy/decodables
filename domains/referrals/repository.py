"""
Referral Repository

@module domains.referrals.repository
@version 1.0.0
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone

from .entity import ReferralEntity

logger = logging.getLogger(__name__)


class ReferralRepository:
    """Referral数据访问层"""

    def __init__(self, supabase_client):
        self.client = supabase_client

    async def create(
        self,
        referrer_id: str,
        referee_id: str,
        referral_code: str,
        reward_amount: int = 50  # 默认50积分
    ) -> Optional[ReferralEntity]:
        """创建推荐记录"""
        try:
            data = {
                "referrer_id": referrer_id,
                "referee_id": referee_id,
                "referral_code": referral_code,
                "status": "pending",
                "reward_amount": reward_amount,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            result = await self.client.table("referrals").insert(data).execute()

            if result.data:
                return ReferralEntity(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Failed to create referral: {e}")
            return None

    async def get_by_code(self, referral_code: str) -> Optional[ReferralEntity]:
        """根据推荐码获取"""
        try:
            result = await self.client.table("referrals") \
                .select("*") \
                .eq("referral_code", referral_code) \
                .execute()

            if result.data:
                return ReferralEntity(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Failed to get referral by code: {e}")
            return None

    async def get_user_referrals(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 20
    ) -> tuple[List[ReferralEntity], int]:
        """获取用户的推荐记录"""
        try:
            result = await self.client.table("referrals") \
                .select("*", count="exact") \
                .eq("referrer_id", user_id) \
                .order("created_at", desc=True) \
                .range(offset, offset + limit - 1) \
                .execute()

            referrals = [ReferralEntity(**r) for r in result.data]
            total = result.count or 0

            return referrals, total

        except Exception as e:
            logger.error(f"Failed to get user referrals: {e}")
            return [], 0

    async def update_status(
        self,
        referral_id: str,
        status: str,
        reward_given: bool = False,
        completed_at: Optional[datetime] = None
    ) -> Optional[ReferralEntity]:
        """更新推荐状态"""
        try:
            update_data = {
                "status": status,
                "reward_given": reward_given
            }

            if completed_at:
                update_data["completed_at"] = completed_at.isoformat()

            result = await self.client.table("referrals") \
                .update(update_data) \
                .eq("id", referral_id) \
                .execute()

            if result.data:
                return ReferralEntity(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Failed to update referral status: {e}")
            return None

    async def get_stats(self, user_id: str) -> dict:
        """获取推荐统计"""
        try:
            # 总推荐数
            total_result = await self.client.table("referrals") \
                .select("id", count="exact") \
                .eq("referrer_id", user_id) \
                .execute()

            # 完成数
            completed_result = await self.client.table("referrals") \
                .select("id", count="exact") \
                .eq("referrer_id", user_id) \
                .eq("status", "completed") \
                .execute()

            # 待定数
            pending_result = await self.client.table("referrals") \
                .select("id", count="exact") \
                .eq("referrer_id", user_id) \
                .eq("status", "pending") \
                .execute()

            return {
                "total": total_result.count or 0,
                "completed": completed_result.count or 0,
                "pending": pending_result.count or 0,
            }

        except Exception as e:
            logger.error(f"Failed to get referral stats: {e}")
            return {"total": 0, "completed": 0, "pending": 0}

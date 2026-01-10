"""
Onboarding Repository

@module domains.onboarding.repository
@version 1.0.0
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone

from .entity import OnboardingStepEntity, OnboardingProgressEntity

logger = logging.getLogger(__name__)


class OnboardingRepository:
    """Onboarding数据访问层"""

    def __init__(self, supabase_client):
        self.client = supabase_client

    # ==================== Steps Management ====================

    async def get_all_active_steps(self) -> List[OnboardingStepEntity]:
        """获取所有活跃的引导步骤"""
        try:
            result = self.client.table("onboarding_steps") \
                .select("*") \
                .eq("is_active", True) \
                .order("step_order") \
                .execute()

            return [OnboardingStepEntity(**step) for step in result.data]

        except Exception as e:
            logger.error(f"Failed to get active steps: {e}")
            return []

    async def get_step_by_key(self, step_key: str) -> Optional[OnboardingStepEntity]:
        """根据key获取步骤"""
        try:
            result = self.client.table("onboarding_steps") \
                .select("*") \
                .eq("step_key", step_key) \
                .eq("is_active", True) \
                .execute()

            if result.data:
                return OnboardingStepEntity(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Failed to get step by key: {e}")
            return None

    # ==================== Progress Management ====================

    async def get_user_progress(self, user_id: str) -> List[OnboardingProgressEntity]:
        """获取用户所有进度"""
        try:
            result = self.client.table("user_onboarding_progress") \
                .select("*") \
                .eq("user_id", user_id) \
                .execute()

            return [OnboardingProgressEntity(**p) for p in result.data]

        except Exception as e:
            logger.error(f"Failed to get user progress: {e}")
            return []

    async def get_progress_by_step(
        self,
        user_id: str,
        step_key: str
    ) -> Optional[OnboardingProgressEntity]:
        """获取用户特定步骤的进度"""
        try:
            # 先获取step_id
            step = await self.get_step_by_key(step_key)
            if not step:
                return None

            result = self.client.table("user_onboarding_progress") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("step_id", step.id) \
                .execute()

            if result.data:
                return OnboardingProgressEntity(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Failed to get progress by step: {e}")
            return None

    async def create_progress(
        self,
        user_id: str,
        step_id: str,
        status: str = "pending"
    ) -> Optional[OnboardingProgressEntity]:
        """创建进度记录"""
        try:
            data = {
                "user_id": user_id,
                "step_id": step_id,
                "status": status,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            result = self.client.table("user_onboarding_progress") \
                .insert(data) \
                .execute()

            if result.data:
                return OnboardingProgressEntity(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Failed to create progress: {e}")
            return None

    async def update_progress(
        self,
        user_id: str,
        step_id: str,
        status: str,
        completed_at: Optional[datetime] = None,
        skipped_at: Optional[datetime] = None
    ) -> Optional[OnboardingProgressEntity]:
        """更新进度"""
        try:
            update_data = {"status": status}

            if completed_at:
                update_data["completed_at"] = completed_at.isoformat()
            if skipped_at:
                update_data["skipped_at"] = skipped_at.isoformat()

            result = self.client.table("user_onboarding_progress") \
                .update(update_data) \
                .eq("user_id", user_id) \
                .eq("step_id", step_id) \
                .execute()

            if result.data:
                return OnboardingProgressEntity(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Failed to update progress: {e}")
            return None

"""
Onboarding Service

@module domains.onboarding.service
@version 1.0.0
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta

from .entity import OnboardingStepEntity, OnboardingProgressEntity
from .repository import OnboardingRepository

logger = logging.getLogger(__name__)


class OnboardingService:
    """引导业务逻辑服务"""

    def __init__(self, repository: OnboardingRepository):
        self.repository = repository

    async def get_available_steps(
        self,
        user_id: str,
        user_tier: str = "t1"
    ) -> List[Dict[str, Any]]:
        """
        获取用户可用的引导步骤

        Returns:
            List of steps with progress info
        """
        # 获取所有活跃步骤
        all_steps = await self.repository.get_all_active_steps()

        # 过滤用户层级
        user_steps = [
            step for step in all_steps
            if user_tier in step.target_tiers or "all" in step.target_tiers
        ]

        # 获取用户进度
        progress_list = await self.repository.get_user_progress(user_id)
        progress_map = {p.step_id: p for p in progress_list}

        # 组合数据
        result = []
        for step in user_steps:
            progress = progress_map.get(step.id)

            result.append({
                "step": step.dict(),
                "progress": progress.dict() if progress else None,
                "status": progress.status if progress else "not_started",
                "is_completed": progress and progress.status == "completed",
                "is_skipped": progress and progress.status == "skipped",
            })

        return result

    async def start_step(
        self,
        user_id: str,
        step_key: str
    ) -> Optional[OnboardingProgressEntity]:
        """
        开始一个引导步骤

        Returns:
            OnboardingProgressEntity or None
        """
        # 获取步骤
        step = await self.repository.get_step_by_key(step_key)
        if not step:
            logger.warning(f"Step not found: {step_key}")
            return None

        # 检查是否已存在进度
        existing = await self.repository.get_progress_by_step(user_id, step_key)
        if existing:
            logger.info(f"Step already started: {step_key}")
            return existing

        # 创建进度记录
        return await self.repository.create_progress(
            user_id=user_id,
            step_id=step.id,
            status="pending"
        )

    async def complete_step(
        self,
        user_id: str,
        step_key: str
    ) -> Optional[OnboardingProgressEntity]:
        """
        完成一个引导步骤

        Returns:
            Updated progress or None
        """
        # 获取步骤
        step = await self.repository.get_step_by_key(step_key)
        if not step:
            return None

        # 获取或创建进度
        progress = await self.repository.get_progress_by_step(user_id, step_key)
        if not progress:
            progress = await self.repository.create_progress(
                user_id=user_id,
                step_id=step.id,
                status="pending"
            )

        # 更新为完成
        return await self.repository.update_progress(
            user_id=user_id,
            step_id=step.id,
            status="completed",
            completed_at=datetime.now(timezone.utc)
        )

    async def skip_step(
        self,
        user_id: str,
        step_key: str
    ) -> Optional[OnboardingProgressEntity]:
        """跳过引导步骤"""
        step = await self.repository.get_step_by_key(step_key)
        if not step:
            return None

        # 获取或创建进度
        progress = await self.repository.get_progress_by_step(user_id, step_key)
        if not progress:
            progress = await self.repository.create_progress(
                user_id=user_id,
                step_id=step.id,
                status="pending"
            )

        # 更新为跳过
        return await self.repository.update_progress(
            user_id=user_id,
            step_id=step.id,
            status="skipped",
            skipped_at=datetime.now(timezone.utc)
        )

    async def get_checklist_progress(
        self,
        user_id: str,
        user_tier: str = "t1"
    ) -> Dict[str, Any]:
        """
        获取用户任务清单进度

        Returns:
            {
                "total": 5,
                "completed": 3,
                "progress_percentage": 60,
                "steps": [...]
            }
        """
        steps_with_progress = await self.get_available_steps(user_id, user_tier)

        # 只统计必须步骤
        required_steps = [
            s for s in steps_with_progress
            if s["step"]["is_required"]
        ]

        total = len(required_steps)
        completed = sum(1 for s in required_steps if s["is_completed"])
        progress_percentage = int((completed / total * 100)) if total > 0 else 0

        return {
            "total": total,
            "completed": completed,
            "progress_percentage": progress_percentage,
            "steps": required_steps,
            "is_complete": completed == total,
        }

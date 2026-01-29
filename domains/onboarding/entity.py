"""
Onboarding Entities

@module domains.onboarding.entity
@version 1.0.0
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class OnboardingStepEntity(BaseModel):
    """
    引导步骤实体

    Attributes:
        id: UUID
        step_key: 步骤唯一标识 (如 "welcome_tour", "editor_tour")
        step_name: 显示名称
        description: 描述
        step_order: 顺序
        is_required: 是否必须完成
        target_tiers: 目标用户层级
        config: 配置JSON (包含步骤详情、奖励等)
        is_active: 是否启用
        created_at: 创建时间
        updated_at: 更新时间
    """
    id: str
    step_key: str
    step_name: str
    description: Optional[str] = None
    step_order: int
    is_required: bool = True
    target_tiers: List[str] = Field(default_factory=lambda: ["t1", "t2", "t3"])
    config: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OnboardingProgressEntity(BaseModel):
    """
    用户引导进度实体

    Attributes:
        id: UUID
        user_id: 用户ID
        step_id: 步骤ID
        status: 状态 (pending/completed/skipped)
        completed_at: 完成时间
        skipped_at: 跳过时间
        created_at: 创建时间
    """
    id: str
    user_id: str
    step_id: str
    status: str  # pending/completed/skipped
    completed_at: Optional[datetime] = None
    skipped_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

"""
Feature Flag Entity

@module domains.feature_flags.entity
@version 1.2.0

Changes in v1.2.0:
- 添加 allowed_tiers 字段支持 Tier 分层筛选
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class FeatureFlagEntity(BaseModel):
    """
    Feature Flag 领域实体

    Attributes:
        id: UUID
        key: Flag唯一标识
        name: 显示名称
        description: 描述
        flag_type: Flag类型 (boolean/multivariate/experiment)
        enabled: 是否启用
        archived: 是否归档
        environments: 环境列表
        start_at: 开始时间
        end_at: 结束时间
        rollout_percentage: 灰度百分比 (0-100)
        whitelist_user_ids: 白名单
        blacklist_user_ids: 黑名单
        targeting_rules: 定向规则
        variants: 变体配置
        default_variant: 默认变体
        tags: 标签
        owner: 负责人
        created_at: 创建时间
        updated_at: 更新时间
        created_by: 创建人
        updated_by: 更新人
    """
    id: str = Field(..., description="UUID")
    key: str = Field(..., description="Flag唯一标识")
    name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="描述")
    flag_type: str = Field("boolean", description="Flag类型")
    enabled: bool = Field(False, description="是否启用")
    archived: bool = Field(False, description="是否归档")

    # 环境和时间
    environments: List[str] = Field(default_factory=lambda: ["production", "staging"])
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None

    # 灰度配置
    rollout_percentage: int = Field(0, ge=0, le=100, description="灰度百分比")
    whitelist_user_ids: List[str] = Field(default_factory=list)
    blacklist_user_ids: List[str] = Field(default_factory=list)

    # v1.2: Tier 分层筛选
    allowed_tiers: List[str] = Field(
        default_factory=list,
        description="允许的 Tier 列表，空数组表示不限制"
    )

    # 规则和变体
    targeting_rules: List[Dict[str, Any]] = Field(default_factory=list)
    variants: List[Dict[str, Any]] = Field(default_factory=lambda: [
        {"key": "control", "value": False, "weight": 50},
        {"key": "treatment", "value": True, "weight": 50}
    ])
    default_variant: str = Field("control", description="默认变体")

    # 元数据
    tags: List[str] = Field(default_factory=list)
    owner: Optional[str] = None

    # 审计字段
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    class Config:
        from_attributes = True  # Pydantic v2
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

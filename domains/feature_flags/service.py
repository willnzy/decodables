"""
Feature Flag Domain Service

@module domains.feature_flags.service
@version 1.2.0

领域服务,处理Flag管理业务逻辑

Changes in v1.2.0:
- 支持 allowed_tiers 字段 (通过 **kwargs 自动传递)
"""

import logging
from typing import Optional, List, Dict, Any

from .entity import FeatureFlagEntity
from .repository import FeatureFlagRepository

logger = logging.getLogger(__name__)


class FeatureFlagService:
    """
    Feature Flag Domain Service

    处理Flag CRUD的业务逻辑
    """

    def __init__(self, repository: FeatureFlagRepository):
        self.repository = repository

    async def create_flag(
        self,
        key: str,
        name: str,
        admin_id: str,
        description: Optional[str] = None,
        flag_type: str = "boolean",
        **kwargs
    ) -> Optional[FeatureFlagEntity]:
        """
        创建Flag

        Args:
            key: Flag唯一标识
            name: 显示名称
            admin_id: 管理员ID
            description: 描述
            flag_type: Flag类型
            **kwargs: 其他字段

        Returns:
            FeatureFlagEntity 或 None
        """
        # 检查key是否已存在
        existing = await self.repository.get_by_key(key)
        if existing:
            logger.warning(f"Flag key already exists: {key}")
            return None

        # 构建Entity
        from datetime import datetime, timezone
        flag = FeatureFlagEntity(
            id="",  # 由数据库生成
            key=key,
            name=name,
            description=description,
            flag_type=flag_type,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            **kwargs
        )

        return await self.repository.create(flag, admin_id)

    async def get_flag(self, key: str) -> Optional[FeatureFlagEntity]:
        """获取Flag"""
        return await self.repository.get_by_key(key)

    async def list_flags(
        self,
        flag_type: Optional[str] = None,
        enabled: Optional[bool] = None,
        archived: bool = False,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 20
    ) -> tuple[List[FeatureFlagEntity], int]:
        """列表查询"""
        return await self.repository.list_flags(
            flag_type=flag_type,
            enabled=enabled,
            archived=archived,
            tags=tags,
            search=search,
            offset=offset,
            limit=limit
        )

    async def update_flag(
        self,
        key: str,
        admin_id: str,
        **updates
    ) -> Optional[FeatureFlagEntity]:
        """更新Flag"""
        return await self.repository.update(key, updates, admin_id)

    async def toggle_flag(
        self,
        key: str,
        enabled: bool,
        admin_id: str
    ) -> Optional[FeatureFlagEntity]:
        """开关Flag"""
        return await self.repository.toggle(key, enabled, admin_id)

    async def archive_flag(
        self,
        key: str,
        admin_id: str
    ) -> bool:
        """归档Flag"""
        return await self.repository.archive(key, admin_id)

    async def get_audit_logs(
        self,
        key: str,
        offset: int = 0,
        limit: int = 20
    ) -> tuple[List[Dict[str, Any]], int]:
        """获取审计日志"""
        return await self.repository.get_audit_logs(key, offset, limit)

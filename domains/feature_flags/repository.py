"""
Feature Flag Repository

@module domains.feature_flags.repository
@version 1.0.0
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from .entity import FeatureFlagEntity

logger = logging.getLogger(__name__)


class FeatureFlagRepository:
    """
    Feature Flag Repository

    数据访问层,负责与Supabase交互
    """

    def __init__(self, supabase_client):
        self.client = supabase_client

    # ==================== CRUD Operations ====================

    async def create(
        self,
        flag: FeatureFlagEntity,
        admin_id: str
    ) -> Optional[FeatureFlagEntity]:
        """创建Flag"""
        try:
            data = flag.dict(exclude={"id"})
            data["created_by"] = admin_id
            data["updated_by"] = admin_id

            result = self.client.table("feature_flags").insert(data).execute()

            if result.data:
                return FeatureFlagEntity(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Failed to create flag: {e}", exc_info=True)
            return None

    async def get_by_key(self, key: str) -> Optional[FeatureFlagEntity]:
        """根据key获取Flag"""
        try:
            result = self.client.table("feature_flags") \
                .select("*") \
                .eq("key", key) \
                .eq("archived", False) \
                .execute()

            if result.data:
                return FeatureFlagEntity(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Failed to get flag by key: {e}")
            return None

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
        """
        列表查询

        Returns:
            (flags, total_count)
        """
        try:
            query = self.client.table("feature_flags").select("*", count="exact")

            # 过滤条件
            query = query.eq("archived", archived)

            if flag_type:
                query = query.eq("flag_type", flag_type)

            if enabled is not None:
                query = query.eq("enabled", enabled)

            if tags:
                query = query.contains("tags", tags)

            if search:
                query = query.or_(f"key.ilike.%{search}%,name.ilike.%{search}%")

            # 分页
            result = query.order("created_at", desc=True) \
                .range(offset, offset + limit - 1) \
                .execute()

            flags = [FeatureFlagEntity(**item) for item in result.data]
            total_count = result.count or 0

            return flags, total_count

        except Exception as e:
            logger.error(f"Failed to list flags: {e}")
            return [], 0

    async def update(
        self,
        key: str,
        updates: Dict[str, Any],
        admin_id: str
    ) -> Optional[FeatureFlagEntity]:
        """更新Flag"""
        try:
            # 获取旧值(用于审计)
            old_flag = await self.get_by_key(key)
            if not old_flag:
                return None

            # 更新
            updates["updated_by"] = admin_id
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()

            result = self.client.table("feature_flags") \
                .update(updates) \
                .eq("key", key) \
                .execute()

            if result.data:
                # 记录审计日志
                await self._log_audit(
                    flag_id=old_flag.id,
                    flag_key=key,
                    action="updated",
                    changes=updates,
                    previous_value=old_flag.dict(),
                    changed_by=admin_id
                )
                return FeatureFlagEntity(**result.data[0])

            return None

        except Exception as e:
            logger.error(f"Failed to update flag: {e}")
            return None

    async def toggle(
        self,
        key: str,
        enabled: bool,
        admin_id: str
    ) -> Optional[FeatureFlagEntity]:
        """开关Flag"""
        return await self.update(key, {"enabled": enabled}, admin_id)

    async def archive(
        self,
        key: str,
        admin_id: str
    ) -> bool:
        """归档Flag (软删除)"""
        result = await self.update(key, {"archived": True}, admin_id)
        return result is not None

    # ==================== 审计日志 ====================

    async def _log_audit(
        self,
        flag_id: str,
        flag_key: str,
        action: str,
        changes: Dict[str, Any],
        previous_value: Dict[str, Any],
        changed_by: str,
        reason: Optional[str] = None
    ):
        """记录审计日志"""
        try:
            self.client.table("flag_audit_logs").insert({
                "flag_id": flag_id,
                "flag_key": flag_key,
                "action": action,
                "changes": changes,
                "previous_value": previous_value,
                "changed_by": changed_by,
                "reason": reason,
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to log audit: {e}")

    async def get_audit_logs(
        self,
        flag_key: str,
        offset: int = 0,
        limit: int = 20
    ) -> tuple[List[Dict[str, Any]], int]:
        """获取审计日志"""
        try:
            result = self.client.table("flag_audit_logs") \
                .select("*", count="exact") \
                .eq("flag_key", flag_key) \
                .order("changed_at", desc=True) \
                .range(offset, offset + limit - 1) \
                .execute()

            return result.data, result.count or 0

        except Exception as e:
            logger.error(f"Failed to get audit logs: {e}")
            return [], 0

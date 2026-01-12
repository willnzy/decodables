"""
Campaigns 模块 Domain Service - Campaign 管理业务逻辑

@module domains.marketing.campaigns.service
@version 3.30 (DDD Migration)

Changes in v3.30:
- Complete DDD Migration from api/admin/campaigns.py (CAM-CRITICAL-1)
- All business logic moved to Service layer
- API layer only handles HTTP concerns
- Added Audit Log (CAM-CRITICAL-3)
- Repository layer interaction abstracted

Architecture:
- API → Service → Repository
"""

import logging

from core.database import get_async_db_client
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from domains.marketing.campaigns.constants import (
    STATUS_DRAFT,
    STATUS_ACTIVE,
    STATUS_PAUSED,
    STATUS_DELETED,
)

logger = logging.getLogger(__name__)


# ==========================================
# Campaign CRUD Operations
# ==========================================

async def list_campaigns(
    status: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    获取 Campaign 列表.

    v3.30: DDD Migration - 从 API 层迁移

    Args:
        status: 状态过滤
        offset: 分页偏移
        limit: 分页大小

    Returns:
        Dict with campaigns, offset, limit
    """
    
    try:
        db_client = await get_async_db_client()
        query = db_client.table("campaigns").select("*").order("created_at", desc=True)

        if status:
            query = query.eq("status", status)

        result = query.range(offset, offset + limit - 1).execute()

        return {
            "campaigns": result.data or [],
            "offset": offset,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"[Campaigns] Failed to list campaigns: {e}")
        return {"campaigns": [], "offset": offset, "limit": limit}


async def get_campaign(campaign_id: str) -> Optional[Dict[str, Any]]:
    """
    获取单个 Campaign.

    v3.30: DDD Migration - 从 API 层迁移

    Args:
        campaign_id: Campaign ID

    Returns:
        Campaign data or None
    """
    
    try:
        db_client = await get_async_db_client()
        result = db_client.table("campaigns").select("*").eq("id", campaign_id).execute()

        if not result.data:
            return None

        return result.data[0]
    except Exception as e:
        logger.error(f"[Campaigns] Failed to get campaign {campaign_id}: {e}")
        return None


async def create_campaign(
    name: str,
    description: Optional[str],
    campaign_type: str,
    config: dict,
    target_type: str,
    target_config: Optional[dict],
    notification_channels: List[str],
    notification_config: Optional[dict],
    start_at: str,
    end_at: Optional[str],
    timezone: str,
    usage_limit: Optional[int],
    usage_per_user: Optional[int],
    admin_id: str,
) -> Optional[Dict[str, Any]]:
    """
    创建 Campaign.

    v3.30: DDD Migration
    - 从 API 层迁移
    - 添加 Audit Log (CAM-CRITICAL-3)

    Args:
        name: Campaign 名称
        description: 描述
        campaign_type: Campaign 类型
        config: 配置
        target_type: 目标类型
        target_config: 目标配置
        notification_channels: 通知渠道
        notification_config: 通知配置
        start_at: 开始时间
        end_at: 结束时间
        timezone: 时区
        usage_limit: 使用限制
        usage_per_user: 每用户使用限制
        admin_id: 管理员 ID

    Returns:
        创建的 Campaign 或 None
    """
    
    campaign_data = {
        "name": name,
        "description": description,
        "type": campaign_type,
        "config": config,
        "target_type": target_type,
        "target_config": target_config,
        "notification_channels": notification_channels,
        "notification_config": notification_config,
        "start_at": start_at,
        "end_at": end_at,
        "timezone": timezone,
        "usage_limit": usage_limit,
        "usage_per_user": usage_per_user,
        "status": STATUS_DRAFT,
        "is_active": False,
        "created_by": admin_id,
    }

    try:
        db_client = await get_async_db_client()
        result = db_client.table("campaigns").insert(campaign_data).execute()

        if not result.data:
            return None

        campaign = result.data[0]

        # Audit Log
        await _log_campaign_change(
            campaign_id=campaign["id"],
            action="create",
            old_value=None,
            new_value=campaign,
            admin_id=admin_id
        )

        logger.info(f"[Campaigns] Campaign {campaign['id']} created by {admin_id}")
        return campaign

    except Exception as e:
        logger.error(f"[Campaigns] Failed to create campaign: {e}")
        return None


async def update_campaign(
    campaign_id: str,
    update_data: Dict[str, Any],
    admin_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    更新 Campaign.

    v3.30: DDD Migration
    - 从 API 层迁移
    - 添加 Audit Log (CAM-CRITICAL-3)

    Args:
        campaign_id: Campaign ID
        update_data: 更新数据
        admin_id: 管理员 ID

    Returns:
        更新后的 Campaign 或 None
    """
    
    if not update_data:
        return None

    try:
        db_client = await get_async_db_client()

        # 获取旧值 (for audit)
        old_campaign = await get_campaign(campaign_id)

        # 添加更新时间
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        # 更新
        result = db_client.table("campaigns").update(update_data).eq("id", campaign_id).execute()

        if not result.data:
            return None

        new_campaign = result.data[0]

        # Audit Log
        if admin_id:
            await _log_campaign_change(
                campaign_id=campaign_id,
                action="update",
                old_value=old_campaign,
                new_value=new_campaign,
                admin_id=admin_id
            )

        logger.info(f"[Campaigns] Campaign {campaign_id} updated by {admin_id}")
        return new_campaign

    except Exception as e:
        logger.error(f"[Campaigns] Failed to update campaign {campaign_id}: {e}")
        return None


async def delete_campaign(
    campaign_id: str,
    admin_id: str,
) -> bool:
    """
    删除 Campaign (软删除).

    v3.30: DDD Migration
    - 从 API 层迁移
    - 添加 Audit Log (CAM-CRITICAL-3)

    Args:
        campaign_id: Campaign ID
        admin_id: 管理员 ID

    Returns:
        是否成功
    """
    
    try:
        db_client = await get_async_db_client()

        # 获取旧值 (for audit)
        old_campaign = await get_campaign(campaign_id)

        # 软删除
        result = db_client.table("campaigns").update({
            "status": STATUS_DELETED,
            "is_active": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", campaign_id).execute()

        if not result.data:
            return False

        # Audit Log
        await _log_campaign_change(
            campaign_id=campaign_id,
            action="delete",
            old_value=old_campaign,
            new_value={"status": STATUS_DELETED, "is_active": False},
            admin_id=admin_id
        )

        logger.info(f"[Campaigns] Campaign {campaign_id} deleted by {admin_id}")
        return True

    except Exception as e:
        logger.error(f"[Campaigns] Failed to delete campaign {campaign_id}: {e}")
        return False


async def activate_campaign(
    campaign_id: str,
    admin_id: str,
) -> bool:
    """
    激活 Campaign.

    v3.30: DDD Migration
    - 从 API 层迁移
    - 添加 Audit Log (CAM-CRITICAL-3)

    Args:
        campaign_id: Campaign ID
        admin_id: 管理员 ID

    Returns:
        是否成功
    """
    
    try:
        db_client = await get_async_db_client()

        # 获取旧值 (for audit)
        old_campaign = await get_campaign(campaign_id)

        # 激活
        result = db_client.table("campaigns").update({
            "status": STATUS_ACTIVE,
            "is_active": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", campaign_id).execute()

        if not result.data:
            return False

        # Audit Log
        await _log_campaign_change(
            campaign_id=campaign_id,
            action="activate",
            old_value=old_campaign,
            new_value={"status": STATUS_ACTIVE, "is_active": True},
            admin_id=admin_id
        )

        logger.info(f"[Campaigns] Campaign {campaign_id} activated by {admin_id}")
        return True

    except Exception as e:
        logger.error(f"[Campaigns] Failed to activate campaign {campaign_id}: {e}")
        return False


async def pause_campaign(
    campaign_id: str,
    admin_id: str,
) -> bool:
    """
    暂停 Campaign.

    v3.30: DDD Migration
    - 从 API 层迁移
    - 添加 Audit Log (CAM-CRITICAL-3)

    Args:
        campaign_id: Campaign ID
        admin_id: 管理员 ID

    Returns:
        是否成功
    """
    
    try:
        db_client = await get_async_db_client()

        # 获取旧值 (for audit)
        old_campaign = await get_campaign(campaign_id)

        # 暂停
        result = db_client.table("campaigns").update({
            "status": STATUS_PAUSED,
            "is_active": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", campaign_id).execute()

        if not result.data:
            return False

        # Audit Log
        await _log_campaign_change(
            campaign_id=campaign_id,
            action="pause",
            old_value=old_campaign,
            new_value={"status": STATUS_PAUSED, "is_active": False},
            admin_id=admin_id
        )

        logger.info(f"[Campaigns] Campaign {campaign_id} paused by {admin_id}")
        return True

    except Exception as e:
        logger.error(f"[Campaigns] Failed to pause campaign {campaign_id}: {e}")
        return False


async def get_campaign_stats(campaign_id: str) -> Optional[Dict[str, Any]]:
    """
    获取 Campaign 统计.

    v3.30: DDD Migration - 从 API 层迁移

    Args:
        campaign_id: Campaign ID

    Returns:
        统计数据或 None
    """
    
    try:
        db_client = await get_async_db_client()

        # 获取 Campaign
        campaign = await get_campaign(campaign_id)
        if not campaign:
            return None

        # 获取 Claims
        claims_result = db_client.table("campaign_claims").select(
            "id, credits_received, created_at",
        ).eq("campaign_id", campaign_id).execute()

        claims = claims_result.data or []
        total_credits = sum(c.get("credits_received", 0) for c in claims)

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign.get("name"),
            "status": campaign.get("status"),
            "total_claims": len(claims),
            "total_credits_given": total_credits,
            "usage_count": campaign.get("usage_count", 0),
            "usage_limit": campaign.get("usage_limit"),
        }

    except Exception as e:
        logger.error(f"[Campaigns] Failed to get stats for campaign {campaign_id}: {e}")
        return None


# ==========================================
# Helper Functions
# ==========================================

async def _log_campaign_change(
    campaign_id: str,
    action: str,
    old_value: Any,
    new_value: Any,
    admin_id: str
):
    """
    记录 Campaign 变更审计日志.

    v3.30: 新增 (CAM-CRITICAL-3)

    Args:
        campaign_id: Campaign ID
        action: 操作类型
        old_value: 旧值
        new_value: 新值
        admin_id: 管理员 ID
    """
    
    try:
        db_client = await get_async_db_client()

        import json
        db_client.table("campaign_audit_logs").insert({
            "campaign_id": campaign_id,
            "action": action,
            "old_value": json.dumps(old_value) if old_value else None,
            "new_value": json.dumps(new_value) if new_value else None,
            "admin_id": admin_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        logger.debug(f"[Campaigns] Audit log created for campaign {campaign_id}")

    except Exception as e:
        logger.warning(f"[Campaigns] Failed to log campaign change: {e}")

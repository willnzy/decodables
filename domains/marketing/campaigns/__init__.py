"""
Campaigns 模块 - Campaign 管理

@module domains.marketing.campaigns
@version 3.30 (DDD Migration)

This domain handles:
- Campaign CRUD operations
- Campaign activation/pause
- Campaign statistics
- Campaign audit logging
"""

from domains.marketing.campaigns.service import (
    list_campaigns,
    get_campaign,
    create_campaign,
    update_campaign,
    delete_campaign,
    activate_campaign,
    pause_campaign,
    get_campaign_stats,
)

__all__ = [
    "list_campaigns",
    "get_campaign",
    "create_campaign",
    "update_campaign",
    "delete_campaign",
    "activate_campaign",
    "pause_campaign",
    "get_campaign_stats",
]

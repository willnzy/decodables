"""
Marketing Domain - Campaigns, promotions, and marketing operations.

@module domains.marketing
@version 1.1.0

Changes:
- v1.1.0: Added CampaignService for DDD compliance
"""

from .repository import ICampaignRepository, CampaignData
from .service import CampaignService, ClaimResult, CampaignWithStatus

__all__ = [
    "ICampaignRepository",
    "CampaignData",
    "CampaignService",
    "ClaimResult",
    "CampaignWithStatus",
]

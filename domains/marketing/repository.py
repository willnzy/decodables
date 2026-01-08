"""
Marketing Repository Interfaces - Abstract data access for marketing domain.

@module domains.marketing.repository
@version 1.0.0

This defines the repository interfaces (ports) for marketing operations.
Concrete implementations live in infrastructure/repositories/.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Set, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CampaignData:
    """Campaign data transfer object."""
    id: str
    name: str
    description: Optional[str]
    type: str
    config: dict
    target_type: str
    target_config: dict
    notification_channels: List[str]
    notification_config: dict
    start_at: datetime
    end_at: datetime
    usage_limit: Optional[int]
    usage_count: int
    status: str
    is_active: bool


class ICampaignRepository(ABC):
    """
    Repository interface for campaign operations.
    """

    @abstractmethod
    async def get_active_campaigns(self) -> List[CampaignData]:
        """
        Get all currently active campaigns.

        Returns:
            List of active campaigns within valid time range
        """
        pass

    @abstractmethod
    async def get_by_id(self, campaign_id: str) -> Optional[CampaignData]:
        """
        Get campaign by ID.

        Args:
            campaign_id: Campaign ID

        Returns:
            CampaignData or None if not found
        """
        pass

    @abstractmethod
    async def get_user_campaign_status(
        self, campaign_ids: List[str], user_id: str
    ) -> Tuple[Set[str], Dict[str, List[str]]]:
        """
        Batch fetch user's claim and dismissal status for multiple campaigns.

        Args:
            campaign_ids: List of campaign IDs to check
            user_id: User ID

        Returns:
            Tuple of (claimed_campaign_ids, dismissed_channels_map)
        """
        pass

    @abstractmethod
    async def record_claim(
        self, campaign_id: str, user_id: str, credits_received: int
    ) -> bool:
        """
        Record a campaign claim.

        Args:
            campaign_id: Campaign ID
            user_id: User ID
            credits_received: Credits awarded

        Returns:
            True if claim recorded, False if duplicate
        """
        pass

    @abstractmethod
    async def delete_claim(self, campaign_id: str, user_id: str) -> None:
        """
        Delete a campaign claim (for rollback purposes).

        Args:
            campaign_id: Campaign ID
            user_id: User ID
        """
        pass

    @abstractmethod
    async def increment_usage_count(self, campaign_id: str) -> bool:
        """
        Atomically increment campaign usage count.

        Args:
            campaign_id: Campaign ID

        Returns:
            True if incremented, False if limit reached
        """
        pass

    @abstractmethod
    async def record_dismissal(
        self, campaign_id: str, user_id: str, channel: str
    ) -> None:
        """
        Record notification dismissal.

        Args:
            campaign_id: Campaign ID
            user_id: User ID
            channel: Notification channel (modal/toast/banner)
        """
        pass

"""
Campaign Service - Domain service for campaign operations.

@module domains.marketing.service
@version 1.0.0

This service encapsulates campaign business logic and coordinates
between the repository and other domain services (like billing).
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple, Set
from dataclasses import dataclass

from .repository import ICampaignRepository, CampaignData

logger = logging.getLogger(__name__)


# ==========================================
# Constants
# ==========================================

# Valid notification channels
VALID_NOTIFICATION_CHANNELS = {"banner", "modal", "toast", "personal_message"}

# Valid campaign types
VALID_CAMPAIGN_TYPES = {"credits_gift", "credits_discount", "credits_bonus"}

# Maximum credit amount for validation
MAX_CREDIT_AMOUNT = 10000


# ==========================================
# DTOs / Result Types
# ==========================================

@dataclass
class ClaimResult:
    """Result of claiming a campaign."""
    success: bool
    credits_received: int = 0
    message: str = ""
    error_code: Optional[str] = None


@dataclass
class CampaignWithStatus:
    """Campaign data with user-specific status."""
    campaign: CampaignData
    has_claimed: bool
    can_claim: bool


# ==========================================
# Service
# ==========================================

class CampaignService:
    """
    Domain service for campaign operations.

    Responsibilities:
    - Validate campaign eligibility
    - Check target audience matching
    - Coordinate claim process with billing
    - Build notification data
    """

    def __init__(self, campaign_repo: ICampaignRepository):
        self._repo = campaign_repo

    async def get_active_campaigns_for_user(
        self, user: Optional[dict]
    ) -> Tuple[List[CampaignWithStatus], Dict[str, List[str]]]:
        """
        Get active campaigns visible to the user with status.

        Args:
            user: User dict or None for anonymous

        Returns:
            Tuple of (campaigns with status, dismissed channels map)
        """
        campaigns = await self._repo.get_active_campaigns()

        if not campaigns:
            return [], {}

        campaign_ids = [c.id for c in campaigns]
        claimed_set: Set[str] = set()
        dismissed_map: Dict[str, List[str]] = {}

        if user:
            claimed_set, dismissed_map = await self._repo.get_user_campaign_status(
                campaign_ids, user["id"]
            )

        result = []
        for campaign in campaigns:
            if not self._check_target_eligibility(campaign, user):
                continue

            has_claimed = campaign.id in claimed_set
            can_claim = not has_claimed and self._check_usage_limit(campaign)

            result.append(CampaignWithStatus(
                campaign=campaign,
                has_claimed=has_claimed,
                can_claim=can_claim,
            ))

        return result, dismissed_map

    async def claim_campaign(
        self,
        campaign_id: str,
        user: dict,
        grant_credits_fn,  # Async function to grant credits
    ) -> ClaimResult:
        """
        Claim a campaign reward.

        Args:
            campaign_id: Campaign ID
            user: User dict
            grant_credits_fn: Async function (user_id, amount, description) -> None

        Returns:
            ClaimResult with success status and credits received
        """
        # Fetch campaign
        campaign = await self._repo.get_by_id(campaign_id)
        if not campaign:
            return ClaimResult(False, error_code="NOT_FOUND", message="Campaign not found")

        # Check active status
        if campaign.status != "active" or not campaign.is_active:
            return ClaimResult(False, error_code="INACTIVE", message="Campaign is not active")

        # Check time range
        now = datetime.now(timezone.utc)
        if now < campaign.start_at:
            return ClaimResult(False, error_code="NOT_STARTED", message="Campaign has not started yet")
        if now >= campaign.end_at:
            return ClaimResult(False, error_code="ENDED", message="Campaign has ended")

        # Check eligibility
        if not self._check_target_eligibility(campaign, user):
            return ClaimResult(False, error_code="NOT_ELIGIBLE", message="You are not eligible for this campaign")

        # Check usage limit
        if not self._check_usage_limit(campaign):
            return ClaimResult(False, error_code="LIMIT_REACHED", message="Campaign usage limit reached")

        # Validate campaign type
        if campaign.type not in VALID_CAMPAIGN_TYPES:
            logger.error(f"[CampaignService] Unknown campaign type: {campaign.type}")
            return ClaimResult(False, error_code="CONFIG_ERROR", message="Campaign configuration error")

        # Calculate credits
        credits_received = 0
        if campaign.type == "credits_gift":
            credits_received = self._validate_credit_amount(campaign.config.get("amount", 0))
            if credits_received is None:
                logger.error(f"[CampaignService] Invalid credit amount in campaign {campaign_id}")
                return ClaimResult(False, error_code="CONFIG_ERROR", message="Campaign configuration error")

        # Record claim (uses UNIQUE constraint to prevent race condition)
        claim_success = await self._repo.record_claim(campaign_id, user["id"], credits_received)
        if not claim_success:
            return ClaimResult(False, error_code="ALREADY_CLAIMED", message="You have already claimed this campaign")

        # Grant credits
        try:
            if credits_received > 0:
                await grant_credits_fn(
                    user["id"],
                    credits_received,
                    f"Campaign reward: {campaign.name}",
                )
        except Exception as e:
            # Rollback claim record
            logger.error(f"[CampaignService] Credit grant failed for campaign {campaign_id}: {e}")
            await self._repo.delete_claim(campaign_id, user["id"])
            return ClaimResult(False, error_code="CREDIT_FAILED", message="Failed to grant credits. Please try again.")

        # Increment usage count (non-critical)
        await self._repo.increment_usage_count(campaign_id)

        # Audit log
        logger.info(f"[CampaignService] CLAIM_SUCCESS campaign={campaign_id} user={user['id']} credits={credits_received}")

        message = f"You received {credits_received} credits!" if credits_received > 0 else "Offer claimed successfully!"
        return ClaimResult(True, credits_received=credits_received, message=message)

    async def dismiss_notification(
        self, campaign_id: str, user_id: str, channel: str
    ) -> bool:
        """
        Dismiss a campaign notification.

        Args:
            campaign_id: Campaign ID
            user_id: User ID
            channel: Notification channel

        Returns:
            True if dismissed successfully
        """
        await self._repo.record_dismissal(campaign_id, user_id, channel)
        return True

    def _check_target_eligibility(self, campaign: CampaignData, user: Optional[dict]) -> bool:
        """Check if user matches the campaign's target audience."""
        target_type = campaign.target_type
        target_config = campaign.target_config

        if target_type == "all":
            return True

        if not user:
            return False

        if target_type == "subscription":
            user_tier = user.get("tier", "free")
            allowed_tiers = target_config.get("tiers", [])
            return user_tier in allowed_tiers

        elif target_type == "users":
            allowed_users = target_config.get("user_ids", [])
            return user["id"] in allowed_users

        elif target_type == "new_users":
            days = target_config.get("days_since_signup", 7)
            created_at = user.get("created_at")
            if not created_at:
                return False
            try:
                signup_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                return (now - signup_date).days <= days
            except Exception:
                return False

        elif target_type == "inactive_users":
            days = target_config.get("days_inactive", 30)
            last_login = user.get("last_login_at")
            if not last_login:
                return True  # Never logged in = inactive
            try:
                login_date = datetime.fromisoformat(last_login.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                return (now - login_date).days >= days
            except Exception:
                return False

        return False

    def _check_usage_limit(self, campaign: CampaignData) -> bool:
        """Check if campaign has remaining usage capacity."""
        if campaign.usage_limit is None:
            return True
        return campaign.usage_count < campaign.usage_limit

    def _validate_credit_amount(self, amount) -> Optional[int]:
        """Validate credit amount is within acceptable range."""
        try:
            value = int(amount)
            if value < 0 or value > MAX_CREDIT_AMOUNT:
                return None
            return value
        except (ValueError, TypeError):
            return None

    def is_valid_notification_channel(self, channel: str) -> bool:
        """Check if notification channel is valid."""
        return channel in VALID_NOTIFICATION_CHANNELS

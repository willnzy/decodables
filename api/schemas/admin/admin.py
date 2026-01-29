"""
Admin Schemas - Admin operation request models

@module schemas.admin
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class CreditAdjustRequest(BaseModel):
    """Admin credit adjustment request."""
    user_id: str
    amount: int
    bucket: str = Field(default="permanent", pattern="^(monthly|permanent)$")
    reason: Optional[str] = None


class TierUpdateRequest(BaseModel):
    """Admin tier update request."""
    user_id: str
    tier: str = Field(..., pattern="^(t1|t2|t3)$")


class DiscountCreateRequest(BaseModel):
    """Admin discount creation request."""
    user_id: str
    discount_percent: int = Field(..., ge=1, le=100)
    valid_days: int = Field(..., ge=1, le=365)
    target_plan: Optional[str] = Field(default=None, pattern="^(t2|t3)$")


class BroadcastRequest(BaseModel):
    """Admin broadcast notification request."""
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=1000)
    target_group: str = Field(default="all", pattern="^(all|t1|t2|t3)$")


class ModerationAction(BaseModel):
    """Admin moderation action."""
    reason: Optional[str] = Field(default=None, max_length=500)


# Legacy admin schemas (from app.py)
class AdminAdjustRequest(BaseModel):
    """Admin credit adjustment (legacy)."""
    user_id: str
    amount: int
    bucket: Optional[str] = "permanent"  # 'monthly' | 'permanent'
    reason: str


class AdminTierRequest(BaseModel):
    """Admin tier update (legacy)."""
    user_id: str
    tier: str


class AdminDowngradeRequest(BaseModel):
    """Admin downgrade request."""
    user_id: str
    user_code: str  # For verification
    user_email: str  # For verification
    target_tier: str  # 't2' | 't1'
    immediate: bool = False  # True = immediate, False = apply at period end
    reason: str


class AdminDiscountRequest(BaseModel):
    """Admin discount (legacy)."""
    user_id: str
    discount_percent: int
    valid_days: int
    target_plan: Optional[str] = None


class AdminBroadcastRequest(BaseModel):
    """Admin broadcast (legacy)."""
    title: str
    content: str
    target_group: Optional[str] = "all"  # 'all', 't1', 't2', 't3'


class AdminModerationRejectRequest(BaseModel):
    """Admin moderation reject request."""
    reason: str


class AdminRefundRequest(BaseModel):
    """Admin refund request."""
    user_id: str
    user_code: str  # Must match email for verification
    payment_intent_id: str
    amount_cents: Optional[int] = None  # None = full refund
    reason: str


class AdminCancelSubscriptionRequest(BaseModel):
    """Admin cancel subscription request."""
    user_id: str
    user_code: str  # Must match email for verification
    subscription_id: str
    immediate: bool = False  # True = cancel now, False = cancel at period end
    reason: str


class AdminSendNotificationRequest(BaseModel):
    """Send notification to single user."""
    user_id: str
    title: str
    content: str
    notification_type: Optional[str] = "system"


class AdminBatchNotificationRequest(BaseModel):
    """Send notification to multiple users."""
    user_ids: List[str]
    title: str
    content: str
    notification_type: Optional[str] = "system"


class ReportResponseRequest(BaseModel):
    """Admin report response request."""
    status: str  # 'reviewed' | 'resolved' | 'dismissed'
    response: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    """Admin config update request."""
    config_key: str
    config_value: dict


class BatchConfigUpdateRequest(BaseModel):
    """Admin batch config update request."""
    updates: List[dict]  # [{"config_key": "...", "config_value": {...}}, ...]


class RateLimitPresetRequest(BaseModel):
    """Admin rate limit preset request."""
    preset: str  # "strict", "normal", "relaxed", "disabled"

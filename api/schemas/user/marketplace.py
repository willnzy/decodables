"""
Marketplace Schemas - Marketplace listing and purchase models

@module schemas.marketplace
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from config import MAX_LISTING_PRICE


class ListingCreate(BaseModel):
    """Create/publish listing request."""
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default="", max_length=500)
    thumbnail_url: str
    resource_url: str
    resource_id: Optional[str] = None  # The actual ID of the resource
    resource_type: str
    price_credits: int = Field(default=0, ge=0, le=MAX_LISTING_PRICE)
    allowed_tiers: Optional[List[str]] = None
    version: Optional[str] = Field(default="1.0", max_length=20)
    changelog: Optional[str] = Field(default="", max_length=500)
    
    @field_validator('resource_type')
    @classmethod
    def validate_type(cls, v):
        if v not in ['project', 'asset']:
            raise ValueError('resource_type must be project or asset')
        return v
    
    @field_validator('allowed_tiers')
    @classmethod
    def validate_tiers(cls, v):
        if v is None:
            return None
        valid_options = [['free'], ['starter', 'pro'], ['pro']]
        sorted_v = sorted(v) if v else []
        for valid in valid_options:
            if sorted(valid) == sorted_v:
                return v
        raise ValueError("allowed_tiers must be ['free'], ['starter','pro'], or ['pro']")


class ListingUpdate(BaseModel):
    """Update listing request."""
    title: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    price_credits: Optional[int] = Field(default=None, ge=0, le=MAX_LISTING_PRICE)
    allowed_tiers: Optional[List[str]] = None


class ListingResponse(BaseModel):
    """Marketplace listing response."""
    id: str
    seller_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    thumbnail_url: str
    resource_url: str
    resource_id: Optional[str] = None
    resource_type: str
    price_credits: int
    allowed_tiers: List[str]
    usage_count: int = 0
    sales_count: int = 0
    is_public: bool = False
    is_deleted: bool = False
    moderation_status: str = "draft"
    moderation_note: Optional[str] = None
    created_at: datetime
    # Computed fields
    is_owned: Optional[bool] = None
    is_accessible: Optional[bool] = None


class MarketplacePublishRequest(BaseModel):
    """Publish to marketplace request."""
    title: str
    description: Optional[str] = ""
    thumbnail_url: str
    resource_url: str
    resource_type: str  # 'project' | 'asset'
    price_credits: int = 0
    allowed_tiers: List[str]  # Required; only ['free'], ['starter','pro'], or ['pro']


class MarketplacePurchaseRequest(BaseModel):
    """Purchase from marketplace request."""
    listing_id: str
    idempotency_key: Optional[str] = None  # Prevent duplicate purchases
    utm_source: Optional[str] = None  # Analytics tracking
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    referral_context: Optional[str] = None  # 'homepage', 'search', 'category', etc.


class ListingUpdateRequest(BaseModel):
    """Update listing request (simplified)."""
    title: Optional[str] = None
    description: Optional[str] = None
    price_credits: Optional[int] = None
    is_public: Optional[bool] = None
    allowed_tiers: Optional[List[str]] = None


class PurchaseRequest(BaseModel):
    """Purchase request with UTM tracking support."""
    listing_id: str
    idempotency_key: Optional[str] = None  # For deduplication
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    referral_context: Optional[dict] = None  # Additional referral info


class PurchaseResult(BaseModel):
    """Purchase result."""
    success: bool
    already_owned: bool = False
    price_paid: int = 0
    seller_revenue: Optional[int] = None
    message: str


class SellerStats(BaseModel):
    """Seller statistics."""
    total_earned_credits: int = 0
    listings_count: int = 0
    total_sales: int = 0
    total_usage: int = 0


class ReportRequest(BaseModel):
    """Content report request."""
    listing_id: str
    reason: str

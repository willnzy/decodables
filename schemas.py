"""
Pydantic Schemas
Request/Response models for API endpoints

@module schemas
"""

from typing import Optional, List, Any, Generic, TypeVar
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from config import MAX_LISTING_PRICE

T = TypeVar('T')


# ==========================================
# Generic Response Models
# ==========================================

class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""
    items: List[T]
    total: int
    page: int
    limit: int
    has_more: bool = False
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, limit: int):
        return cls(
            items=items,
            total=total,
            page=page,
            limit=limit,
            has_more=total > page * limit
        )


# ==========================================
# User Schemas
# ==========================================

class UserProfile(BaseModel):
    """User profile response."""
    id: str
    email: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    tier: str = "free"
    subscription_status: str = "inactive"
    credits_monthly: int = 0
    credits_permanent: int = 0
    credits_total: int = 0
    is_member: bool = False
    role: str = "user"


class CreditTransaction(BaseModel):
    """Credit transaction record."""
    id: str
    amount: int
    bucket: str
    balance_monthly_after: int
    balance_permanent_after: int
    type: str
    description: Optional[str] = None
    created_at: datetime


# ==========================================
# Project Schemas
# ==========================================

class ProjectCreate(BaseModel):
    """Create project request."""
    title: Optional[str] = Field(default="My Magic Story", max_length=100)
    canvas_data: Optional[dict] = None


class ProjectUpdate(BaseModel):
    """Update project request."""
    title: Optional[str] = Field(default=None, max_length=100)
    canvas_data: Optional[dict] = None
    thumbnail_url: Optional[str] = None
    used_listing_ids: Optional[List[str]] = None


class ProjectResponse(BaseModel):
    """Project response."""
    id: str
    user_id: str
    title: str
    thumbnail_url: Optional[str] = None
    canvas_data: Optional[dict] = None
    contains_locked_elements: bool = False
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime


class ProjectSaveResult(BaseModel):
    """Result of project save operation."""
    status: str = "saved"
    locked_elements: List[dict] = []
    new_usage_recorded: List[str] = []


# ==========================================
# Marketplace Schemas
# ==========================================

class ListingCreate(BaseModel):
    """Create/publish listing request."""
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default="", max_length=500)
    thumbnail_url: str
    resource_url: str
    resource_id: Optional[str] = None  # The actual ID of the resource (asset.id or project.id)
    resource_type: str
    price_credits: int = Field(default=0, ge=0, le=MAX_LISTING_PRICE)
    allowed_tiers: Optional[List[str]] = None
    version: Optional[str] = Field(default="1.0", max_length=20)  # Version number
    changelog: Optional[str] = Field(default="", max_length=500)  # What's new in this version
    
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
    resource_id: Optional[str] = None  # The actual resource UUID (project.id or asset.id)
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


class PurchaseRequest(BaseModel):
    """Purchase request."""
    listing_id: str


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


# ==========================================
# Admin Schemas
# ==========================================

class CreditAdjustRequest(BaseModel):
    """Admin credit adjustment request."""
    user_id: str
    amount: int
    bucket: str = Field(default="permanent", pattern="^(monthly|permanent)$")
    reason: Optional[str] = None


class TierUpdateRequest(BaseModel):
    """Admin tier update request."""
    user_id: str
    tier: str = Field(..., pattern="^(free|starter|pro)$")


class DiscountCreateRequest(BaseModel):
    """Admin discount creation request."""
    user_id: str
    discount_percent: int = Field(..., ge=1, le=100)
    valid_days: int = Field(..., ge=1, le=365)
    target_plan: Optional[str] = Field(default=None, pattern="^(starter|pro)$")


class BroadcastRequest(BaseModel):
    """Admin broadcast notification request."""
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=1000)
    target_group: str = Field(default="all", pattern="^(all|free|starter|pro)$")


class ModerationAction(BaseModel):
    """Admin moderation action."""
    reason: Optional[str] = Field(default=None, max_length=500)


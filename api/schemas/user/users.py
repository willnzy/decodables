"""
User Schemas - User profile and credit related models

@module schemas.users
"""

from typing import Optional
from pydantic import BaseModel
from datetime import datetime


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


class TimezoneUpdateRequest(BaseModel):
    """Request body for updating user timezone."""
    timezone: str  # IANA timezone identifier (e.g., 'Asia/Shanghai')

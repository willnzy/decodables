"""
Admin Subscriptions Router - Subscription management endpoints for admins

@module api.admin.subscriptions
@version 3.28

Changes:
- v3.28: P1/P2 Architecture refactoring
  - SUB-MEDIUM-1/2/3: Extracted business logic to SubscriptionService
  - SUB-MEDIUM-5: Created SubscriptionRepository
  - SUB-MEDIUM-6: Added Response Models (RefundResponse, etc.)
  - SUB-MEDIUM-7: Split complex downgrade logic into smaller methods
  - SUB-MEDIUM-8: Extracted common user_code validation to Service layer
  - Endpoints now delegate to Service layer (DDD pattern)
- v3.27: P0 Security fixes
  - SUB-CRITICAL-1: Replaced direct stripe.Subscription.retrieve() with service wrapper
  - SUB-CRITICAL-2: Replaced direct stripe.Subscription.modify() with service wrapper
  - SUB-HIGH-1/2/3/5: Added timeout to all Stripe API calls
  - SUB-HIGH-4: Removed unused get_supabase_client() call
  - SUB-MEDIUM-4: Removed function-level stripe imports (already at module level)
- v3.25: Security improvements
  - SUB-MEDIUM-1: Added field length limits to request models
  - SUB-MEDIUM-2: Added target_tier enum validation
  - SUB-LOW-1: Limited Stripe error exposure

Endpoints:
- POST /api/admin/refund - Process refund
- POST /api/admin/subscription/cancel - Cancel subscription
- POST /api/admin/subscription/downgrade - Downgrade subscription
"""

import os
import logging
from typing import Optional

import stripe  # v3.27: Moved to module level (SUB-MEDIUM-4)

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field, field_validator

from core.database import get_database_client
from infrastructure.repositories import (
    SupabaseAdminUsersRepository,
    SupabasePaymentRepository,
    SupabaseUserRepository,
)
from domains.subscriptions import SubscriptionService  # v3.28: Service layer
from infrastructure.rate_limiter import limiter
from dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["admin-subscriptions-v2"])


# ==========================================
# Constants (v3.25)
# ==========================================

# v3.25: SUB-MEDIUM-2 - Valid target tiers for downgrade
VALID_TARGET_TIERS = {"t1", "t2"}

# v3.25: Monthly credits by tier (from CLAUDE.md business rules)
TIER_MONTHLY_CREDITS = {
    "t1": 0,
    "t2": 200,
    "t3": 500,
}


# ==========================================
# Request Models (v3.25: Added field validation)
# ==========================================

class AdminRefundRequest(BaseModel):
    # v3.25: SUB-MEDIUM-1 - Field length limits
    user_id: str = Field(..., min_length=1, max_length=100)
    user_code: str = Field(..., min_length=1, max_length=50)  # Must match for verification
    payment_intent_id: str = Field(..., min_length=1, max_length=100)
    amount_cents: Optional[int] = Field(None, ge=1, le=100000000)  # None = full refund, max $1M
    reason: str = Field(..., min_length=1, max_length=1000)


class AdminCancelSubscriptionRequest(BaseModel):
    # v3.25: SUB-MEDIUM-1 - Field length limits
    user_id: str = Field(..., min_length=1, max_length=100)
    user_code: str = Field(..., min_length=1, max_length=50)  # Must match for verification
    subscription_id: str = Field(..., min_length=1, max_length=100)
    immediate: bool = False  # True = cancel now, False = cancel at period end
    reason: str = Field(..., min_length=1, max_length=1000)


class AdminDowngradeRequest(BaseModel):
    # v3.25: SUB-MEDIUM-1 - Field length limits
    user_id: str = Field(..., min_length=1, max_length=100)
    user_code: str = Field(..., min_length=1, max_length=50)  # For verification
    user_email: str = Field(..., min_length=1, max_length=255)  # For verification
    target_tier: str = Field(..., max_length=20)  # 'starter' | 'free'
    immediate: bool = False  # True = immediate, False = apply at period end
    reason: str = Field(..., min_length=1, max_length=1000)

    # v3.25: SUB-MEDIUM-2 - target_tier enum validation
    @field_validator("target_tier")
    @classmethod
    def validate_target_tier(cls, v: str) -> str:
        v_lower = v.lower()
        if v_lower not in VALID_TARGET_TIERS:
            raise ValueError(f"Invalid target_tier. Must be one of: {', '.join(VALID_TARGET_TIERS)}")
        return v_lower


# ==========================================
# Response Models (v3.28: SUB-MEDIUM-6)
# ==========================================

class RefundResponse(BaseModel):
    """Response model for refund operation."""
    status: str = "refunded"
    refund_id: str
    amount: int  # Amount in cents
    currency: str


class CancelSubscriptionResponse(BaseModel):
    """Response model for subscription cancellation."""
    status: str  # "canceled" or "cancel_scheduled"
    subscription_id: str
    cancel_at_period_end: bool
    current_period_end: int  # Unix timestamp


class DowngradeSubscriptionResponse(BaseModel):
    """Response model for subscription downgrade."""
    status: str  # "downgraded" or "downgrade_scheduled"
    from_tier: str
    to_tier: str
    subscription_id: Optional[str] = None  # None if downgrading to free without subscription


# ==========================================
# Subscription Management Endpoints
# ==========================================

@router.post("/refund", response_model=RefundResponse)
@limiter.limit("10/minute")
async def adm_refund(
    request: Request,
    req: AdminRefundRequest,
    admin: dict = Depends(require_admin)
) -> RefundResponse:
    """
    Admin refund operation (full or partial) with safety checks.

    v3.28: Refactored to use SubscriptionService (SUB-MEDIUM-1).
    """
    db = get_database_client()
    users_repo = SupabaseUserRepository(db)
    payment_repo = SupabasePaymentRepository(db)
    admin_repo = SupabaseAdminUsersRepository(db)

    service = SubscriptionService(users_repo, payment_repo, admin_repo)

    result = await service.process_refund(
        user_id=req.user_id,
        user_code=req.user_code,
        payment_intent_id=req.payment_intent_id,
        amount_cents=req.amount_cents,
        reason=req.reason,
        admin_id=admin["id"]
    )

    return RefundResponse(**result)


@router.post("/subscription/cancel", response_model=CancelSubscriptionResponse)
@limiter.limit("10/minute")
async def adm_cancel_subscription(
    request: Request,
    req: AdminCancelSubscriptionRequest,
    admin: dict = Depends(require_admin)
) -> CancelSubscriptionResponse:
    """
    Admin-initiated subscription cancellation.

    v3.28: Refactored to use SubscriptionService (SUB-MEDIUM-2).
    """
    db = get_database_client()
    users_repo = SupabaseUserRepository(db)
    payment_repo = SupabasePaymentRepository(db)
    admin_repo = SupabaseAdminUsersRepository(db)

    service = SubscriptionService(users_repo, payment_repo, admin_repo)

    result = await service.cancel_user_subscription(
        user_id=req.user_id,
        user_code=req.user_code,
        subscription_id=req.subscription_id,
        immediate=req.immediate,
        reason=req.reason,
        admin_id=admin["id"]
    )

    return CancelSubscriptionResponse(**result)


@router.post("/subscription/downgrade", response_model=DowngradeSubscriptionResponse)
@limiter.limit("10/minute")
async def adm_downgrade_subscription(
    request: Request,
    req: AdminDowngradeRequest,
    admin: dict = Depends(require_admin)
) -> DowngradeSubscriptionResponse:
    """
    Admin-assisted subscription downgrade.

    v3.28: Refactored to use SubscriptionService (SUB-MEDIUM-3/7).
    """
    db = get_database_client()
    users_repo = SupabaseUserRepository(db)
    payment_repo = SupabasePaymentRepository(db)
    admin_repo = SupabaseAdminUsersRepository(db)

    service = SubscriptionService(users_repo, payment_repo, admin_repo)

    result = await service.downgrade_user_subscription(
        user_id=req.user_id,
        user_code=req.user_code,
        user_email=req.user_email,
        target_tier=req.target_tier,
        immediate=req.immediate,
        reason=req.reason,
        admin_id=admin["id"]
    )

    return DowngradeSubscriptionResponse(**result)

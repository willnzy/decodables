"""
Admin Subscriptions Router - Subscription management endpoints for admins

@module api.admin.subscriptions
@version 3.29 (Container-based DI)

Changes in v3.29:
- SUB-ARCH-1: Migrated to Container-based dependency injection
- SUB-ARCH-2: Removed direct repository imports from API layer
- Architecture: API → Container → Service → Repository (Strict DIP)

Changes in v3.28:
- SUB-MEDIUM-1/2/3: Extracted business logic to SubscriptionService
- SUB-MEDIUM-5: Created SubscriptionRepository
- SUB-MEDIUM-6: Added Response Models (RefundResponse, etc.)
- SUB-MEDIUM-7: Split complex downgrade logic into smaller methods
- SUB-MEDIUM-8: Extracted common user_code validation to Service layer

Changes in v3.27:
- SUB-CRITICAL-1: Replaced direct stripe.Subscription.retrieve() with service wrapper
- SUB-CRITICAL-2: Replaced direct stripe.Subscription.modify() with service wrapper
- SUB-HIGH-1/2/3/5: Added timeout to all Stripe API calls

Changes in v3.25:
- SUB-MEDIUM-1: Added field length limits to request models
- SUB-MEDIUM-2: Added target_tier enum validation
- SUB-LOW-1: Limited Stripe error exposure

Endpoints:
- POST /api/admin/refund - Process refund
- POST /api/admin/subscription/cancel - Cancel subscription
- POST /api/admin/subscription/downgrade - Downgrade subscription
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field, field_validator

from infrastructure.rate_limiter import limiter
from dependencies import require_admin

# v3.29: Container-based DI
# WHY: API layer should not know about concrete repository implementations
from container import get_container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["admin-subscriptions-v2"])


# ==========================================
# Dependency Injection (v3.29: Container-based)
# ==========================================

async def get_subscription_service():
    """
    Get SubscriptionService from Container.

    WHY Container-based DI?
    1. Decouples API layer from infrastructure implementations
    2. Enables easy testing with mock services
    3. Centralizes dependency management
    4. Supports future provider switches
    """
    container = get_container()
    return await container.get_subscription_service()


# ==========================================
# Constants
# ==========================================

VALID_TARGET_TIERS = {"t1", "t2"}


# ==========================================
# Request Models
# ==========================================

class AdminRefundRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    user_code: str = Field(..., min_length=1, max_length=50)
    payment_intent_id: str = Field(..., min_length=1, max_length=100)
    amount_cents: Optional[int] = Field(None, ge=1, le=100000000)
    reason: str = Field(..., min_length=1, max_length=1000)


class AdminCancelSubscriptionRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    user_code: str = Field(..., min_length=1, max_length=50)
    subscription_id: str = Field(..., min_length=1, max_length=100)
    immediate: bool = False
    reason: str = Field(..., min_length=1, max_length=1000)


class AdminDowngradeRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    user_code: str = Field(..., min_length=1, max_length=50)
    user_email: str = Field(..., min_length=1, max_length=255)
    target_tier: str = Field(..., max_length=20)
    immediate: bool = False
    reason: str = Field(..., min_length=1, max_length=1000)

    @field_validator("target_tier")
    @classmethod
    def validate_target_tier(cls, v: str) -> str:
        v_lower = v.lower()
        if v_lower not in VALID_TARGET_TIERS:
            raise ValueError(f"Invalid target_tier. Must be one of: {', '.join(VALID_TARGET_TIERS)}")
        return v_lower


# ==========================================
# Response Models
# ==========================================

class RefundResponse(BaseModel):
    """Response model for refund operation."""
    status: str = "refunded"
    refund_id: str
    amount: int
    currency: str


class CancelSubscriptionResponse(BaseModel):
    """Response model for subscription cancellation."""
    status: str
    subscription_id: str
    cancel_at_period_end: bool
    current_period_end: int


class DowngradeSubscriptionResponse(BaseModel):
    """Response model for subscription downgrade."""
    status: str
    from_tier: str
    to_tier: str
    subscription_id: Optional[str] = None


# ==========================================
# Subscription Management Endpoints
# ==========================================

@router.post("/refund", response_model=RefundResponse)
@limiter.limit("10/minute")
async def adm_refund(
    request: Request,
    req: AdminRefundRequest,
    admin: dict = Depends(require_admin),
    service = Depends(get_subscription_service),
) -> RefundResponse:
    """
    Admin refund operation (full or partial) with safety checks.

    v3.29: Refactored to use Container-based SubscriptionService.
    """
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
    admin: dict = Depends(require_admin),
    service = Depends(get_subscription_service),
) -> CancelSubscriptionResponse:
    """
    Admin-initiated subscription cancellation.

    v3.29: Refactored to use Container-based SubscriptionService.
    """
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
    admin: dict = Depends(require_admin),
    service = Depends(get_subscription_service),
) -> DowngradeSubscriptionResponse:
    """
    Admin-assisted subscription downgrade.

    v3.29: Refactored to use Container-based SubscriptionService.
    """
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

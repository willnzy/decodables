"""
Billing API - Credit management endpoints using DDD handlers.

@module api.user.billing
@version 1.2.1

Changes in v1.2.1:
- B-HIGH-1-FIX: Fixed user_id validation - Clerk IDs are NOT UUID format
  - Clerk user IDs are text format like "user_2abc..." (prefix + 24-27 chars)
  - Changed from UUID regex to Clerk ID format validation

Changes in v1.2.0:
- B-P0-3: Removed /credits/deduct public endpoint (security risk)
- B-HIGH-1: Added UUID validation for user_id in AddCreditsRequest (WRONG - fixed in v1.2.1)
- B-HIGH-2: Removed balance exposure from /can-afford response
- B-HIGH-3: Sanitized error messages to prevent info leakage
- B-MEDIUM-1: Added rate limiting to all endpoints
- B-MEDIUM-2: Added audit logging for sensitive operations
- B-MEDIUM-3: Added operation whitelist validation
- B-LOW-2: Fixed TransactionHistoryResponse type annotation

Changes in v1.1.0:
- B-P0-1: /credits/add now requires admin permission
- B-P0-2: Fixed CreditTransaction.id field issue (use tx.created_at as fallback)
- B-H4: Removed balance exposure from error messages

Endpoints:
- GET /api/v2/user/billing/credits - Get user credits
- GET /api/v2/user/billing/transactions - Get transaction history
- GET /api/v2/user/billing/can-afford - Check if user can afford operation
- POST /api/v2/user/billing/credits/add - Add credits (admin only)
"""

import logging
import re
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

from dependencies import get_current_user, require_admin
from infrastructure.rate_limiter import limiter
from container import get_container

from application.queries.billing import (
    GetUserCreditsQuery,
    GetTransactionHistoryQuery,
    CheckCanAffordQuery,
)
from application.commands.billing import (
    AddCreditsCommand,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["user-billing-v2"])

# ==========================================
# Constants
# ==========================================

# v1.2.1: B-HIGH-1-FIX - Clerk user ID validation pattern
# Clerk user IDs are format: user_{base58_chars} where base58_chars is typically 24-27 chars
# Example: user_2NNEqL2nrIRdJ194ndJqAHwEfxC
CLERK_USER_ID_PATTERN = re.compile(r"^user_[a-zA-Z0-9]{20,30}$")

# v1.2.0: B-MEDIUM-3 - Valid operation names for cost lookup
VALID_OPERATIONS = {
    "image_generation",
    "image_generation_reference",
    "text_generation",
    "smart_scan",
    "pdf_export",
}


# ==========================================
# Response Models
# ==========================================

class CreditsResponse(BaseModel):
    """User credits response."""
    monthly_credits: int
    permanent_credits: int
    total_credits: int
    tier: str


class TransactionResponse(BaseModel):
    """Transaction item response."""
    id: str
    amount: int
    balance_after: int
    tx_type: str
    description: Optional[str] = None
    created_at: datetime


class TransactionHistoryResponse(BaseModel):
    """Transaction history response."""
    # v1.2.0: B-LOW-2 - Fixed type annotation
    transactions: List[dict]
    total_count: int


class AffordabilityResponse(BaseModel):
    """Affordability check response."""
    can_afford: bool
    # v1.2.0: B-HIGH-2 - Removed current_balance to reduce info exposure
    required_amount: int


# ==========================================
# Request Models
# ==========================================

# v1.2.0: B-P0-3 - Removed DeductCreditsRequest (endpoint removed for security)


class AddCreditsRequest(BaseModel):
    """Request to add credits (admin only)."""
    # v1.2.1: B-HIGH-1-FIX - Changed to Clerk user ID format validation
    # Clerk IDs are like "user_2NNEqL2nrIRdJ194ndJqAHwEfxC" (25-35 chars total)
    user_id: str = Field(..., description="Target user ID to add credits to", min_length=25, max_length=35)
    amount: int = Field(..., gt=0, le=10000)
    credit_type: str = Field(..., pattern="^(monthly|permanent)$")
    reason: str = Field(..., min_length=1, max_length=200)  # v1.2.0: B-LOW-1 - Increased max_length

    @field_validator("user_id")
    @classmethod
    def validate_user_id_format(cls, v: str) -> str:
        """Validate user_id is a valid Clerk user ID format."""
        if not CLERK_USER_ID_PATTERN.match(v):
            raise ValueError("user_id must be a valid Clerk user ID format (e.g., user_2abc...)")
        return v


# ==========================================
# Endpoints
# ==========================================

@router.get("/credits", response_model=CreditsResponse)
@limiter.limit("60/minute")  # v1.2.0: B-MEDIUM-1 - Rate limiting
async def get_credits(request: Request, user: dict = Depends(get_current_user)):
    """
    Get current user's credit balance.

    Returns:
        CreditsResponse with monthly, permanent, and total credits
    """
    container = get_container()
    handler = container.get_user_credits_handler

    query = GetUserCreditsQuery(user_id=user["id"])
    result = await handler.handle(query)

    if not result.success:
        # v1.2.0: B-HIGH-3 - Sanitized error message
        logger.error(f"[Billing] Failed to get credits for user {user['id']}: {result.error}")
        raise HTTPException(500, "Failed to retrieve credit balance")

    return CreditsResponse(
        monthly_credits=result.monthly_credits,
        permanent_credits=result.permanent_credits,
        total_credits=result.total_credits,
        tier=result.tier,
    )


@router.get("/transactions", response_model=TransactionHistoryResponse)
@limiter.limit("30/minute")  # v1.2.0: B-MEDIUM-1 - Rate limiting
async def get_transactions(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tx_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user: dict = Depends(get_current_user),
):
    """
    Get user's transaction history.

    Args:
        limit: Maximum items to return (default: 50)
        offset: Number of items to skip (default: 0)
        tx_type: Filter by transaction type
        start_date: Filter by start date
        end_date: Filter by end date

    Returns:
        TransactionHistoryResponse with transactions list
    """
    container = get_container()
    handler = container.get_transaction_history_handler

    query = GetTransactionHistoryQuery(
        user_id=user["id"],
        limit=limit,
        offset=offset,
        tx_type=tx_type,
        start_date=start_date,
        end_date=end_date,
    )
    result = await handler.handle(query)

    if not result.success:
        # v1.2.0: B-HIGH-3 - Sanitized error message
        logger.error(f"[Billing] Failed to get transactions for user {user['id']}: {result.error}")
        raise HTTPException(500, "Failed to retrieve transaction history")

    # v1.1.0: B-P0-2 fix - use idempotency_key or created_at as fallback for id
    return TransactionHistoryResponse(
        transactions=[
            {
                "id": getattr(tx, 'id', None) or tx.idempotency_key or str(tx.created_at.timestamp()),
                "amount": tx.amount,
                "balance_after": tx.balance_after.total if tx.balance_after else 0,
                "tx_type": tx.tx_type.value,
                "description": tx.description,
                "created_at": tx.created_at,
            }
            for tx in result.transactions
        ],
        total_count=result.total_count,
    )


@router.get("/can-afford", response_model=AffordabilityResponse)
@limiter.limit("60/minute")  # v1.2.0: B-MEDIUM-1 - Rate limiting
async def check_can_afford(
    request: Request,
    amount: Optional[int] = Query(None, ge=0, le=100000),  # v1.2.0: Added max limit
    operation: Optional[str] = Query(None, max_length=50),  # v1.2.0: Added max_length
    user: dict = Depends(get_current_user),
):
    """
    Check if user can afford an operation or amount.

    Args:
        amount: Credit amount to check (max: 100000)
        operation: Operation name (e.g., "image_generation")

    Returns:
        AffordabilityResponse with can_afford flag
    """
    if amount is None and operation is None:
        raise HTTPException(400, "Either amount or operation must be specified")

    # v1.2.0: B-MEDIUM-3 - Validate operation against whitelist
    if operation and operation not in VALID_OPERATIONS:
        raise HTTPException(400, "Invalid operation name")

    container = get_container()
    handler = container.get_user_credits_handler

    # Get current credits
    credits_query = GetUserCreditsQuery(user_id=user["id"])
    credits_result = await handler.handle(credits_query)

    if not credits_result.success:
        # v1.2.0: B-HIGH-3 - Sanitized error message
        logger.error(f"[Billing] Failed to check affordability for user {user['id']}: {credits_result.error}")
        raise HTTPException(500, "Failed to check affordability")

    # Calculate required amount
    if operation:
        # Use billing service to get operation cost
        billing_service = get_container().billing_service
        required = billing_service.get_operation_cost(operation)
    else:
        required = amount

    can_afford = credits_result.total_credits >= required

    # v1.2.0: B-HIGH-2 - Removed current_balance from response
    return AffordabilityResponse(
        can_afford=can_afford,
        required_amount=required,
    )


# ==========================================
# Admin Endpoints
# ==========================================

# v1.2.0: B-P0-3 - Removed /credits/deduct endpoint
# Credit deductions should ONLY happen through domain services internally,
# not through a public API endpoint. This prevents potential abuse scenarios.


@router.post("/credits/add")
@limiter.limit("10/minute")  # v1.2.0: B-MEDIUM-1 - Rate limiting (admin)
async def add_credits(
    request: Request,
    req: AddCreditsRequest,
    admin: dict = Depends(require_admin),  # v1.1.0: B-P0-1 fix - require admin
):
    """
    Add credits to user account.

    Note: This endpoint requires ADMIN permissions.
    Only administrators can add credits to user accounts.

    Args:
        req: Add credits request with target user_id, amount and type

    Returns:
        Updated credit balance
    """
    container = get_container()
    handler = container.add_credits_handler

    # Map credit_type to CreditBucket and TransactionType
    from domains.billing.value_objects import CreditBucket, TransactionType
    bucket = CreditBucket.MONTHLY if req.credit_type == "monthly" else CreditBucket.PERMANENT
    tx_type = TransactionType.SUBSCRIPTION_GRANT if req.credit_type == "monthly" else TransactionType.ADMIN_ADJUSTMENT

    command = AddCreditsCommand(
        user_id=req.user_id,  # v1.1.0: Target user from request, not current user
        amount=req.amount,
        bucket=bucket,
        tx_type=tx_type,
        description=f"[Admin: {admin['id'][:8]}] {req.reason}",
    )
    result = await handler.handle(command)

    if not result.success:
        # v1.2.0: B-HIGH-3 - Sanitized error message + audit log
        logger.error(f"[Admin] Failed to add credits: admin={admin['id']} target={req.user_id} error={result.error}")
        raise HTTPException(400, "Failed to add credits")

    # v1.2.0: B-MEDIUM-2 - Enhanced audit logging
    logger.info(
        f"[Admin] CREDITS_ADDED admin={admin['id']} target={req.user_id} "
        f"amount={req.amount} type={req.credit_type} reason={req.reason}"
    )

    return {
        "success": True,
        "target_user_id": req.user_id,
        "amount_added": result.transaction.amount if result.transaction else 0,
        "new_balance": result.new_balance,
    }

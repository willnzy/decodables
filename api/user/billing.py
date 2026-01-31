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

from domains.identity.aggregates.user_profile import UserProfile
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
async def get_credits(request: Request, user: UserProfile = Depends(get_current_user)):
    """
    Get current user's credit balance and tier information.

    Retrieves the user's current credit balance breakdown, including monthly
    recurring credits and permanent (purchased) credits. Credits are used for
    AI-powered features like image generation, text generation, and Smart Scan.

    v1.2.0: Added rate limiting (B-MEDIUM-1) and sanitized errors (B-HIGH-3).

    Returns:
        CreditsResponse containing:
            - monthly_credits: Credits from subscription (reset monthly)
                t1 (Free): 0/month
                t2 (Starter): 200/month
                t3 (Pro): 500/month
            - permanent_credits: Purchased credits (never expire)
                From credit pack purchases (100/$2.99, 500/$13.49, 2000/$48)
            - total_credits: Sum of monthly + permanent credits
                Used for affordability checks and feature access
            - tier: User's current tier (t1/t2/t3)

    Raises:
        401: Unauthorized (not authenticated)
        429: Rate limit exceeded (max 60 requests per minute)
        500: Database error or service unavailable

    Security:
        - Authentication required
        - Rate limit: 60 requests per minute
        - Error messages sanitized (no internal details exposed)
        - User can only access their own credits

    Usage:
        Used by frontend to:
        - Display credit balance in UI
        - Check if user can afford AI operations
        - Show appropriate upgrade prompts

    Example:
        GET /api/v2/user/billing/credits

        Response:
        {
            "monthly_credits": 200,
            "permanent_credits": 150,
            "total_credits": 350,
            "tier": "t2"
        }
    """
    container = get_container()
    handler = await container.get_user_credits_handler()

    query = GetUserCreditsQuery(user_id=user.user_id)
    result = await handler.handle(query)

    if not result.success:
        # v1.2.0: B-HIGH-3 - Sanitized error message
        logger.error(f"[Billing] Failed to get credits for user {user.user_id}: {result.error}")
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
    limit: int = Query(50, ge=1, le=100, description="Maximum number of transactions to return (1-100, default: 50)"),
    offset: int = Query(0, ge=0, description="Number of transactions to skip for pagination"),
    tx_type: Optional[str] = Query(None, description="Filter by transaction type (e.g., 'credit_purchase', 'ai_generation')"),
    start_date: Optional[datetime] = Query(None, description="Filter transactions from this date onwards (ISO 8601 format)"),
    end_date: Optional[datetime] = Query(None, description="Filter transactions up to this date (ISO 8601 format)"),
    user: UserProfile = Depends(get_current_user),
):
    """
    Get user's transaction history with optional filtering and pagination.

    Retrieves a chronological list of all credit-related transactions for the user,
    including purchases, refunds, AI operation charges, and subscription renewals.
    Useful for billing transparency, dispute resolution, and usage tracking.

    v1.2.0: Added rate limiting (B-MEDIUM-1) and sanitized errors (B-HIGH-3).
    v1.1.0: Fixed ID fallback (B-P0-2) - uses idempotency_key when id is null.

    Args:
        limit: Maximum number of transactions to return (default: 50, max: 100)
            Pagination support for large transaction histories
        offset: Skip first N transactions (default: 0)
            Used with limit for pagination
        tx_type: Optional filter by transaction type
            Common values:
                - "credit_purchase": Purchased credit packs
                - "subscription_renewal": Monthly tier credit grant
                - "ai_image_generation": Used 5 credits for AI image
                - "ai_text_generation": Used 1 credit for AI text
                - "smart_scan": Used 10 credits for Smart Scan
                - "refund": Credit refund from support
        start_date: Filter transactions from this date (inclusive)
            ISO 8601 format: "2026-01-11T00:00:00Z"
        end_date: Filter transactions to this date (inclusive)
            ISO 8601 format: "2026-01-11T23:59:59Z"

    Returns:
        TransactionHistoryResponse containing:
            - transactions: List of transaction objects including:
                - id: Transaction ID (UUID or fallback to idempotency_key)
                - amount: Credit amount (positive for credits added, negative for spent)
                - balance_after: User's credit balance after this transaction
                - tx_type: Transaction type identifier
                - description: Human-readable description
                - created_at: Transaction timestamp
                - metadata: Additional transaction details (JSON)
            - total: Total number of transactions (respecting filters)
            - limit: Limit applied
            - offset: Offset applied
            - has_more: Whether more transactions exist (for pagination)

    Raises:
        400: Invalid date format, invalid limit/offset, or tx_type validation error
        401: Unauthorized (not authenticated)
        429: Rate limit exceeded (max 30 requests per minute)
        500: Database error or service unavailable

    Security:
        - Authentication required
        - Rate limit: 30 requests per minute
        - User can only access their own transactions
        - Error messages sanitized (no internal details exposed)
        - Sensitive payment data (card numbers, CVV) never included

    Example:
        GET /api/v2/user/billing/transactions?limit=10&tx_type=ai_image_generation&start_date=2026-01-01T00:00:00Z

        Response:
        {
            "transactions": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "amount": -5,
                    "balance_after": 345,
                    "tx_type": "ai_image_generation",
                    "description": "AI Image Generation - Page 1",
                    "created_at": "2026-01-11T10:30:00Z",
                    "metadata": {"project_id": "abc123", "prompt": "..."}
                },
                {
                    "id": "660e8400-e29b-41d4-a716-446655440001",
                    "amount": 100,
                    "balance_after": 350,
                    "tx_type": "credit_purchase",
                    "description": "Credit Pack Purchase - 100 credits",
                    "created_at": "2026-01-10T15:20:00Z",
                    "metadata": {"stripe_payment_id": "pi_..."}
                }
            ],
            "total": 2,
            "limit": 10,
            "offset": 0,
            "has_more": false
        }
    """
    container = get_container()
    handler = await container.get_transaction_history_handler()

    query = GetTransactionHistoryQuery(
        user_id=user.user_id,
        limit=limit,
        offset=offset,
        tx_type=tx_type,
        start_date=start_date,
        end_date=end_date,
    )
    result = await handler.handle(query)

    if not result.success:
        # v1.2.0: B-HIGH-3 - Sanitized error message
        logger.error(f"[Billing] Failed to get transactions for user {user.user_id}: {result.error}")
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
    user: UserProfile = Depends(get_current_user),
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
    handler = await container.get_user_credits_handler()

    # Get current credits
    credits_query = GetUserCreditsQuery(user_id=user.user_id)
    credits_result = await handler.handle(credits_query)

    if not credits_result.success:
        # v1.2.0: B-HIGH-3 - Sanitized error message
        logger.error(f"[Billing] Failed to check affordability for user {user.user_id}: {credits_result.error}")
        raise HTTPException(500, "Failed to check affordability")

    # Calculate required amount
    if operation:
        # WS-B2: Fix double bug — (1) async get_billing_service (2) await async method
        billing_service = await get_container().get_billing_service()
        required = await billing_service.get_operation_cost(operation)
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
    handler = await container.get_add_credits_handler()

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

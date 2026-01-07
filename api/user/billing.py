"""
Billing API - Credit management endpoints using DDD handlers.

@module api.user.billing
@version 1.0.0

Endpoints:
- GET /api/v2/user/billing/credits - Get user credits
- GET /api/v2/user/billing/transactions - Get transaction history
- GET /api/v2/user/billing/can-afford - Check if user can afford operation
- POST /api/v2/user/billing/credits/deduct - Deduct credits (internal)
- POST /api/v2/user/billing/credits/add - Add credits (internal)
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from dependencies import get_current_user
from container import get_container

from application.queries.billing import (
    GetUserCreditsQuery,
    GetTransactionHistoryQuery,
    CheckCanAffordQuery,
)
from application.commands.billing import (
    DeductCreditsCommand,
    AddCreditsCommand,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["user-billing-v2"])


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
    transactions: list
    total_count: int


class AffordabilityResponse(BaseModel):
    """Affordability check response."""
    can_afford: bool
    current_balance: int
    required_amount: int


# ==========================================
# Request Models
# ==========================================

class DeductCreditsRequest(BaseModel):
    """Request to deduct credits."""
    amount: int = Field(..., gt=0, le=1000)
    operation: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None


class AddCreditsRequest(BaseModel):
    """Request to add credits."""
    amount: int = Field(..., gt=0, le=10000)
    credit_type: str = Field(..., pattern="^(monthly|permanent)$")
    reason: str = Field(..., min_length=1, max_length=100)


# ==========================================
# Endpoints
# ==========================================

@router.get("/credits", response_model=CreditsResponse)
async def get_credits(user: dict = Depends(get_current_user)):
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
        raise HTTPException(500, result.error or "Failed to get credits")

    return CreditsResponse(
        monthly_credits=result.monthly_credits,
        permanent_credits=result.permanent_credits,
        total_credits=result.total_credits,
        tier=result.tier,
    )


@router.get("/transactions", response_model=TransactionHistoryResponse)
async def get_transactions(
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
        raise HTTPException(500, result.error or "Failed to get transactions")

    return TransactionHistoryResponse(
        transactions=[
            {
                "id": tx.id,
                "amount": tx.amount,
                "balance_after": tx.balance_after,
                "tx_type": tx.tx_type.value,
                "description": tx.description,
                "created_at": tx.created_at,
            }
            for tx in result.transactions
        ],
        total_count=result.total_count,
    )


@router.get("/can-afford", response_model=AffordabilityResponse)
async def check_can_afford(
    amount: Optional[int] = Query(None, ge=0),
    operation: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """
    Check if user can afford an operation or amount.

    Args:
        amount: Credit amount to check
        operation: Operation name (e.g., "image_generation")

    Returns:
        AffordabilityResponse with can_afford flag
    """
    if amount is None and operation is None:
        raise HTTPException(400, "Either amount or operation must be specified")

    container = get_container()
    handler = container.get_user_credits_handler  # Use credits handler for now

    # Get current credits
    credits_query = GetUserCreditsQuery(user_id=user["id"])
    credits_result = await handler.handle(credits_query)

    if not credits_result.success:
        raise HTTPException(500, "Failed to check credits")

    # Calculate required amount
    if operation:
        # Use billing service to get operation cost
        billing_service = get_container().billing_service
        cost = billing_service.get_operation_cost(operation)
        required = cost.amount
    else:
        required = amount

    can_afford = credits_result.total_credits >= required

    return AffordabilityResponse(
        can_afford=can_afford,
        current_balance=credits_result.total_credits,
        required_amount=required,
    )


# ==========================================
# Internal Endpoints (for service-to-service)
# ==========================================

@router.post("/credits/deduct")
async def deduct_credits(
    req: DeductCreditsRequest,
    user: dict = Depends(get_current_user),
):
    """
    Deduct credits for an operation.

    Note: This endpoint is primarily for internal use.
    Most credit deductions happen automatically via domain services.

    Args:
        req: Deduction request with amount and operation

    Returns:
        Updated credit balance
    """
    container = get_container()
    handler = container.deduct_credits_handler

    command = DeductCreditsCommand(
        user_id=user["id"],
        amount=req.amount,
        operation=req.operation,
        description=req.description,
    )
    result = await handler.handle(command)

    if not result.success:
        if "insufficient" in (result.error or "").lower():
            raise HTTPException(402, result.error)
        raise HTTPException(400, result.error or "Failed to deduct credits")

    return {
        "success": True,
        "amount_deducted": result.amount_deducted,
        "new_balance": result.new_balance,
    }


@router.post("/credits/add")
async def add_credits(
    req: AddCreditsRequest,
    user: dict = Depends(get_current_user),
):
    """
    Add credits to user account.

    Note: This endpoint requires elevated permissions in production.
    Currently available for testing purposes.

    Args:
        req: Add credits request with amount and type

    Returns:
        Updated credit balance
    """
    # TODO: Add admin/internal authorization check
    container = get_container()
    handler = container.add_credits_handler

    command = AddCreditsCommand(
        user_id=user["id"],
        amount=req.amount,
        credit_type=req.credit_type,
        reason=req.reason,
    )
    result = await handler.handle(command)

    if not result.success:
        raise HTTPException(400, result.error or "Failed to add credits")

    return {
        "success": True,
        "amount_added": result.amount_added,
        "new_balance": result.new_balance,
    }

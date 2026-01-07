"""
Credits API - User-facing credit endpoints.

@module api.credits_api
@version 1.0.0

This is a simplified user-facing API that wraps billing functionality.
Provides a cleaner interface for frontend consumption.

Endpoints:
- GET /api/v2/credits - Get user credits (simplified)
- GET /api/v2/credits/history - Get credit history
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from dependencies import get_current_user
from container import get_container

from application.queries.billing import (
    GetUserCreditsQuery,
    GetTransactionHistoryQuery,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/credits", tags=["credits-v2"])


# ==========================================
# Response Models
# ==========================================

class SimpleCreditsResponse(BaseModel):
    """Simplified credits response for frontend."""
    total: int
    monthly: int
    permanent: int
    is_member: bool


class HistoryItem(BaseModel):
    """Credit history item."""
    id: str
    amount: int
    type: str
    description: Optional[str]
    date: datetime


class CreditsHistoryResponse(BaseModel):
    """Credit history response."""
    items: List[HistoryItem]
    total: int
    page: int


# ==========================================
# Endpoints
# ==========================================

@router.get("", response_model=SimpleCreditsResponse)
async def get_my_credits(user: dict = Depends(get_current_user)):
    """
    Get current user's credit balance (simplified).

    Returns:
        SimpleCreditsResponse with total, monthly, permanent credits
    """
    container = get_container()
    handler = container.get_user_credits_handler

    query = GetUserCreditsQuery(user_id=user["id"])
    result = await handler.handle(query)

    if not result.success:
        logger.error(f"Failed to get credits for user {user['id']}: {result.error}")
        raise HTTPException(500, "Failed to get credits")

    tier = result.tier.lower() if result.tier else "free"
    is_member = tier in ["starter", "pro"]

    return SimpleCreditsResponse(
        total=result.total_credits,
        monthly=result.monthly_credits,
        permanent=result.permanent_credits,
        is_member=is_member,
    )


@router.get("/history", response_model=CreditsHistoryResponse)
async def get_credit_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    """
    Get credit transaction history.

    Args:
        page: Page number (default: 1)
        limit: Items per page (default: 20)

    Returns:
        CreditsHistoryResponse with paginated history
    """
    container = get_container()
    handler = container.get_transaction_history_handler

    offset = (page - 1) * limit

    query = GetTransactionHistoryQuery(
        user_id=user["id"],
        limit=limit,
        offset=offset,
    )
    result = await handler.handle(query)

    if not result.success:
        logger.error(f"Failed to get history for user {user['id']}: {result.error}")
        raise HTTPException(500, "Failed to get credit history")

    items = [
        HistoryItem(
            id=tx.id,
            amount=tx.amount,
            type=tx.tx_type.value,
            description=tx.description,
            date=tx.created_at,
        )
        for tx in result.transactions
    ]

    return CreditsHistoryResponse(
        items=items,
        total=result.total_count,
        page=page,
    )

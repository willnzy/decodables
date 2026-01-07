"""
Platform API - Feature flags and experiments.

@module api.platform_api
@version 1.0.0

Endpoints:
- GET /api/v2/platform/flags/{key} - Evaluate feature flag
- GET /api/v2/platform/experiments/{key}/variant - Get experiment variant
- POST /api/v2/platform/experiments/{key}/assign - Assign variant
"""

import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from dependencies import get_current_user
from container import get_container

from application.queries.platform import (
    EvaluateFeatureFlagQuery,
    GetExperimentVariantQuery,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/platform", tags=["platform-v2"])


# ==========================================
# Response Models
# ==========================================

class FeatureFlagResponse(BaseModel):
    """Feature flag evaluation response."""
    key: str
    enabled: bool
    variant: Optional[str] = None


class ExperimentVariantResponse(BaseModel):
    """Experiment variant response."""
    experiment_key: str
    variant: Optional[str] = None
    assigned: bool = False
    reason: Optional[str] = None


class ExperimentAssignRequest(BaseModel):
    """Request to assign experiment variant."""
    user_identifier: str
    identifier_type: str = "user"
    context: Optional[Dict[str, Any]] = None


# ==========================================
# Feature Flags Endpoints
# ==========================================

@router.get("/flags/{flag_key}")
async def evaluate_flag(
    flag_key: str,
    user: dict = Depends(get_current_user),
) -> FeatureFlagResponse:
    """
    Evaluate a feature flag for the current user.

    Args:
        flag_key: Feature flag key

    Returns:
        FeatureFlagResponse with enabled status
    """
    container = get_container()
    handler = container.evaluate_feature_flag_handler

    query = EvaluateFeatureFlagQuery(
        flag_key=flag_key,
        user_id=user["id"],
        user_tier=user.get("tier", "free"),
    )

    result = await handler.handle(query)

    if not result.success:
        # Return disabled for unknown flags
        return FeatureFlagResponse(
            key=flag_key,
            enabled=False,
        )

    return FeatureFlagResponse(
        key=flag_key,
        enabled=result.enabled,
        variant=result.variant,
    )


# ==========================================
# Experiments Endpoints
# ==========================================

@router.get("/experiments/{experiment_key}/variant")
async def get_variant(
    experiment_key: str,
    user: dict = Depends(get_current_user),
) -> ExperimentVariantResponse:
    """
    Get experiment variant for the current user.

    Args:
        experiment_key: Experiment key

    Returns:
        ExperimentVariantResponse with variant assignment
    """
    container = get_container()
    handler = container.get_experiment_variant_handler

    query = GetExperimentVariantQuery(
        experiment_key=experiment_key,
        user_id=user["id"],
    )

    result = await handler.handle(query)

    if not result.success:
        return ExperimentVariantResponse(
            experiment_key=experiment_key,
            assigned=False,
            reason=result.error or "Experiment not found or not running",
        )

    return ExperimentVariantResponse(
        experiment_key=experiment_key,
        variant=result.variant,
        assigned=result.variant is not None,
    )


@router.post("/experiments/{experiment_key}/assign")
async def assign_variant(
    experiment_key: str,
    req: ExperimentAssignRequest,
) -> ExperimentVariantResponse:
    """
    Assign experiment variant to a user/visitor.

    This is a public endpoint for visitor assignment.
    Uses deterministic hashing for consistent assignment.

    Args:
        experiment_key: Experiment key
        req: Assignment request with user identifier

    Returns:
        ExperimentVariantResponse with assigned variant
    """
    container = get_container()
    platform_service = container.platform_service

    try:
        variant = await platform_service.assign_experiment_variant(
            experiment_key=experiment_key,
            user_identifier=req.user_identifier,
            identifier_type=req.identifier_type,
            context=req.context,
        )

        if variant is None:
            return ExperimentVariantResponse(
                experiment_key=experiment_key,
                assigned=False,
                reason="Not eligible or experiment not running",
            )

        return ExperimentVariantResponse(
            experiment_key=experiment_key,
            variant=variant,
            assigned=True,
        )

    except Exception as e:
        logger.error(f"Failed to assign variant for {experiment_key}: {e}")
        return ExperimentVariantResponse(
            experiment_key=experiment_key,
            assigned=False,
            reason="Assignment failed",
        )

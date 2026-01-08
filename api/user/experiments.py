"""Experiments API - A/B testing endpoints (v2).

@module api.user.experiments
@version 2.1.0

Endpoints:
- POST /api/v2/user/experiments/{key}/assign - Get variant assignment
- POST /api/v2/user/experiments/{key}/exposure - Track exposure
- POST /api/v2/user/experiments/{key}/conversion - Track conversion
- GET /api/v2/user/experiments/user/{identifier} - Get user experiments

Changes in v2.1.0:
- Fixed parameter mismatch between API and Service layer
- Aligned API request models with Service function signatures
"""

from typing import Optional, Dict, Any

from fastapi import APIRouter
from pydantic import BaseModel

from domains.platform import experiments as experiment_service

router = APIRouter(prefix="/experiments", tags=["experiments"])


# ==========================================
# Request Models
# ==========================================

class AssignmentRequest(BaseModel):
    """Request model for variant assignment.

    Attributes:
        user_identifier: User ID or anonymous ID (e.g., "user_123", "anon_abc")
        user_properties: Optional user properties for targeting (e.g., {"tier": "pro"})
    """
    user_identifier: str
    user_properties: Optional[Dict[str, Any]] = None


class ExposureRequest(BaseModel):
    """Request model for tracking exposure.

    Attributes:
        user_identifier: User ID or anonymous ID
        variant_key: Assigned variant key (e.g., "control", "variant_a")
        context: Optional context info (e.g., {"page": "home"})
    """
    user_identifier: str
    variant_key: str
    context: Optional[Dict[str, Any]] = None


class ConversionRequest(BaseModel):
    """Request model for tracking conversion.

    Attributes:
        user_identifier: User ID or anonymous ID
        metric_key: Metric being tracked (e.g., "signup", "purchase", "primary")
        value: Metric value (default: 1.0, can be revenue amount)
        metadata: Optional metadata (e.g., {"order_id": "ord_123"})
    """
    user_identifier: str
    metric_key: str = "primary"
    value: Optional[float] = 1.0
    metadata: Optional[Dict[str, Any]] = None


# ==========================================
# Public Endpoints
# ==========================================

@router.post("/{experiment_key}/assign")
def assign_variant(experiment_key: str, req: AssignmentRequest):
    """
    Assign experiment variant to user.

    Uses deterministic hashing for consistent assignment.
    Same user always gets the same variant.
    """
    variant = experiment_service.assign_variant(
        experiment_key=experiment_key,
        user_identifier=req.user_identifier,
        user_properties=req.user_properties,
    )

    if variant is None:
        return {
            "variant": None,
            "experiment_key": experiment_key,
            "assigned": False,
            "reason": "Not eligible or experiment not running"
        }

    return {
        "variant": variant,
        "experiment_key": experiment_key,
        "assigned": True
    }


@router.post("/{experiment_key}/exposure")
def track_exposure(experiment_key: str, req: ExposureRequest):
    """
    Track experiment exposure event.

    Call this when user actually sees the variant (not just assigned).
    Deduplicates within 1 hour window.
    """
    success = experiment_service.track_exposure(
        experiment_key=experiment_key,
        user_identifier=req.user_identifier,
        variant_key=req.variant_key,
        context=req.context,
    )

    return {"success": success}


@router.post("/{experiment_key}/conversion")
def track_conversion(experiment_key: str, req: ConversionRequest):
    """
    Track experiment conversion event.

    Call this when user completes a conversion action.
    Automatically looks up user's assigned variant.
    """
    success = experiment_service.track_conversion(
        experiment_key=experiment_key,
        user_identifier=req.user_identifier,
        metric_key=req.metric_key,
        value=req.value or 1.0,
        metadata=req.metadata,
    )

    return {"success": success}


@router.get("/user/{user_identifier}")
def get_user_experiments(user_identifier: str):
    """
    Get all experiments for a user.

    Returns list of experiment assignments with variant info.
    """
    experiments = experiment_service.get_user_experiments(user_identifier)
    return {"experiments": experiments}

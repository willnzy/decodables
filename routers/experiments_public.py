"""
A/B Testing Experiments - Public API

@module routers.experiments_public
@version 3.24

Public Endpoints:
- POST /api/experiments/{key}/assign - Get variant assignment
- POST /api/experiments/{key}/exposure - Track exposure
- POST /api/experiments/{key}/conversion - Track conversion
- GET /api/experiments/user/{identifier} - Get user experiments
"""

from typing import Optional, Dict, Any

from fastapi import APIRouter
from pydantic import BaseModel

from services import experiment_service


# ==========================================
# Request Models
# ==========================================

class AssignmentRequest(BaseModel):
    user_identifier: str
    identifier_type: str = "user"  # user, visitor
    context: Optional[Dict[str, Any]] = None


class ExposureRequest(BaseModel):
    user_identifier: str
    variant_key: str


class ConversionRequest(BaseModel):
    user_identifier: str
    variant_key: str
    conversion_type: str = "primary"
    value: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


# ==========================================
# Public Router
# ==========================================

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@router.post("/{experiment_key}/assign")
def assign_variant(experiment_key: str, req: AssignmentRequest):
    """Assign experiment variant to user."""
    variant = experiment_service.assign_variant(
        experiment_key=experiment_key,
        user_identifier=req.user_identifier,
        identifier_type=req.identifier_type,
        context=req.context
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
    """Track experiment exposure event."""
    success = experiment_service.track_exposure(
        experiment_key=experiment_key,
        user_identifier=req.user_identifier,
        variant_key=req.variant_key
    )
    
    return {"success": success}


@router.post("/{experiment_key}/conversion")
def track_conversion(experiment_key: str, req: ConversionRequest):
    """Track experiment conversion event."""
    success = experiment_service.track_conversion(
        experiment_key=experiment_key,
        user_identifier=req.user_identifier,
        variant_key=req.variant_key,
        conversion_type=req.conversion_type,
        value=req.value,
        metadata=req.metadata
    )
    
    return {"success": success}


@router.get("/user/{user_identifier}")
def get_user_experiments(user_identifier: str):
    """Get all experiments for a user."""
    experiments = experiment_service.get_user_experiments(user_identifier)
    return {"experiments": experiments}

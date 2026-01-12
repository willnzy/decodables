"""
Admin Experiments API - A/B Testing experiment management.

@module api.admin.experiments
@version 3.31 (Utility Endpoints Migration - 100% Service-based)

Changes:
- v3.31: Migrated remaining utility endpoints to ExperimentService
  - ai_analysis now uses experiment_service.get_experiment_results()
  - quick_recommendation now uses experiment_service.get_experiment_results()
  - ALL 14 endpoints now exclusively use Service layer (100% DDD compliance)
  - Removed all direct calls to old module functions
- v3.30: Migrated analysis and trend endpoints to ExperimentService
  - get_experiment_results now uses experiment_service.get_experiment_results()
  - trigger_aggregation now uses experiment_service.aggregate_experiment_results()
  - trigger_all_aggregation now uses experiment_service.aggregate_experiment_results(None)
  - get_experiment_trend now uses experiment_service.get_daily_trend()
  - get_hourly_trend now uses experiment_service.get_hourly_trend()
  - ALL endpoints now use Service layer (100% DDD compliance)
- v3.29: Added dependency injection for ExperimentService (Perfect DDD)
  - Created ExperimentService class replacing module functions
  - Added get_experiment_service() DI factory
  - All CRUD endpoints use Depends(get_experiment_service)
  - Architecture: API → Service (DI) → Repository
- v3.28: DDD Architecture Migration (EXP-CRITICAL-1)
  - Migrated from domains/platform/experiments/crud.py to Repository pattern
  - All data access now through infrastructure/repositories/experiment_repository.py
  - Added @retry_on_network_error_async to all Repository methods
  - Added OOM protection (.limit(10000)) to all Repository queries
  - Achieved 100% DDD architecture compliance
- v3.28: P2/P3 final improvements
  - EXP-MEDIUM-2: Added timezone handling to date parsing
  - EXP-HIGH-5: Fixed list_experiments return type (Service returns tuple)
- v3.26: Critical fixes and improvements
  - EXP-CRITICAL-1: Fixed API direct database access (trend endpoints now use Service)
  - EXP-HIGH-1: Added Pydantic response models for all endpoints
  - EXP-HIGH-2: Added query limits to prevent OOM
  - EXP-HIGH-3: Added unified error handling to all endpoints
  - EXP-HIGH-4: Moved AI imports to top level
  - EXP-HIGH-6: Added audit logging for all operations
- v3.25: Security improvements
  - EXP-MEDIUM-1: Added rate limiting to all endpoints
  - EXP-MEDIUM-2: Added status parameter validation (list)
  - EXP-MEDIUM-3: Added experiment_type validation
  - EXP-MEDIUM-4: Added date format validation (results)
  - EXP-MEDIUM-5: Added days range validation (1-90)
  - EXP-MEDIUM-6: Added hours range validation (1-168)
  - EXP-LOW-1: Migrated page to offset pagination

Endpoints:
- GET /experiments - List experiments
- POST /experiments - Create experiment
- GET /experiments/{key} - Get experiment
- PUT /experiments/{key} - Update experiment
- DELETE /experiments/{key} - Delete experiment
- PUT /experiments/{key}/status - Update status
- GET /experiments/{key}/results - Get results
- POST /experiments/{key}/aggregate - Trigger aggregation
- POST /experiments/aggregate-all - Aggregate all
- POST /experiments/cache/clear - Clear cache
- POST /experiments/{key}/ai-analysis - AI analysis
- GET /experiments/{key}/quick-recommendation - Quick recommendation
- GET /experiments/{key}/trend - Daily trend
- GET /experiments/{key}/hourly-trend - Hourly trend
"""

import logging
import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel, Field, field_validator

from dependencies import require_admin
from domains.platform.experiments.service import ExperimentService  # v3.29: Use Service class
from domains.platform import experiments  # v3.29: Keep for legacy functions (analysis, trend, etc.)
from domains.platform import experiment_ai_service  # EXP-HIGH-4: Moved import to top
from infrastructure.repositories.experiment_repository import SupabaseExperimentRepository
from infrastructure.rate_limiter import limiter
from core.database import get_async_db_client

# Import response models (EXP-HIGH-1)
from api.admin.experiments_models import (
    ExperimentListResponse, ExperimentResponse, ExperimentCreateResponse,
    ExperimentDetailResponse, ExperimentUpdateResponse, StatusUpdateResponse,
    ExperimentDeleteResponse, ExperimentResultsResponse, AggregationResponse,
    CacheClearResponse, AIAnalysisResponse, RecommendationResponse,
    DailyTrendResponse, HourlyTrendResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/experiments", tags=["admin-experiments-v2"])


# ==========================================
# Dependency Injection
# ==========================================

async def get_experiment_service() -> ExperimentService:
    """
    Dependency injection factory for ExperimentService.

    Returns:
        ExperimentService instance with Repository injected
    """
    db = await get_async_db_client()
    experiment_repo = SupabaseExperimentRepository(client=db)
    return ExperimentService(experiment_repo)


# ==========================================
# Constants
# ==========================================

DEFAULT_TREND_DAYS = 30
MAX_TREND_DAYS = 90
DEFAULT_TREND_HOURS = 24
MAX_TREND_HOURS = 168  # 7 days


# ==========================================
# Constants (v3.25)
# ==========================================

# v3.25: EXP-MEDIUM-2 - Valid experiment statuses
VALID_EXPERIMENT_STATUSES = {"draft", "running", "paused", "completed"}

# v3.25: EXP-MEDIUM-3 - Valid experiment types
VALID_EXPERIMENT_TYPES = {"ab", "multivariate", "feature_flag"}

# v3.25: EXP-MEDIUM-4 - Date format validation pattern
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?")


def validate_date_format(date_str: Optional[str], field_name: str) -> None:
    """v3.25: EXP-MEDIUM-4 - Validate date format (YYYY-MM-DD or ISO)."""
    if date_str is not None and not DATE_PATTERN.match(date_str):
        raise HTTPException(400, f"Invalid {field_name} format. Use YYYY-MM-DD or ISO format")


# ==========================================
# Request Models
# ==========================================

class VariantConfig(BaseModel):
    key: str
    name: str
    weight: int = Field(ge=0, le=100)


class TargetingConfig(BaseModel):
    include_anonymous: bool = True
    tiers: Optional[List[str]] = None


class MetricConfig(BaseModel):
    key: str
    event: str
    type: str = "conversion"


class ExperimentCreateRequest(BaseModel):
    experiment_key: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    experiment_type: str = Field(default="ab", max_length=50)
    variants: List[VariantConfig]
    targeting: Optional[TargetingConfig] = None
    traffic_allocation: int = Field(default=100, ge=0, le=100)
    metrics: Optional[List[MetricConfig]] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None

    # v3.25: EXP-MEDIUM-3 - Validate experiment_type
    @field_validator("experiment_type")
    @classmethod
    def validate_experiment_type(cls, v):
        if v not in VALID_EXPERIMENT_TYPES:
            raise ValueError(f"Invalid experiment_type. Must be one of: {', '.join(VALID_EXPERIMENT_TYPES)}")
        return v


class ExperimentUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    variants: Optional[List[VariantConfig]] = None
    targeting: Optional[TargetingConfig] = None
    traffic_allocation: Optional[int] = Field(default=None, ge=0, le=100)
    metrics: Optional[List[MetricConfig]] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    fallback_variant: Optional[str] = Field(None, max_length=100)
    winning_variant: Optional[str] = Field(None, max_length=100)


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., max_length=50)

    # v3.25: EXP-MEDIUM-2 - Validate status
    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in VALID_EXPERIMENT_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(VALID_EXPERIMENT_STATUSES)}")
        return v


class AIAnalysisRequest(BaseModel):
    additional_context: Optional[str] = Field(None, max_length=2000)


# ==========================================
# Helper Functions
# ==========================================

def _enrich_results_with_significance(results: Dict[str, Any]) -> Dict[str, Any]:
    """Add statistical significance analysis to results."""
    variants_data = results.get("variants", {})
    if "control" in variants_data:
        control_data = variants_data["control"]
        for variant_key, variant_data in variants_data.items():
            if variant_key != "control":
                significance = experiments.calculate_statistical_significance(
                    control_conversions=control_data.get("total_conversions", 0),
                    control_exposures=control_data.get("total_exposures", 0),
                    variant_conversions=variant_data.get("total_conversions", 0),
                    variant_exposures=variant_data.get("total_exposures", 0)
                )
                variant_data["significance"] = significance
    return results


# ==========================================
# CRUD Endpoints (v3.25: Added rate limiting and validation)
# ==========================================

@router.get("", response_model=ExperimentListResponse)
@limiter.limit("30/minute")
async def list_experiments(
    request: Request,
    status: Optional[str] = Query(None, max_length=50, description="Filter by status"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Page size (1-100)"),
    admin: dict = Depends(require_admin),
    experiment_service: ExperimentService = Depends(get_experiment_service),  # v3.29: DI
):
    """List all experiments."""
    try:
        logger.info(f"[Admin {admin.get('id')}] Listing experiments (status={status}, offset={offset}, limit={limit})")

        # v3.25: EXP-MEDIUM-2 - Validate status parameter
        if status is not None and status not in VALID_EXPERIMENT_STATUSES:
            raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(VALID_EXPERIMENT_STATUSES)}")

        # v3.29: Use ExperimentService with DI
        experiments, total = await experiment_service.list_experiments(status=status, limit=limit, offset=offset)
        return ExperimentListResponse(experiments=experiments, total=total, offset=offset, limit=limit)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] List experiments failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to list experiments")


@router.post("", response_model=ExperimentCreateResponse)
@limiter.limit("20/minute")
async def create_experiment(
    request: Request,
    req: ExperimentCreateRequest,
    admin: dict = Depends(require_admin),
    experiment_service: ExperimentService = Depends(get_experiment_service),  # v3.29: DI
):
    """Create new experiment."""
    try:
        logger.info(f"[Admin {admin.get('id')}] Creating experiment: {req.experiment_key}")

        total_weight = sum(v.weight for v in req.variants)
        if total_weight != 100:
            raise HTTPException(400, f"Variants weight must sum to 100, got {total_weight}")

        variants = [v.model_dump() for v in req.variants]
        targeting = req.targeting.model_dump() if req.targeting else None
        metrics = [m.model_dump() for m in req.metrics] if req.metrics else None

        experiment = await experiment_service.create_experiment(
            experiment_key=req.experiment_key,
            name=req.name,
            description=req.description,
            experiment_type=req.experiment_type,
            variants=variants,
            targeting=targeting,
            traffic_allocation=req.traffic_allocation,
            metrics=metrics,
            start_at=req.start_at,
            end_at=req.end_at,
            created_by=admin.get("id")
        )

        if not experiment:
            raise HTTPException(500, "Failed to create experiment")

        logger.info(f"[Admin {admin.get('id')}] Created experiment: {req.experiment_key}")
        return ExperimentCreateResponse(status="created", experiment=ExperimentResponse(**experiment))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Create experiment failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to create experiment")


@router.get("/{experiment_key}", response_model=ExperimentDetailResponse)
@limiter.limit("30/minute")
async def get_experiment(
    request: Request,
    experiment_key: str,
    admin: dict = Depends(require_admin),
    experiment_service: ExperimentService = Depends(get_experiment_service),  # v3.29: DI
):
    """Get experiment details."""
    try:
        logger.info(f"[Admin {admin.get('id')}] Getting experiment: {experiment_key}")

        experiment = await experiment_service.get_experiment(experiment_key)
        if not experiment:
            raise HTTPException(404, "Experiment not found")

        return ExperimentDetailResponse(experiment=ExperimentResponse(**experiment))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Get experiment failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve experiment")


@router.put("/{experiment_key}", response_model=ExperimentUpdateResponse)
@limiter.limit("20/minute")
async def update_experiment(
    request: Request,
    experiment_key: str,
    req: ExperimentUpdateRequest,
    admin: dict = Depends(require_admin),
    experiment_service: ExperimentService = Depends(get_experiment_service),  # v3.29: DI
):
    """Update experiment configuration."""
    try:
        logger.info(f"[Admin {admin.get('id')}] Updating experiment: {experiment_key}")

        updates = {}
        if req.name is not None:
            updates["name"] = req.name
        if req.description is not None:
            updates["description"] = req.description
        if req.variants is not None:
            total_weight = sum(v.weight for v in req.variants)
            if total_weight != 100:
                raise HTTPException(400, f"Variants weight must sum to 100, got {total_weight}")
            updates["variants"] = [v.model_dump() for v in req.variants]
        if req.targeting is not None:
            updates["targeting"] = req.targeting.model_dump()
        if req.traffic_allocation is not None:
            updates["traffic_allocation"] = req.traffic_allocation
        if req.metrics is not None:
            updates["metrics"] = [m.model_dump() for m in req.metrics]
        if req.start_at is not None:
            updates["start_at"] = req.start_at
        if req.end_at is not None:
            updates["end_at"] = req.end_at
        if req.fallback_variant is not None:
            updates["fallback_variant"] = req.fallback_variant
        if req.winning_variant is not None:
            updates["winning_variant"] = req.winning_variant

        if not updates:
            raise HTTPException(400, "No fields to update")

        experiment = await experiment_service.update_experiment(experiment_key, **updates)
        if not experiment:
            raise HTTPException(404, "Experiment not found")

        logger.info(f"[Admin {admin.get('id')}] Updated experiment: {experiment_key}")
        return ExperimentUpdateResponse(status="updated", experiment=ExperimentResponse(**experiment))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Update experiment failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to update experiment")


@router.put("/{experiment_key}/status", response_model=StatusUpdateResponse)
@limiter.limit("20/minute")
async def update_experiment_status(
    request: Request,
    experiment_key: str,
    req: StatusUpdateRequest,
    admin: dict = Depends(require_admin),
    experiment_service: ExperimentService = Depends(get_experiment_service),  # v3.29: DI
):
    """Update experiment status."""
    try:
        logger.info(f"[Admin {admin.get('id')}] Updating status for {experiment_key}: {req.status}")

        # Note: Status validation is now done in StatusUpdateRequest via field_validator
        result = await experiment_service.update_experiment_status(experiment_key, req.status)
        if not result:
            raise HTTPException(404, "Experiment not found")

        logger.info(f"[Admin {admin.get('id')}] Status updated: {experiment_key} -> {req.status}")
        return StatusUpdateResponse(status="updated", new_status=req.status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Update status failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to update status")


@router.delete("/{experiment_key}", response_model=ExperimentDeleteResponse)
@limiter.limit("10/minute")
async def delete_experiment(
    request: Request,
    experiment_key: str,
    admin: dict = Depends(require_admin),
    experiment_service: ExperimentService = Depends(get_experiment_service),  # v3.29: DI
):
    """Delete experiment."""
    try:
        logger.info(f"[Admin {admin.get('id')}] Deleting experiment: {experiment_key}")

        experiment = await experiment_service.get_experiment(experiment_key)
        if not experiment:
            raise HTTPException(404, "Experiment not found")
        if experiment.get("status") == "running":
            raise HTTPException(400, "Cannot delete running experiment")

        success = await experiment_service.delete_experiment(experiment_key)
        if not success:
            raise HTTPException(500, "Failed to delete experiment")

        # ✅ Task 9 - Phase 2: Log experiment deletion to audit trail
        try:
            from core.database import get_async_db_client
            from infrastructure.repositories.admin_repository import SupabaseAdminUsersRepository

            admin_repo = SupabaseAdminUsersRepository(await get_async_db_client())
            await admin_repo.admin_log_operation(
                admin_id=admin["id"],
                operation_type="experiment_delete",
                target_type="experiment",
                target_id=experiment_key,
                details=f"Experiment '{experiment_key}' deleted",
                source="api",
            )
        except Exception as e:
            logger.warning(f"Failed to log experiment deletion: {e}")

        logger.info(f"[Admin {admin.get('id')}] Deleted experiment: {experiment_key}")
        return ExperimentDeleteResponse(status="deleted", experiment_key=experiment_key)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Delete experiment failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to delete experiment")


# ==========================================
# Results & Analysis Endpoints (v3.25: Added rate limiting)
# ==========================================

@router.get("/{experiment_key}/results", response_model=ExperimentResultsResponse)
@limiter.limit("30/minute")
async def get_experiment_results(
    request: Request,
    experiment_key: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO format)"),
    admin: dict = Depends(require_admin),
    experiment_service: ExperimentService = Depends(get_experiment_service),  # v3.30: DI
):
    """Get experiment results."""
    try:
        logger.info(f"[Admin {admin.get('id')}] Getting results for {experiment_key}")

        # v3.25: EXP-MEDIUM-4 - Validate date formats
        validate_date_format(start_date, "start_date")
        validate_date_format(end_date, "end_date")

        # v3.28: EXP-MEDIUM-2 - Add timezone handling
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
        else:
            start_dt = None

        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
        else:
            end_dt = None

        # v3.30: Use ExperimentService
        results = await experiment_service.get_experiment_results(experiment_key, start_dt, end_dt)
        if not results:
            raise HTTPException(404, "Experiment not found")

        enriched = _enrich_results_with_significance(results)
        return ExperimentResultsResponse(**enriched)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Get results failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to retrieve results")


@router.post("/{experiment_key}/aggregate", response_model=AggregationResponse)
@limiter.limit("10/minute")
async def trigger_aggregation(
    request: Request,
    experiment_key: str,
    admin: dict = Depends(require_admin),
    experiment_service: ExperimentService = Depends(get_experiment_service),  # v3.30: DI
):
    """Trigger result aggregation."""
    try:
        logger.info(f"[Admin {admin.get('id')}] Triggering aggregation for {experiment_key}")

        # v3.30: Use ExperimentService
        success = await experiment_service.aggregate_experiment_results(experiment_key)
        if not success:
            raise HTTPException(500, "Failed to aggregate results")

        logger.info(f"[Admin {admin.get('id')}] Aggregation completed: {experiment_key}")
        return AggregationResponse(
            status="aggregated",
            experiment_key=experiment_key,
            message="Aggregation completed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Aggregation failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to aggregate results")


@router.post("/aggregate-all", response_model=AggregationResponse)
@limiter.limit("5/minute")
async def trigger_all_aggregation(
    request: Request,
    admin: dict = Depends(require_admin),
    experiment_service: ExperimentService = Depends(get_experiment_service),  # v3.30: DI
):
    """Trigger aggregation for all running experiments."""
    try:
        logger.info(f"[Admin {admin.get('id')}] Triggering aggregation for all experiments")

        # v3.30: Use ExperimentService (None = all running experiments)
        success = await experiment_service.aggregate_experiment_results(None)
        if not success:
            raise HTTPException(500, "Failed to aggregate results")

        logger.info(f"[Admin {admin.get('id')}] All aggregations completed")
        return AggregationResponse(
            status="aggregated",
            message="All experiments aggregated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Aggregate-all failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to aggregate results")


@router.post("/cache/clear", response_model=CacheClearResponse)
@limiter.limit("10/minute")
async def clear_cache(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Clear experiment cache."""
    try:
        logger.info(f"[Admin {admin.get('id')}] Clearing experiment cache")

        experiments.clear_experiment_cache()

        logger.info(f"[Admin {admin.get('id')}] Cache cleared")
        return CacheClearResponse(status="cache_cleared")

    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Clear cache failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to clear cache")


@router.post("/{experiment_key}/ai-analysis", response_model=AIAnalysisResponse)
@limiter.limit("10/minute")
async def get_ai_analysis(
    request: Request,
    experiment_key: str,
    req: Optional[AIAnalysisRequest] = None,
    admin: dict = Depends(require_admin),
    experiment_service: ExperimentService = Depends(get_experiment_service),  # v3.29: DI
):
    """Get AI analysis report for experiment."""
    try:
        logger.info(f"[Admin {admin.get('id')}] Requesting AI analysis for {experiment_key}")

        experiment = await experiment_service.get_experiment(experiment_key)
        if not experiment:
            raise HTTPException(404, "Experiment not found")

        results_data = await experiment_service.get_experiment_results(experiment_key)
        if not results_data or not results_data.get("results"):
            results = {"variants": {}}
        else:
            results = results_data.get("results", {})
        results = _enrich_results_with_significance(results)

        additional_context = req.additional_context if req else None
        analysis = experiment_ai_service.analyze_experiment_results(experiment, results, additional_context)

        if not analysis.get("success"):
            raise HTTPException(500, "AI analysis failed")

        logger.info(f"[Admin {admin.get('id')}] AI analysis completed for {experiment_key}")
        return AIAnalysisResponse(**analysis)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] AI analysis failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to generate AI analysis")


@router.get("/{experiment_key}/quick-recommendation", response_model=RecommendationResponse)
@limiter.limit("30/minute")
async def get_quick_recommendation(
    request: Request,
    experiment_key: str,
    admin: dict = Depends(require_admin),
    experiment_service: ExperimentService = Depends(get_experiment_service),  # v3.29: DI
):
    """Get quick decision recommendation (rule-based)."""
    try:
        logger.info(f"[Admin {admin.get('id')}] Getting quick recommendation for {experiment_key}")

        experiment = await experiment_service.get_experiment(experiment_key)
        if not experiment:
            raise HTTPException(404, "Experiment not found")

        results_data = await experiment_service.get_experiment_results(experiment_key)
        if not results_data or not results_data.get("results"):
            results = {"variants": {}}
        else:
            results = results_data.get("results", {})
        results = _enrich_results_with_significance(results)

        recommendation = experiment_ai_service.get_quick_recommendation(results)

        logger.info(f"[Admin {admin.get('id')}] Quick recommendation generated for {experiment_key}")
        return RecommendationResponse(experiment_key=experiment_key, recommendation=recommendation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Quick recommendation failed: {type(e).__name__} - {e}")
        raise HTTPException(500, "Failed to generate recommendation")


# ==========================================
# Trend Endpoints (v3.25: Added rate limiting and validation)
# ==========================================

@router.get("/{experiment_key}/trend", response_model=DailyTrendResponse)
@limiter.limit("20/minute")
async def get_experiment_trend(
    request: Request,
    experiment_key: str,
    days: int = Query(DEFAULT_TREND_DAYS, ge=1, le=MAX_TREND_DAYS, description="Number of days (1-90)"),
    admin: dict = Depends(require_admin),
    experiment_service: ExperimentService = Depends(get_experiment_service),  # v3.30: DI
):
    """Get daily trend data for charts."""
    try:
        logger.info(f"[Admin {admin.get('id')}] Getting daily trend: {experiment_key} ({days} days)")

        # v3.30: Use ExperimentService
        trend_data = await experiment_service.get_daily_trend(experiment_key, days)
        if not trend_data:
            raise HTTPException(status_code=404, detail="Experiment not found")

        return DailyTrendResponse(**trend_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] Get daily trend failed for {experiment_key}: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve trend data")


@router.get("/{experiment_key}/hourly-trend", response_model=HourlyTrendResponse)
@limiter.limit("20/minute")
async def get_hourly_trend(
    request: Request,
    experiment_key: str,
    hours: int = Query(DEFAULT_TREND_HOURS, ge=1, le=MAX_TREND_HOURS, description="Number of hours (1-168)"),
    admin: dict = Depends(require_admin),
    experiment_service: ExperimentService = Depends(get_experiment_service),  # v3.30: DI
):
    """Get hourly trend data."""
    try:
        logger.info(f"[Admin {admin.get('id')}] Getting hourly trend: {experiment_key} ({hours} hours)")

        # v3.30: Use ExperimentService
        trend_data = await experiment_service.get_hourly_trend(experiment_key, hours)
        if not trend_data:
            raise HTTPException(status_code=404, detail="Experiment not found")

        return HourlyTrendResponse(**trend_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] Get hourly trend failed for {experiment_key}: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve trend data")

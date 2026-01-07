"""
Admin Experiments API - A/B Testing experiment management.

@module api.admin.experiments
@version 2.0.0

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

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from dependencies import require_admin
from domains.platform import experiment_service

router = APIRouter(prefix="/experiments", tags=["admin-experiments-v2"])


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
    description: Optional[str] = None
    experiment_type: str = "ab"
    variants: List[VariantConfig]
    targeting: Optional[TargetingConfig] = None
    traffic_allocation: int = Field(default=100, ge=0, le=100)
    metrics: Optional[List[MetricConfig]] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None


class ExperimentUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    variants: Optional[List[VariantConfig]] = None
    targeting: Optional[TargetingConfig] = None
    traffic_allocation: Optional[int] = Field(default=None, ge=0, le=100)
    metrics: Optional[List[MetricConfig]] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    fallback_variant: Optional[str] = None
    winning_variant: Optional[str] = None


class StatusUpdateRequest(BaseModel):
    status: str


class AIAnalysisRequest(BaseModel):
    additional_context: Optional[str] = None


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
                significance = experiment_service.calculate_statistical_significance(
                    control_conversions=control_data.get("total_conversions", 0),
                    control_exposures=control_data.get("total_exposures", 0),
                    variant_conversions=variant_data.get("total_conversions", 0),
                    variant_exposures=variant_data.get("total_exposures", 0)
                )
                variant_data["significance"] = significance
    return results


# ==========================================
# CRUD Endpoints
# ==========================================

@router.get("")
async def list_experiments(
    status: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    admin: dict = Depends(require_admin)
):
    """List all experiments."""
    offset = (page - 1) * limit
    experiments, total = experiment_service.list_experiments(status=status, limit=limit, offset=offset)
    return {"experiments": experiments, "total": total, "page": page, "limit": limit}


@router.post("")
async def create_experiment(
    req: ExperimentCreateRequest,
    admin: dict = Depends(require_admin)
):
    """Create new experiment."""
    total_weight = sum(v.weight for v in req.variants)
    if total_weight != 100:
        raise HTTPException(400, f"Variants weight must sum to 100, got {total_weight}")

    variants = [v.model_dump() for v in req.variants]
    targeting = req.targeting.model_dump() if req.targeting else None
    metrics = [m.model_dump() for m in req.metrics] if req.metrics else None

    experiment = experiment_service.create_experiment(
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
    return {"status": "created", "experiment": experiment}


@router.get("/{experiment_key}")
async def get_experiment(
    experiment_key: str,
    admin: dict = Depends(require_admin)
):
    """Get experiment details."""
    experiment = experiment_service.get_experiment(experiment_key, use_cache=False)
    if not experiment:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found")
    return {"experiment": experiment}


@router.put("/{experiment_key}")
async def update_experiment(
    experiment_key: str,
    req: ExperimentUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """Update experiment configuration."""
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

    experiment = experiment_service.update_experiment(experiment_key, updates, admin.get("id"))
    if not experiment:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found")
    return {"status": "updated", "experiment": experiment}


@router.put("/{experiment_key}/status")
async def update_experiment_status(
    experiment_key: str,
    req: StatusUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """Update experiment status."""
    valid_statuses = ["draft", "running", "paused", "completed"]
    if req.status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid_statuses}")

    success = experiment_service.update_experiment_status(experiment_key, req.status, admin.get("id"))
    if not success:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found")
    return {"status": "updated", "new_status": req.status}


@router.delete("/{experiment_key}")
async def delete_experiment(
    experiment_key: str,
    admin: dict = Depends(require_admin)
):
    """Delete experiment."""
    experiment = experiment_service.get_experiment(experiment_key, use_cache=False)
    if not experiment:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found")
    if experiment.get("status") == "running":
        raise HTTPException(400, "Cannot delete running experiment")

    success = experiment_service.delete_experiment(experiment_key)
    if not success:
        raise HTTPException(500, "Failed to delete experiment")
    return {"status": "deleted", "experiment_key": experiment_key}


# ==========================================
# Results & Analysis Endpoints
# ==========================================

@router.get("/{experiment_key}/results")
async def get_experiment_results(
    experiment_key: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """Get experiment results."""
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None

    results = experiment_service.get_experiment_results(experiment_key, start_dt, end_dt)
    if not results:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found")
    return _enrich_results_with_significance(results)


@router.post("/{experiment_key}/aggregate")
async def trigger_aggregation(
    experiment_key: str,
    admin: dict = Depends(require_admin)
):
    """Trigger result aggregation."""
    success = experiment_service.aggregate_experiment_results(experiment_key)
    if not success:
        raise HTTPException(500, "Failed to aggregate results")
    return {"status": "aggregated", "experiment_key": experiment_key}


@router.post("/aggregate-all")
async def trigger_all_aggregation(admin: dict = Depends(require_admin)):
    """Trigger aggregation for all running experiments."""
    success = experiment_service.aggregate_experiment_results()
    if not success:
        raise HTTPException(500, "Failed to aggregate results")
    return {"status": "aggregated"}


@router.post("/cache/clear")
async def clear_cache(admin: dict = Depends(require_admin)):
    """Clear experiment cache."""
    experiment_service.clear_experiment_cache()
    return {"status": "cache_cleared"}


@router.post("/{experiment_key}/ai-analysis")
async def get_ai_analysis(
    experiment_key: str,
    req: Optional[AIAnalysisRequest] = None,
    admin: dict = Depends(require_admin)
):
    """Get AI analysis report for experiment."""
    from domains.platform import experiment_ai_service

    experiment = experiment_service.get_experiment(experiment_key, use_cache=False)
    if not experiment:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found")

    results = experiment_service.get_experiment_results(experiment_key)
    if not results:
        results = {"variants": {}}
    results = _enrich_results_with_significance(results)

    additional_context = req.additional_context if req else None
    analysis = experiment_ai_service.analyze_experiment_results(experiment, results, additional_context)

    if not analysis.get("success"):
        raise HTTPException(500, analysis.get("error", "AI analysis failed"))
    return analysis


@router.get("/{experiment_key}/quick-recommendation")
async def get_quick_recommendation(
    experiment_key: str,
    admin: dict = Depends(require_admin)
):
    """Get quick decision recommendation (rule-based)."""
    from domains.platform import experiment_ai_service

    experiment = experiment_service.get_experiment(experiment_key, use_cache=False)
    if not experiment:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found")

    results = experiment_service.get_experiment_results(experiment_key)
    if not results:
        results = {"variants": {}}
    results = _enrich_results_with_significance(results)

    recommendation = experiment_ai_service.get_quick_recommendation(results)
    return {"experiment_key": experiment_key, "recommendation": recommendation}


# ==========================================
# Trend Endpoints
# ==========================================

@router.get("/{experiment_key}/trend")
async def get_experiment_trend(
    experiment_key: str,
    days: int = 30,
    admin: dict = Depends(require_admin)
):
    """Get daily trend data for charts."""
    days = min(days, 90)

    experiment = experiment_service.get_experiment(experiment_key, use_cache=False)
    if not experiment:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found")

    experiment_id = experiment.get("id")
    variants = experiment.get("variants", [])
    variant_keys = [v.get("key") for v in variants]

    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")

    results_data = supabase.table("experiment_results").select("*")\
        .eq("experiment_id", experiment_id).gte("date", start_date).order("date").execute()

    daily_data = {}
    for result in results_data.data or []:
        date_str = result.get("date", "")
        if not date_str:
            continue
        if date_str not in daily_data:
            daily_data[date_str] = {vk: {"exposures": 0, "conversions": 0} for vk in variant_keys}

        variant_key = result.get("variant_key")
        if variant_key in daily_data[date_str]:
            daily_data[date_str][variant_key]["exposures"] += result.get("exposures", 0)
            daily_data[date_str][variant_key]["conversions"] += result.get("conversions", 0)

    trend_list = []
    for date_str in sorted(daily_data.keys()):
        day_entry = {"date": date_str}
        for variant_key in variant_keys:
            vdata = daily_data[date_str].get(variant_key, {"exposures": 0, "conversions": 0})
            day_entry[f"{variant_key}_exposures"] = vdata["exposures"]
            day_entry[f"{variant_key}_conversions"] = vdata["conversions"]
            rate = (vdata["conversions"] / vdata["exposures"] * 100) if vdata["exposures"] > 0 else 0
            day_entry[f"{variant_key}_rate"] = round(rate, 2)
        trend_list.append(day_entry)

    return {"experiment_key": experiment_key, "variants": variant_keys, "days": days, "trend": trend_list}


@router.get("/{experiment_key}/hourly-trend")
async def get_hourly_trend(
    experiment_key: str,
    hours: int = 24,
    admin: dict = Depends(require_admin)
):
    """Get hourly trend data."""
    hours = min(hours, 168)

    experiment = experiment_service.get_experiment(experiment_key, use_cache=False)
    if not experiment:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found")

    experiment_id = experiment.get("id")
    variants = experiment.get("variants", [])
    variant_keys = [v.get("key") for v in variants]

    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=hours)
    start_date = start_time.strftime("%Y-%m-%d")

    results_data = supabase.table("experiment_results").select("*")\
        .eq("experiment_id", experiment_id).gte("date", start_date).order("date").order("hour").execute()

    trend_list = []
    for result in results_data.data or []:
        date_str = result.get("date", "")
        hour = result.get("hour", 0)
        variant_key = result.get("variant_key")
        time_str = f"{date_str}T{hour:02d}:00:00"

        result_datetime = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        if result_datetime.replace(tzinfo=timezone.utc) < start_time:
            continue

        existing = next((t for t in trend_list if t.get("time") == time_str), None)
        if not existing:
            existing = {"time": time_str}
            for vk in variant_keys:
                existing[f"{vk}_exposures"] = 0
                existing[f"{vk}_conversions"] = 0
            trend_list.append(existing)

        if variant_key in variant_keys:
            existing[f"{variant_key}_exposures"] = result.get("exposures", 0)
            existing[f"{variant_key}_conversions"] = result.get("conversions", 0)

    trend_list.sort(key=lambda x: x.get("time", ""))
    return {"experiment_key": experiment_key, "variants": variant_keys, "hours": hours, "trend": trend_list}

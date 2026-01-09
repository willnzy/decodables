"""
Experiments Management API Models - Request/Response schemas.

@module api.admin.experiments_models
@version 1.0.0
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ==========================================
# Experiment Models
# ==========================================

class ExperimentVariantResponse(BaseModel):
    """Experiment variant."""
    key: str = Field(..., description="Variant key")
    name: str = Field(..., description="Variant name")
    weight: int = Field(..., description="Traffic weight (0-100)")
    config: Optional[Dict[str, Any]] = Field(None, description="Variant configuration")


class ExperimentTargetingResponse(BaseModel):
    """Targeting configuration."""
    include_anonymous: bool = Field(True, description="Include anonymous users")
    tiers: Optional[List[str]] = Field(None, description="Target user tiers")


class ExperimentMetricResponse(BaseModel):
    """Experiment metric."""
    key: str = Field(..., description="Metric key")
    event: str = Field(..., description="Event name")
    type: str = Field(..., description="Metric type")


class ExperimentResponse(BaseModel):
    """Single experiment."""
    id: Optional[str] = Field(None, description="Experiment ID")
    experiment_key: str = Field(..., description="Experiment key")
    name: str = Field(..., description="Experiment name")
    description: Optional[str] = Field(None, description="Description")
    experiment_type: str = Field(..., description="Experiment type")
    status: str = Field(..., description="Experiment status")
    variants: List[Dict[str, Any]] = Field(..., description="Variants")
    targeting: Optional[Dict[str, Any]] = Field(None, description="Targeting rules")
    traffic_allocation: int = Field(..., description="Traffic allocation percentage")
    metrics: Optional[List[Dict[str, Any]]] = Field(None, description="Metrics")
    start_at: Optional[str] = Field(None, description="Start time")
    end_at: Optional[str] = Field(None, description="End time")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="Creator ID")
    fallback_variant: Optional[str] = Field(None, description="Fallback variant key")
    winning_variant: Optional[str] = Field(None, description="Winning variant key")


class ExperimentListResponse(BaseModel):
    """Response for GET /experiments."""
    experiments: List[ExperimentResponse] = Field(..., description="List of experiments")
    total: int = Field(..., description="Total count")
    offset: int = Field(..., description="Pagination offset")
    limit: int = Field(..., description="Page size")


class ExperimentCreateResponse(BaseModel):
    """Response for POST /experiments."""
    status: str = Field(..., description="Creation status")
    experiment: ExperimentResponse = Field(..., description="Created experiment")


class ExperimentDetailResponse(BaseModel):
    """Response for GET /experiments/{key}."""
    experiment: ExperimentResponse = Field(..., description="Experiment details")


class ExperimentUpdateResponse(BaseModel):
    """Response for PUT /experiments/{key}."""
    status: str = Field(..., description="Update status")
    experiment: ExperimentResponse = Field(..., description="Updated experiment")


class StatusUpdateResponse(BaseModel):
    """Response for PUT /experiments/{key}/status."""
    status: str = Field(..., description="Update status")
    new_status: str = Field(..., description="New experiment status")


class ExperimentDeleteResponse(BaseModel):
    """Response for DELETE /experiments/{key}."""
    status: str = Field(..., description="Deletion status")
    experiment_key: str = Field(..., description="Deleted experiment key")


# ==========================================
# Results & Analysis Models
# ==========================================

class VariantResultData(BaseModel):
    """Variant result data."""
    total_exposures: int = Field(..., description="Total exposures")
    total_conversions: int = Field(..., description="Total conversions")
    conversion_rate: float = Field(..., description="Conversion rate (%)")
    significance: Optional[float] = Field(None, description="Statistical significance")


class ExperimentResultsResponse(BaseModel):
    """Response for GET /experiments/{key}/results."""
    experiment_key: Optional[str] = Field(None, description="Experiment key")
    variants: Dict[str, Any] = Field(..., description="Variant results")
    start_date: Optional[str] = Field(None, description="Start date")
    end_date: Optional[str] = Field(None, description="End date")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AggregationResponse(BaseModel):
    """Response for POST /experiments/{key}/aggregate."""
    status: str = Field(..., description="Aggregation status")
    experiment_key: Optional[str] = Field(None, description="Experiment key")
    message: Optional[str] = Field(None, description="Status message")


class CacheClearResponse(BaseModel):
    """Response for POST /experiments/cache/clear."""
    status: str = Field(..., description="Cache clear status")


# ==========================================
# AI Analysis Models
# ==========================================

class AIAnalysisResponse(BaseModel):
    """Response for POST /experiments/{key}/ai-analysis."""
    success: bool = Field(..., description="Analysis success status")
    analysis: Optional[str] = Field(None, description="AI analysis text")
    recommendations: Optional[List[str]] = Field(None, description="Recommendations")
    confidence: Optional[float] = Field(None, description="Confidence score")
    summary: Optional[str] = Field(None, description="Summary")
    insights: Optional[List[str]] = Field(None, description="Key insights")


class RecommendationResponse(BaseModel):
    """Response for GET /experiments/{key}/quick-recommendation."""
    experiment_key: str = Field(..., description="Experiment key")
    recommendation: Dict[str, Any] = Field(..., description="Recommendation data")


# ==========================================
# Trend Models
# ==========================================

class DailyTrendResponse(BaseModel):
    """Response for GET /experiments/{key}/trend."""
    experiment_key: str = Field(..., description="Experiment key")
    variants: List[str] = Field(..., description="Variant keys")
    days: int = Field(..., description="Number of days")
    trend: List[Dict[str, Any]] = Field(..., description="Trend data points")


class HourlyTrendResponse(BaseModel):
    """Response for GET /experiments/{key}/hourly-trend."""
    experiment_key: str = Field(..., description="Experiment key")
    variants: List[str] = Field(..., description="Variant keys")
    hours: int = Field(..., description="Number of hours")
    trend: List[Dict[str, Any]] = Field(..., description="Trend data points")

"""
Config Management API Models - Request/Response schemas.

@module api.admin.config_models
@version 1.0.0
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ==========================================
# Config Entry Models
# ==========================================

class ConfigEntry(BaseModel):
    """Single configuration entry."""
    key: str = Field(..., description="Configuration key")
    value: str = Field(..., description="Configuration value (JSON string)")
    config_group: str = Field(..., description="Configuration group")
    description: Optional[str] = Field(None, description="Configuration description")
    is_active: bool = Field(..., description="Whether config is active")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    updated_by: Optional[str] = Field(None, description="Admin ID who last updated")


# ==========================================
# Config Query Response Models
# ==========================================

class AllConfigsResponse(BaseModel):
    """Response for GET /config."""
    configs: List[ConfigEntry] = Field(..., description="List of configurations")
    total: int = Field(..., description="Total number of configs")


class SingleConfigResponse(BaseModel):
    """Response for GET /config/{config_key}."""
    key: str = Field(..., description="Configuration key")
    value: Dict[str, Any] = Field(..., description="Configuration value")
    is_active: bool = Field(..., description="Whether config is active")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


# ==========================================
# Config Update Response Models
# ==========================================

class ConfigUpdateResponse(BaseModel):
    """Response for PUT /config."""
    success: bool = Field(..., description="Update success status")
    message: str = Field(..., description="Response message")
    config_key: str = Field(..., description="Updated configuration key")


class BatchConfigUpdateResponse(BaseModel):
    """Response for PUT /config/batch."""
    success: bool = Field(..., description="Overall success status")
    results: Dict[str, bool] = Field(..., description="Per-config update results")
    updated_count: int = Field(..., description="Number of successfully updated configs")
    failed_count: int = Field(..., description="Number of failed updates")


# ==========================================
# Rate Limit Models
# ==========================================

class RateLimitConfig(BaseModel):
    """Single rate limit configuration."""
    key: str = Field(..., description="Rate limit key")
    limit: int = Field(..., description="Request limit")
    window: str = Field(..., description="Time window (minute, hour, day)")
    enabled: bool = Field(..., description="Whether rate limit is enabled")


class RateLimitsResponse(BaseModel):
    """Response for GET /rate-limits."""
    rate_limits: List[RateLimitConfig] = Field(..., description="List of rate limit configs")
    global_enabled: bool = Field(..., description="Whether rate limiting is globally enabled")
    total: int = Field(..., description="Total number of rate limit configs")


class RateLimitPresetInfo(BaseModel):
    """Single rate limit preset information."""
    name: str = Field(..., description="Preset name")
    description: str = Field(..., description="Preset description")
    multiplier: Optional[float] = Field(None, description="Multiplier for limits")
    enabled: Optional[bool] = Field(None, description="Whether to enable rate limiting")


class RateLimitPresetsResponse(BaseModel):
    """Response for GET /rate-limits/presets."""
    presets: List[RateLimitPresetInfo] = Field(..., description="Available presets")
    total: int = Field(..., description="Total number of presets")


class RateLimitPresetApplyResponse(BaseModel):
    """Response for POST /rate-limits/preset."""
    success: bool = Field(..., description="Apply success status")
    message: str = Field(..., description="Response message")
    preset: str = Field(..., description="Applied preset name")


# ==========================================
# Cache Management Models
# ==========================================

class CacheClearResponse(BaseModel):
    """Response for POST /config/cache/clear."""
    success: bool = Field(..., description="Clear success status")
    message: str = Field(..., description="Response message")

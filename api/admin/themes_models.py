"""Admin Themes API - Request and Response Models.

@module api.admin.themes_models
@version 2.1.0
"""

from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator

from domains.themes.constants import (
    VALID_CATEGORIES,
    VALID_REVIEW_STATUSES,
    VALID_REVIEW_ACTIONS,
    NAME_MIN_LENGTH,
    NAME_MAX_LENGTH,
    SLOGAN_MAX_LENGTH,
    DESCRIPTION_MAX_LENGTH,
    REVIEW_NOTES_MAX_LENGTH,
    PRIORITY_MIN,
    PRIORITY_MAX,
    DEFAULT_LIMIT,
    MAX_LIMIT,
    DEFAULT_BATCH_DAYS,
    MAX_BATCH_DAYS,
    MIN_BATCH_DAYS,
)


# ==========================================
# Request Models
# ==========================================

class ThemeCreateRequest(BaseModel):
    """Theme creation request."""
    name: str = Field(..., min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    category: str = Field("holiday")
    priority: int = Field(50, ge=PRIORITY_MIN, le=PRIORITY_MAX)
    description: Optional[str] = Field(None, max_length=DESCRIPTION_MAX_LENGTH)
    slogan: Optional[str] = Field(None, max_length=SLOGAN_MAX_LENGTH)
    theme_config: Optional[Dict[str, Any]] = None
    name_i18n: Optional[Dict[str, str]] = None
    slogan_i18n: Optional[Dict[str, str]] = None
    description_i18n: Optional[Dict[str, str]] = None
    regions: Optional[List[str]] = None
    date_rule: Optional[Dict[str, Any]] = None
    linked_campaign_id: Optional[str] = None
    source_url: Optional[str] = None
    learn_more_url: Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        if v not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}")
        return v


class ThemeUpdateRequest(BaseModel):
    """Theme update request."""
    name: Optional[str] = Field(None, min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    category: Optional[str] = None
    priority: Optional[int] = Field(None, ge=PRIORITY_MIN, le=PRIORITY_MAX)
    description: Optional[str] = Field(None, max_length=DESCRIPTION_MAX_LENGTH)
    slogan: Optional[str] = Field(None, max_length=SLOGAN_MAX_LENGTH)
    theme_config: Optional[Dict[str, Any]] = None
    name_i18n: Optional[Dict[str, str]] = None
    slogan_i18n: Optional[Dict[str, str]] = None
    description_i18n: Optional[Dict[str, str]] = None
    regions: Optional[List[str]] = None
    date_rule: Optional[Dict[str, Any]] = None
    linked_campaign_id: Optional[str] = None
    source_url: Optional[str] = None
    learn_more_url: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        if v is not None and v not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}")
        return v


class ThemeReviewRequest(BaseModel):
    """Theme review request."""
    action: str = Field(..., description="Review action: approve, reject, switch")
    alternative_id: Optional[str] = Field(None, description="Alternative ID for switch action")
    notes: Optional[str] = Field(None, max_length=REVIEW_NOTES_MAX_LENGTH)

    @field_validator("action")
    @classmethod
    def validate_action(cls, v):
        if v not in VALID_REVIEW_ACTIONS:
            raise ValueError(f"Invalid action. Must be one of: {', '.join(VALID_REVIEW_ACTIONS)}")
        return v


class ThemeRegenerateRequest(BaseModel):
    """Theme regenerate request."""
    reason: Optional[str] = Field(None, max_length=REVIEW_NOTES_MAX_LENGTH)


class BatchApproveRequest(BaseModel):
    """Batch approve request."""
    theme_ids: List[str] = Field(..., min_length=1, max_length=100)


class BatchGenerateRequest(BaseModel):
    """Batch generate request."""
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    days: int = Field(DEFAULT_BATCH_DAYS, ge=MIN_BATCH_DAYS, le=MAX_BATCH_DAYS)
    overwrite: bool = Field(False)


# ==========================================
# Response Models
# ==========================================

class ThemeResponse(BaseModel):
    """Single theme response."""
    id: str
    name: str
    category: Optional[str] = None
    priority: Optional[int] = None
    date: Optional[str] = None
    description: Optional[str] = None
    slogan: Optional[str] = None
    theme_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None
    review_status: Optional[str] = None
    ai_generated: Optional[bool] = None
    ai_alternatives: Optional[List[Dict[str, Any]]] = None
    selected_alternative_id: Optional[str] = None
    ai_recommended_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ThemeListResponse(BaseModel):
    """Theme list response."""
    themes: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int


class GenerationStatusResponse(BaseModel):
    """Generation status response."""
    total_days: int
    generated: int
    missing: int
    review_status: Dict[str, int]
    missing_dates: List[str]
    recommendation: str


class BatchGenerateResponse(BaseModel):
    """Batch generate response."""
    generated: int
    skipped: int
    failed: int
    details: List[Dict[str, Any]]


class ReviewResponse(BaseModel):
    """Review response."""
    theme: Dict[str, Any]
    message: str


class HistoryResponse(BaseModel):
    """Theme history response."""
    theme_id: str
    current: Dict[str, Any]
    history: List[Dict[str, Any]]
    regenerate_count: int


class BatchApproveResponse(BaseModel):
    """Batch approve response."""
    approved: int
    failed: int

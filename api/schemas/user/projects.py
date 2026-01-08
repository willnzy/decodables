"""
Project Schemas - Project related request/response models

@module schemas.projects
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class ProjectCreate(BaseModel):
    """Create project request."""
    title: Optional[str] = Field(default="My Magic Story", max_length=100)
    canvas_data: Optional[dict] = None


class ProjectUpdate(BaseModel):
    """Update project request."""
    title: Optional[str] = Field(default=None, max_length=100)
    canvas_data: Optional[dict] = None
    thumbnail_url: Optional[str] = None
    used_listing_ids: Optional[List[str]] = None


class ProjectResponse(BaseModel):
    """Project response."""
    id: str
    user_id: str
    title: str
    thumbnail_url: Optional[str] = None
    canvas_data: Optional[dict] = None
    contains_locked_elements: bool = False
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime


class ProjectSaveResult(BaseModel):
    """Result of project save operation."""
    status: str = "saved"
    locked_elements: List[dict] = []
    new_usage_recorded: List[str] = []

"""
System Resources Schemas
Data models for system resource management

@module schemas.system_resources
@version 3.24
"""

from typing import List, Optional
from pydantic import BaseModel


class ResourceCreate(BaseModel):
    """Request model for creating a system resource."""
    type: str
    category: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = []
    allowed_tiers: Optional[List[str]] = ["free", "starter", "pro"]
    sort_order: Optional[int] = 0
    is_active: Optional[bool] = True
    metadata: Optional[dict] = {}


class ResourceUpdate(BaseModel):
    """Request model for updating a system resource."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    allowed_tiers: Optional[List[str]] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    metadata: Optional[dict] = None


class ResourceBatchAction(BaseModel):
    """Request model for batch resource actions."""
    resource_ids: List[str]
    action: str  # "activate", "deactivate", "delete"

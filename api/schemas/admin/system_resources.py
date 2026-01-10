"""
System Resources Schemas
Data models for system resource management

@module schemas.system_resources
@version 3.25

Changes:
- v3.25: Security improvements
  - Added field length constraints (SR-LOW-2)
  - Added action enum validation (SR-MEDIUM-4)
  - Added resource_ids max length validation
  - Added tags list size limit
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# v3.25: Valid batch actions
VALID_BATCH_ACTIONS = Literal["activate", "deactivate", "delete"]

# v3.25: Max tags per resource
MAX_TAGS = 20

# v3.25: Max batch size
MAX_BATCH_SIZE = 100


class ResourceCreate(BaseModel):
    """Request model for creating a system resource."""
    type: str = Field(..., max_length=50)  # v3.25: SR-LOW-2
    category: Optional[str] = Field(None, max_length=50)  # v3.25: SR-LOW-2
    name: Optional[str] = Field(None, max_length=200)  # v3.25: SR-LOW-2
    description: Optional[str] = Field(None, max_length=2000)  # v3.25: SR-LOW-2
    tags: Optional[List[str]] = Field(default=[], max_length=MAX_TAGS)  # v3.25: Limit tags
    allowed_tiers: Optional[List[str]] = ["t1", "t2", "t3"]
    sort_order: Optional[int] = Field(0, ge=0, le=10000)  # v3.25: Add bounds
    is_active: Optional[bool] = True
    metadata: Optional[dict] = {}


class ResourceUpdate(BaseModel):
    """Request model for updating a system resource."""
    name: Optional[str] = Field(None, max_length=200)  # v3.25: SR-LOW-2
    description: Optional[str] = Field(None, max_length=2000)  # v3.25: SR-LOW-2
    category: Optional[str] = Field(None, max_length=50)  # v3.25: SR-LOW-2
    tags: Optional[List[str]] = Field(None, max_length=MAX_TAGS)  # v3.25: Limit tags
    allowed_tiers: Optional[List[str]] = None
    sort_order: Optional[int] = Field(None, ge=0, le=10000)  # v3.25: Add bounds
    is_active: Optional[bool] = None
    metadata: Optional[dict] = None


class ResourceBatchAction(BaseModel):
    """Request model for batch resource actions."""
    resource_ids: List[str] = Field(..., max_length=MAX_BATCH_SIZE)  # v3.25: SR-MEDIUM-3
    action: VALID_BATCH_ACTIONS  # v3.25: SR-MEDIUM-4 - Enum validation

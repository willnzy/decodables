"""
Asset Schemas - User asset related models

@module schemas.assets
"""

from typing import Optional
from pydantic import BaseModel


class CreateAssetFromUrlRequest(BaseModel):
    """Request body for creating asset from existing URL"""
    url: str
    project_id: Optional[str] = None
    type: Optional[str] = "uploaded"  # uploaded/ai_generated/scanned
    description: Optional[str] = None
    metadata: Optional[dict] = None

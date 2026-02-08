"""Feature Override Admin API (API-010 Phase 5).

@module api.admin.overrides
@version 1.0.0

Admin endpoints for managing user feature overrides:
- GET /admin/feature-overrides/{user_id} - Get all overrides for a user
- POST /admin/feature-overrides/{user_id} - Set override for a user
- DELETE /admin/feature-overrides/{user_id}/{flag_key} - Remove override
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from dependencies import require_admin
from container import get_container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feature-overrides", tags=["admin-feature-overrides"])


# ==================== Request/Response Models ====================

class FeatureOverrideResponse(BaseModel):
    """Feature override record response."""
    user_id: str
    flag_key: str
    override_value: bool
    created_at: Optional[str] = None
    created_by: Optional[str] = None


class UserOverridesResponse(BaseModel):
    """User feature overrides response."""
    user_id: str
    overrides: List[FeatureOverrideResponse]


# ==================== Endpoints ====================

@router.get("/{user_id}", response_model=UserOverridesResponse)
async def get_user_overrides(
    user_id: str,
    admin=Depends(require_admin),
) -> UserOverridesResponse:
    """
    API-010 Phase 5: Get all feature overrides for a user.

    Returns all feature flag overrides configured for a specific user.
    This allows admins to see which features have been manually enabled/disabled.

    Args:
        user_id: User ID to fetch overrides for
        admin: Admin user (from require_admin dependency)

    Returns:
        UserOverridesResponse with list of all overrides for the user

    Raises:
        HTTPException: 404 if user not found (returns empty overrides list)
    """
    try:
        container = get_container()
        client = await container.get_supabase_client()

        result = await client.table("user_feature_overrides").select("*").eq(
            "user_id", user_id
        ).execute()

        overrides = []
        if result.data:
            for row in result.data:
                overrides.append(FeatureOverrideResponse(
                    user_id=row["user_id"],
                    flag_key=row["flag_key"],
                    override_value=row.get("override_value", False),
                    created_at=row.get("created_at"),
                    created_by=row.get("created_by"),
                ))

        logger.info(
            f"[Admin] Retrieved {len(overrides)} feature overrides for user {user_id}",
            extra={"admin_id": admin.get("id"), "user_id": user_id, "override_count": len(overrides)}
        )

        return UserOverridesResponse(user_id=user_id, overrides=overrides)

    except Exception as e:
        logger.error(
            f"[Admin] Failed to get overrides for user {user_id}: {e}",
            extra={"admin_id": admin.get("id"), "user_id": user_id}
        )
        raise HTTPException(500, "Failed to get feature overrides. Please try again.")

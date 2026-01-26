"""
User Assets Router - User asset management endpoints (v3.3.0)

@module api.user.user_assets
@version 3.3.0

Changes:
- v3.3.0: Dashboard endpoint refactored
  - GET /dashboard now returns asset list with view filtering (all/bought/selling)
  - Supports offset/limit pagination and search
  - Returns counts for tab badges
- v3.2.0: Pagination support
  - GET /assets now supports offset/limit pagination
  - GET /deleted now supports offset/limit pagination
  - Response format: {items, total, offset, limit, has_more}
- v3.1.0: API Consolidation Phase 3
  - REMOVED: GET /seller-stats (use /api/v2/user/seller/stats?include=assets)
- v3.0.0: DDD architecture upgrade - Full CQRS pattern
  - Created AssetsService v1.0.0 with 10 business methods
  - Added 5 Query Handlers (GetUserAssets, CheckURL, DashboardStats, SellerStats, ListDeleted)
  - Added 5 Command Handlers (Upload, FromURL, Delete, IncrementUsage, Restore)
  - Eliminated direct Repository instantiation from API layer
  - Eliminated direct Supabase calls from API layer
  - Moved all business logic to Service layer
  - Improved testability and maintainability

- v3.25: Security improvements (inherited)
  - UA-HIGH-1: Added SSRF protection (private IP filtering)
  - UA-MEDIUM-1: Added asset_id UUID format validation
  - UA-MEDIUM-2: Added project_id UUID format validation
  - UA-MEDIUM-3: Added rate limiting to all endpoints
  - UA-LOW-1: Limited error detail exposure in check-url
  - UA-LOW-2: Added URL length limit (2048 chars)

Endpoints:
- GET /api/v2/user/assets?offset=0&limit=50 - Get user assets (paginated)
- POST /api/v2/user/assets - Upload asset
- DELETE /api/v2/user/assets/{asset_id} - Delete asset
- POST /api/v2/user/assets/from-url - Add asset from URL
- GET /api/v2/user/assets/check-url - Check URL validity
- POST /api/v2/user/assets/{asset_id}/increment-usage - Increment usage
- GET /api/v2/user/assets/dashboard?view=all&offset=0&limit=15 - Asset dashboard (with view filter)
- GET /api/v2/user/assets/deleted?offset=0&limit=50 - Get deleted assets (paginated)
- POST /api/v2/user/assets/{asset_id}/restore - Restore asset
"""

import re
from typing import Optional

from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, Query
from pydantic import BaseModel, Field

from domains.identity.aggregates.user_profile import UserProfile
from infrastructure.logging.activity_logger import log_activity
from infrastructure.rate_limiter import limiter
from dependencies import get_current_user
from core.utils.timezone import get_request_timezone
from core.middleware import validate_file_size  # P3-005: File upload size validation
from container import get_container
from application.queries.assets import (
    GetUserAssetsQuery,
    CheckURLQuery,
    GetDeletedAssetsQuery,
    GetDashboardAssetsQuery,
)
from application.commands.assets import (
    UploadAssetCommand,
    AddAssetFromURLCommand,
    DeleteAssetCommand,
    IncrementAssetUsageCommand,
    RestoreAssetCommand,
)

router = APIRouter(prefix="/assets", tags=["user-assets-v3"])


# ==========================================
# Constants (v3.25)
# ==========================================

# v3.25: UA-MEDIUM-1/2 - UUID validation pattern
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)


def validate_uuid_id(value: str, field_name: str = "ID") -> None:
    """v3.25: Validate that a value is a valid UUID format."""
    from fastapi import HTTPException
    if not UUID_PATTERN.match(value):
        raise HTTPException(400, f"Invalid {field_name} format")


def validate_optional_uuid(value: Optional[str], field_name: str = "ID") -> None:
    """v3.25: Validate optional UUID field."""
    if value is not None:
        validate_uuid_id(value, field_name)


# ==========================================
# Request Models
# ==========================================

class AssetFromUrlRequest(BaseModel):
    url: str = Field(..., max_length=2048)
    project_id: Optional[str] = Field(None, pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


# ==========================================
# Asset Endpoints
# ==========================================

@router.get("")
@limiter.limit("60/minute")
async def my_assets(
    request: Request,
    project_id: Optional[str] = None,
    scope: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
    user: UserProfile = Depends(get_current_user)
):
    """
    Fetch user assets with pagination.

    v3.2.0: Added pagination support (offset/limit).
    v3.0.0: Now uses GetUserAssetsHandler (Container pattern).

    Query Parameters:
        - project_id: Optional project ID filter
        - scope: "all" for cross-project (Pro only)
        - offset: Number of items to skip (default: 0)
        - limit: Max items to return (default: 50, max: 100)

    Returns:
        {
            "items": [...],
            "total": 123,
            "offset": 0,
            "limit": 50,
            "has_more": true
        }
    """
    # Validate pagination params
    if offset < 0:
        offset = 0
    if limit < 1:
        limit = 50
    if limit > 100:
        limit = 100

    # v3.25: UA-MEDIUM-2 - Validate project_id format
    validate_optional_uuid(project_id, "project ID")

    # Pro tier check for cross-project scope (t3/t4 only)
    user_tier = user.tier.value if hasattr(user.tier, 'value') else user.tier
    if scope == "all" and user_tier not in ("t3", "t4"):
        from fastapi import HTTPException
        raise HTTPException(403, "Pro required for cross-project history")

    target_proj = project_id if scope != "all" else None

    container = get_container()
    handler = await container.get_user_assets_handler()

    query = GetUserAssetsQuery(
        user_id=user.user_id,
        project_id=target_proj,
        offset=offset,
        limit=limit
    )
    result = await handler.handle(query)

    return {
        "items": result.items,
        "total": result.total,
        "offset": result.offset,
        "limit": result.limit,
        "has_more": result.has_more
    }


@router.post("")
@limiter.limit("20/minute")
async def upload_asset(
    request: Request,
    file: UploadFile = Depends(validate_file_size),  # P3-005: File size validation (10MB limit)
    project_id: Optional[str] = Form(None),
    user: UserProfile = Depends(get_current_user)
):
    """
    Upload personal assets (Pro only, PRD v3.2).

    v3.0.0: Now uses UploadAssetHandler (Container pattern).
    Business logic (Pro check, file validation) moved to Service layer.

    P3-005: Added 10MB file size limit via validate_file_size dependency.
    """
    # v3.25: UA-MEDIUM-2 - Validate project_id format
    validate_optional_uuid(project_id, "project ID")

    tz = get_request_timezone(request, user_id=user.user_id)

    container = get_container()
    handler = await container.get_upload_asset_handler()

    command = UploadAssetCommand(
        user_id=user.user_id,
        user_tier=user.tier.value if hasattr(user.tier, 'value') else str(user.tier),
        file=file,
        project_id=project_id,
        timezone=tz
    )
    result = await handler.handle(command)

    return result.result


@router.delete("/{asset_id}")
@limiter.limit("30/minute")
async def delete_asset(
    request: Request,
    asset_id: str,
    permanent: bool = False,
    user: UserProfile = Depends(get_current_user)
):
    """
    Delete a user asset (PRD v3.3).

    v3.0.0: Now uses DeleteAssetHandler (Container pattern).
    """
    # v3.25: UA-MEDIUM-1 - Validate asset_id format
    validate_uuid_id(asset_id, "asset ID")

    container = get_container()
    handler = await container.get_delete_asset_handler()

    command = DeleteAssetCommand(
        asset_id=asset_id,
        user_id=user.user_id,
        permanent=permanent
    )
    result = await handler.handle(command)

    # Log activity
    if permanent:
        log_activity(user.user_id, "permanent_delete_asset", {"asset_id": asset_id})
    else:
        log_activity(user.user_id, "delete_asset", {"asset_id": asset_id})

    return result.result


@router.post("/from-url")
@limiter.limit("30/minute")
async def add_asset_from_url(
    request: Request,
    req: AssetFromUrlRequest,
    user: UserProfile = Depends(get_current_user)
):
    """
    Add an asset from external URL.

    v3.0.0: Now uses AddAssetFromURLHandler (Container pattern).
    Business logic (SSRF protection, URL validation) moved to Service layer.
    """
    tz = get_request_timezone(request, user_id=user.user_id)

    container = get_container()
    handler = await container.get_add_asset_from_url_handler()

    command = AddAssetFromURLCommand(
        user_id=user.user_id,
        url=req.url,
        project_id=req.project_id,
        timezone=tz
    )
    result = await handler.handle(command)

    # Log activity
    if result.result.get("asset"):
        log_activity(user.user_id, "create_asset_from_url", {
            "asset_id": result.result["asset"].get("id")
        })

    return result.result


@router.get("/check-url")
@limiter.limit("60/minute")
async def check_url(
    request: Request,
    url: str,
    user: UserProfile = Depends(get_current_user)
):
    """
    Check if a URL points to a valid image.

    v3.0.0: Now uses CheckURLHandler (Container pattern).
    Business logic (SSRF check, URL validation) moved to Service layer.
    """
    container = get_container()
    handler = await container.get_check_url_handler()

    query = CheckURLQuery(url=url)
    result = await handler.handle(query)

    return result.result


@router.post("/{asset_id}/increment-usage")
@limiter.limit("120/minute")
async def increment_usage(
    request: Request,
    asset_id: str,
    user: UserProfile = Depends(get_current_user)
):
    """
    Increment usage count for an asset.

    v3.0.0: Now uses IncrementAssetUsageHandler (Container pattern).
    """
    # v3.25: UA-MEDIUM-1 - Validate asset_id format
    validate_uuid_id(asset_id, "asset ID")

    container = get_container()
    handler = await container.get_increment_asset_usage_handler()

    command = IncrementAssetUsageCommand(
        asset_id=asset_id,
        user_id=user.user_id
    )
    result = await handler.handle(command)

    return {"status": "ok", "usage_count": result.usage_count}


@router.get("/dashboard")
@limiter.limit("30/minute")
async def get_asset_dashboard(
    request: Request,
    view: str = Query("all", pattern="^(all|bought|selling)$"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(15, ge=1, le=100, description="Number of records to return (1-100)"),
    search: Optional[str] = None,
    user: UserProfile = Depends(get_current_user)
):
    """
    Get assets for dashboard with view type filtering.

    v3.3.0: Refactored to return asset list with view filtering (all/bought/selling).
    v3.0.0: Now uses GetDashboardAssetsHandler (Container pattern).

    Args:
        view: View type - "all" (default), "bought", or "selling"
        offset: Number of records to skip (default: 0)
        limit: Number of records to return (default: 15, max: 100)
        search: Search query (searches in name field)

    Returns:
        Dict with items, total, offset, limit, has_more, and counts for tab badges
    """
    container = get_container()
    handler = await container.get_dashboard_assets_handler()

    query = GetDashboardAssetsQuery(
        user_id=user.user_id,
        view_type=view,
        offset=offset,
        limit=limit,
        search=search,
    )

    result = await handler.handle(query)

    if result.success:
        return result.data
    else:
        from fastapi import HTTPException
        raise HTTPException(500, result.error or "Failed to load assets")


@router.get("/deleted")
@limiter.limit("30/minute")
async def get_deleted(
    request: Request,
    offset: int = 0,
    limit: int = 50,
    user: UserProfile = Depends(get_current_user)
):
    """
    Get soft-deleted assets (trash) with pagination.

    v3.2.0: Added pagination support (offset/limit).
    v3.0.0: Now uses GetDeletedAssetsHandler (Container pattern).

    Query Parameters:
        - offset: Number of items to skip (default: 0)
        - limit: Max items to return (default: 50, max: 100)

    Returns:
        {
            "items": [...],
            "total": 10,
            "offset": 0,
            "limit": 50,
            "has_more": false
        }
    """
    # Validate pagination params
    if offset < 0:
        offset = 0
    if limit < 1:
        limit = 50
    if limit > 100:
        limit = 100

    container = get_container()
    handler = await container.get_deleted_assets_handler()

    query = GetDeletedAssetsQuery(
        user_id=user.user_id,
        offset=offset,
        limit=limit
    )
    result = await handler.handle(query)

    return {
        "items": result.items,
        "total": result.total,
        "offset": result.offset,
        "limit": result.limit,
        "has_more": result.has_more
    }


@router.post("/{asset_id}/restore")
@limiter.limit("30/minute")
async def restore(
    request: Request,
    asset_id: str,
    user: UserProfile = Depends(get_current_user)
):
    """
    Restore a soft-deleted asset.

    v3.0.0: Now uses RestoreAssetHandler (Container pattern).
    """
    # v3.25: UA-MEDIUM-1 - Validate asset_id format
    validate_uuid_id(asset_id, "asset ID")

    container = get_container()
    handler = await container.get_restore_asset_handler()

    command = RestoreAssetCommand(
        asset_id=asset_id,
        user_id=user.user_id
    )
    result = await handler.handle(command)

    # Log activity
    log_activity(user.user_id, "restore_asset", {"asset_id": asset_id})

    return {"status": "ok", "asset": result.asset}

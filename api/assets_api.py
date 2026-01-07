"""
User Assets API - User personal asset management.

@module api.assets_api
@version 1.0.0

Endpoints:
- GET /api/v2/assets - Get user assets
- POST /api/v2/assets - Upload asset (Pro only)
- DELETE /api/v2/assets/{id} - Delete asset
- POST /api/v2/assets/from-url - Add asset from URL
- GET /api/v2/assets/check-url - Check URL validity
- POST /api/v2/assets/{id}/increment-usage - Increment usage count
- GET /api/v2/assets/dashboard - Asset dashboard
- GET /api/v2/assets/deleted - Get deleted assets (trash)
- POST /api/v2/assets/{id}/restore - Restore deleted asset
"""

import uuid
import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, Query
from pydantic import BaseModel

from dependencies import get_current_user
from services.db_service import (
    supabase,
    get_assets,
    save_asset,
    soft_delete_asset,
    permanently_hide_asset,
    increment_asset_usage,
    get_deleted_assets,
    restore_asset,
    log_activity,
)
from services.rate_limiter import limiter
from timezone_utils import get_request_timezone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/assets", tags=["assets-v2"])


# ==========================================
# Request/Response Models
# ==========================================

class AssetFromUrlRequest(BaseModel):
    """Request to add asset from URL."""
    url: str
    project_id: Optional[str] = None


class AssetItem(BaseModel):
    """Asset item."""
    id: str
    url: str
    source: str
    usage_count: int = 0
    created_at: Optional[str] = None

    class Config:
        extra = "allow"


class AssetsListResponse(BaseModel):
    """Assets list response."""
    items: List[Dict[str, Any]]
    total: int


class AssetUploadResponse(BaseModel):
    """Asset upload response."""
    url: str
    filename: str


class AssetDeleteResponse(BaseModel):
    """Asset delete response."""
    status: str
    action: str
    asset_id: str


class AssetDashboardResponse(BaseModel):
    """Asset dashboard response."""
    total_assets: int
    total_usage: int
    by_source: Dict[str, int]
    recent: List[Dict[str, Any]]


class UrlCheckResponse(BaseModel):
    """URL check response."""
    valid: bool
    content_type: Optional[str] = None
    status_code: Optional[int] = None
    error: Optional[str] = None


# ==========================================
# Endpoints
# ==========================================

@router.get("")
async def get_my_assets(
    project_id: Optional[str] = None,
    scope: Optional[str] = Query(None, pattern="^(project|all)$"),
    user: dict = Depends(get_current_user),
) -> AssetsListResponse:
    """
    Get user's assets.

    Args:
        project_id: Filter by project
        scope: "project" for single project, "all" for all (Pro only)

    Returns:
        User's assets list
    """
    # Cross-project history requires Pro
    if scope == "all" and (user.get("tier") or "").lower() != "pro":
        raise HTTPException(403, "Pro required for cross-project history")

    target_proj = project_id if scope != "all" else None
    assets = get_assets(user["id"], target_proj)

    return AssetsListResponse(
        items=assets if isinstance(assets, list) else assets.get("items", []),
        total=len(assets) if isinstance(assets, list) else assets.get("total", 0),
    )


@router.post("")
@limiter.limit("20/minute")
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
) -> AssetUploadResponse:
    """
    Upload personal asset (Pro only).

    Args:
        file: Image file to upload
        project_id: Optional project to associate with

    Returns:
        Uploaded asset URL and filename
    """
    from services.ai.image_generator import supabase as storage_supabase, BUCKET_NAME

    user_tier = (user.get("tier") or "").lower()
    if user_tier != "pro":
        raise HTTPException(403, "Personal asset upload requires Pro plan")

    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']
    if file.content_type not in allowed_types:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    # Read and validate size
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(400, "File too large. Maximum size is 5MB")

    if not storage_supabase:
        raise HTTPException(500, "Storage service not configured")

    # Generate filename
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
    filename = f"{user['id']}/uploads/{uuid.uuid4()}.{ext}"

    try:
        storage_supabase.storage.from_(BUCKET_NAME).upload(
            path=filename,
            file=contents,
            file_options={"content-type": file.content_type},
        )
        url = storage_supabase.storage.from_(BUCKET_NAME).get_public_url(filename)

        # Save to database
        tz = get_request_timezone(request, user_id=user.get("id"))
        save_asset(user["id"], url, "uploaded", project_id, timezone=tz)

        return AssetUploadResponse(url=url, filename=filename)

    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(500, f"Failed to upload file: {str(e)}")


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    permanent: bool = Query(False),
    user: dict = Depends(get_current_user),
) -> AssetDeleteResponse:
    """
    Delete a user asset.

    Args:
        asset_id: Asset ID to delete
        permanent: If true, permanently hide (stage 2)

    Returns:
        Deletion status
    """
    if permanent:
        result = permanently_hide_asset(asset_id, user["id"])
        if result:
            log_activity(user["id"], "permanent_delete_asset", {"asset_id": asset_id})
        action = "permanently deleted"
    else:
        result = soft_delete_asset(asset_id, user["id"])
        if result:
            log_activity(user["id"], "delete_asset", {"asset_id": asset_id})
        action = "moved to trash"

    if not result:
        raise HTTPException(404, "Asset not found or not owned by user")

    return AssetDeleteResponse(
        status="ok",
        action=action,
        asset_id=asset_id,
    )


@router.post("/from-url")
@limiter.limit("30/minute")
async def add_asset_from_url(
    request: Request,
    req: AssetFromUrlRequest,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Add an asset from external URL.

    Args:
        req: Request with URL and optional project_id

    Returns:
        Created asset
    """
    import httpx

    # Validate URL format
    if not req.url.startswith(('http://', 'https://')):
        raise HTTPException(400, "Invalid URL format")

    # Check if URL is accessible and points to an image
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.head(req.url, follow_redirects=True)
            if response.status_code != 200:
                raise HTTPException(400, f"URL not accessible: {response.status_code}")

            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                raise HTTPException(400, "URL does not point to an image")

    except httpx.RequestError as e:
        raise HTTPException(400, f"Failed to access URL: {str(e)}")

    # Save asset
    tz = get_request_timezone(request, user_id=user.get("id"))
    asset = save_asset(user["id"], req.url, "external", req.project_id, timezone=tz)

    if asset:
        log_activity(user["id"], "create_asset_from_url", {"asset_id": asset.get("id")})

    return {"status": "ok", "asset": asset}


@router.get("/check-url")
async def check_url(
    url: str,
    user: dict = Depends(get_current_user),
) -> UrlCheckResponse:
    """
    Check if a URL points to a valid image.

    Returns:
        URL validity status
    """
    import httpx

    if not url.startswith(('http://', 'https://')):
        return UrlCheckResponse(valid=False, error="Invalid URL format")

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.head(url, follow_redirects=True)
            content_type = response.headers.get('content-type', '')

            return UrlCheckResponse(
                valid=response.status_code == 200 and content_type.startswith('image/'),
                content_type=content_type,
                status_code=response.status_code,
            )

    except Exception as e:
        return UrlCheckResponse(valid=False, error=str(e))


@router.post("/{asset_id}/increment-usage")
async def increment_usage(
    asset_id: str,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Increment usage count for an asset.

    Returns:
        Updated usage count
    """
    result = increment_asset_usage(asset_id, user["id"])
    if not result:
        raise HTTPException(404, "Asset not found")

    return {"status": "ok", "usage_count": result.get("usage_count", 0)}


@router.get("/dashboard")
async def get_asset_dashboard(
    user: dict = Depends(get_current_user),
) -> AssetDashboardResponse:
    """
    Get asset usage dashboard data.

    Returns:
        Dashboard statistics
    """
    try:
        assets = supabase.table("assets").select("*").eq("user_id", user["id"]).execute()
        assets_data = assets.data or []

        total_assets = len(assets_data)
        total_usage = sum(a.get("usage_count", 0) for a in assets_data)

        by_source = {}
        for a in assets_data:
            src = a.get("source", "unknown")
            by_source[src] = by_source.get(src, 0) + 1

        recent = sorted(
            assets_data,
            key=lambda x: x.get("created_at", ""),
            reverse=True,
        )[:10]

        return AssetDashboardResponse(
            total_assets=total_assets,
            total_usage=total_usage,
            by_source=by_source,
            recent=recent,
        )

    except Exception as e:
        logger.error(f"Failed to get asset dashboard: {e}")
        raise HTTPException(500, str(e))


@router.get("/deleted")
async def get_deleted_assets_list(
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get soft-deleted assets (trash).

    Returns:
        List of deleted assets that can be restored
    """
    return get_deleted_assets(user["id"])


@router.post("/{asset_id}/restore")
async def restore_deleted_asset(
    asset_id: str,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Restore a soft-deleted asset from trash.

    Returns:
        Restored asset
    """
    result = restore_asset(asset_id, user["id"])
    if not result:
        raise HTTPException(404, "Asset not found in trash")

    log_activity(user["id"], "restore_asset", {"asset_id": asset_id})

    return {"status": "ok", "asset": result}

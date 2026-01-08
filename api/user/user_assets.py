"""
User Assets Router - User asset management endpoints

@module api.user.user_assets
@version 3.25

Changes:
- v3.25: Security improvements
  - UA-HIGH-1: Added SSRF protection (private IP filtering)
  - UA-MEDIUM-1: Added asset_id UUID format validation
  - UA-MEDIUM-2: Added project_id UUID format validation
  - UA-MEDIUM-3: Added rate limiting to all endpoints
  - UA-LOW-1: Limited error detail exposure in check-url
  - UA-LOW-2: Added URL length limit (2048 chars)

Endpoints:
- GET /api/v2/user/assets - Get user assets
- POST /api/v2/user/assets - Upload asset
- DELETE /api/v2/user/assets/{asset_id} - Delete asset
- POST /api/v2/user/assets/from-url - Add asset from URL
- GET /api/v2/user/assets/check-url - Check URL validity
- POST /api/v2/user/assets/{asset_id}/increment-usage - Increment usage
- GET /api/v2/user/assets/dashboard - Asset dashboard
- GET /api/v2/user/assets/seller-stats - Seller stats
- GET /api/v2/user/assets/deleted - Get deleted assets
- POST /api/v2/user/assets/{asset_id}/restore - Restore asset
"""

import uuid
import logging
import re
import ipaddress
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, File, Form
from pydantic import BaseModel, Field

from core.database import get_supabase_client
from infrastructure.repositories.asset_repository import SupabaseAssetRepository
from infrastructure.logging.activity_logger import log_activity
from infrastructure.rate_limiter import limiter
from dependencies import get_current_user
from core.utils.timezone import get_request_timezone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["user-assets-v2"])


# ==========================================
# Constants (v3.25)
# ==========================================

# v3.25: UA-MEDIUM-1/2 - UUID validation pattern
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)

# v3.25: UA-LOW-2 - Maximum URL length
MAX_URL_LENGTH = 2048


def validate_uuid_id(value: str, field_name: str = "ID") -> None:
    """v3.25: Validate that a value is a valid UUID format."""
    if not UUID_PATTERN.match(value):
        raise HTTPException(400, f"Invalid {field_name} format")


def validate_optional_uuid(value: Optional[str], field_name: str = "ID") -> None:
    """v3.25: Validate optional UUID field."""
    if value is not None and not UUID_PATTERN.match(value):
        raise HTTPException(400, f"Invalid {field_name} format")


def is_private_ip(hostname: str) -> bool:
    """v3.25: UA-HIGH-1 - Check if hostname resolves to private/internal IP."""
    import socket
    try:
        # Resolve hostname to IP
        ip = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(ip)

        # Check if it's a private, loopback, link-local, or reserved address
        return (
            ip_obj.is_private or
            ip_obj.is_loopback or
            ip_obj.is_link_local or
            ip_obj.is_reserved or
            ip_obj.is_multicast
        )
    except (socket.gaierror, ValueError):
        # If we can't resolve, err on the side of caution
        return True


def validate_url_safe(url: str) -> None:
    """v3.25: UA-HIGH-1 - Validate URL is safe (no SSRF)."""
    # Check URL length
    if len(url) > MAX_URL_LENGTH:
        raise HTTPException(400, f"URL too long. Maximum {MAX_URL_LENGTH} characters")

    # Check URL format
    if not url.startswith(('http://', 'https://')):
        raise HTTPException(400, "Invalid URL format")

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname

        if not hostname:
            raise HTTPException(400, "Invalid URL: no hostname")

        # Block private IPs to prevent SSRF
        if is_private_ip(hostname):
            raise HTTPException(400, "URL points to internal network")

        # Block common internal hostnames
        blocked_hostnames = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
        if hostname.lower() in blocked_hostnames:
            raise HTTPException(400, "URL points to internal network")

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Invalid URL format")


# ==========================================
# Request Models
# ==========================================

class AssetFromUrlRequest(BaseModel):
    url: str = Field(..., max_length=MAX_URL_LENGTH)
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
    user: dict = Depends(get_current_user)
):
    """Fetch user assets."""
    # v3.25: UA-MEDIUM-2 - Validate project_id format
    validate_optional_uuid(project_id, "project ID")

    if scope == "all" and user["tier"] != "pro":
        raise HTTPException(403, "Pro required for cross-project history")
    target_proj = project_id if scope != "all" else None
    assets_repo = SupabaseAssetRepository()
    return await assets_repo.get_assets(user["id"], target_proj)


@router.post("")
@limiter.limit("20/minute")
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    user: dict = Depends(get_current_user)
):
    """Upload personal assets (Pro only, PRD v3.2)."""
    from shared.ai.image_generator import supabase as storage_supabase, BUCKET_NAME

    # v3.25: UA-MEDIUM-2 - Validate project_id format
    validate_optional_uuid(project_id, "project ID")

    user_tier = (user.get("tier") or "").lower()
    if user_tier != "pro":
        raise HTTPException(403, "Personal asset upload requires Pro plan.")
    
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']
    if file.content_type not in allowed_types:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")
    
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(400, "File too large. Maximum size is 5MB")
    
    if not storage_supabase:
        raise HTTPException(500, "Storage service not configured")
    
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
    filename = f"{user['id']}/uploads/{uuid.uuid4()}.{ext}"
    
    try:
        storage_supabase.storage.from_(BUCKET_NAME).upload(
            path=filename,
            file=contents,
            file_options={"content-type": file.content_type}
        )
        url = storage_supabase.storage.from_(BUCKET_NAME).get_public_url(filename)

        tz = get_request_timezone(request, user_id=user.get("id"))
        assets_repo = SupabaseAssetRepository()
        await assets_repo.save_asset(user["id"], url, "uploaded", project_id, timezone=tz)

        return {"url": url, "filename": filename}
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(500, f"Failed to upload file: {str(e)}")


@router.delete("/{asset_id}")
@limiter.limit("30/minute")
async def delete_asset(
    request: Request,
    asset_id: str,
    permanent: bool = False,
    user: dict = Depends(get_current_user)
):
    """Delete a user asset (PRD v3.3)."""
    # v3.25: UA-MEDIUM-1 - Validate asset_id format
    validate_uuid_id(asset_id, "asset ID")

    assets_repo = SupabaseAssetRepository()

    if permanent:
        result = await assets_repo.permanently_hide_asset(asset_id, user["id"])
        if result:
            log_activity(user["id"], "permanent_delete_asset", {"asset_id": asset_id})
        action = "permanently deleted"
    else:
        result = await assets_repo.soft_delete_asset(asset_id, user["id"])
        if result:
            log_activity(user["id"], "delete_asset", {"asset_id": asset_id})
        action = "moved to trash"

    if not result:
        raise HTTPException(404, "Asset not found or not owned by user")

    return {"status": "ok", "action": action, "asset_id": asset_id}


@router.post("/from-url")
@limiter.limit("30/minute")
async def add_asset_from_url(
    request: Request,
    req: AssetFromUrlRequest,
    user: dict = Depends(get_current_user)
):
    """Add an asset from external URL."""
    import httpx

    # v3.25: UA-HIGH-1 - Validate URL safety (SSRF protection)
    validate_url_safe(req.url)

    # Check if URL is accessible
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.head(req.url, follow_redirects=True)
            if response.status_code != 200:
                raise HTTPException(400, f"URL not accessible: {response.status_code}")

            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                raise HTTPException(400, "URL does not point to an image")
    except httpx.RequestError:
        raise HTTPException(400, "Failed to access URL")

    tz = get_request_timezone(request, user_id=user.get("id"))
    assets_repo = SupabaseAssetRepository()

    asset = await assets_repo.save_asset(user["id"], req.url, "external", req.project_id, timezone=tz)

    if asset:
        log_activity(user["id"], "create_asset_from_url", {"asset_id": asset.get("id")})

    return {"status": "ok", "asset": asset}


@router.get("/check-url")
@limiter.limit("60/minute")
async def check_url(request: Request, url: str, user: dict = Depends(get_current_user)):
    """Check if a URL points to a valid image."""
    import httpx

    # v3.25: UA-LOW-2 - Check URL length
    if len(url) > MAX_URL_LENGTH:
        return {"valid": False, "error": "URL too long"}

    if not url.startswith(('http://', 'https://')):
        return {"valid": False, "error": "Invalid URL format"}

    # v3.25: UA-HIGH-1 - Check for SSRF
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname or is_private_ip(hostname):
            return {"valid": False, "error": "Invalid URL"}
    except Exception:
        return {"valid": False, "error": "Invalid URL"}

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.head(url, follow_redirects=True)
            content_type = response.headers.get('content-type', '')

            return {
                "valid": response.status_code == 200 and content_type.startswith('image/'),
                "content_type": content_type,
                "status_code": response.status_code
            }
    except Exception:
        # v3.25: UA-LOW-1 - Don't expose detailed error messages
        return {"valid": False, "error": "Failed to access URL"}


@router.post("/{asset_id}/increment-usage")
@limiter.limit("120/minute")
async def increment_usage(request: Request, asset_id: str, user: dict = Depends(get_current_user)):
    """Increment usage count for an asset."""
    # v3.25: UA-MEDIUM-1 - Validate asset_id format
    validate_uuid_id(asset_id, "asset ID")

    assets_repo = SupabaseAssetRepository()
    result = await assets_repo.increment_asset_usage(asset_id, user["id"])
    if not result:
        raise HTTPException(404, "Asset not found")
    return {"status": "ok", "usage_count": result.get("usage_count", 0)}


@router.get("/dashboard")
@limiter.limit("30/minute")
async def get_asset_dashboard(request: Request, user: dict = Depends(get_current_user)):
    """Get asset usage dashboard data."""
    supabase = get_supabase_client()

    try:
        assets = supabase.table("assets").select("*").eq("user_id", user["id"]).execute()
        assets_data = assets.data or []
        
        total_assets = len(assets_data)
        total_usage = sum(a.get("usage_count", 0) for a in assets_data)
        by_source = {}
        for a in assets_data:
            src = a.get("source", "unknown")
            by_source[src] = by_source.get(src, 0) + 1
        
        return {
            "total_assets": total_assets,
            "total_usage": total_usage,
            "by_source": by_source,
            "recent": sorted(assets_data, key=lambda x: x.get("created_at", ""), reverse=True)[:10]
        }
    except Exception as e:
        logger.error(f"Failed to get asset dashboard: {e}")
        raise HTTPException(500, str(e))


@router.get("/seller-stats")
@limiter.limit("30/minute")
async def get_seller_stats(request: Request, user: dict = Depends(get_current_user)):
    """Get seller statistics for marketplace assets."""
    supabase = get_supabase_client()

    try:
        listings = supabase.table("marketplace_listings").select(
            "id, title, price, sales_count, created_at"
        ).eq("user_id", user["id"]).eq("is_deleted", False).execute()
        
        listings_data = listings.data or []
        total_sales = sum(l.get("sales_count", 0) for l in listings_data)
        total_revenue = sum(l.get("price", 0) * l.get("sales_count", 0) for l in listings_data)
        
        return {
            "total_listings": len(listings_data),
            "total_sales": total_sales,
            "total_revenue": total_revenue,
            "listings": listings_data
        }
    except Exception as e:
        logger.error(f"Failed to get seller stats: {e}")
        raise HTTPException(500, str(e))


@router.get("/deleted")
@limiter.limit("30/minute")
async def get_deleted(request: Request, user: dict = Depends(get_current_user)):
    """Get soft-deleted assets (trash)."""
    assets_repo = SupabaseAssetRepository()
    return await assets_repo.get_deleted_assets(user["id"])


@router.post("/{asset_id}/restore")
@limiter.limit("30/minute")
async def restore(request: Request, asset_id: str, user: dict = Depends(get_current_user)):
    """Restore a soft-deleted asset."""
    # v3.25: UA-MEDIUM-1 - Validate asset_id format
    validate_uuid_id(asset_id, "asset ID")

    assets_repo = SupabaseAssetRepository()

    result = await assets_repo.restore_asset(asset_id, user["id"])
    if not result:
        raise HTTPException(404, "Asset not found in trash")
    log_activity(user["id"], "restore_asset", {"asset_id": asset_id})
    return {"status": "ok", "asset": result}

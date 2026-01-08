"""
System Resources Management Router
Admin API for managing system assets (stickers, templates, etc.)

@module api.user.system_resources
@version 3.25

Changes:
- v3.25: Security improvements
  - SR-HIGH-1: Added rate limiting to all endpoints
  - SR-MEDIUM-1: Added search parameter length limit and sanitization
  - SR-MEDIUM-2: Added UUID validation for resource_id
  - SR-MEDIUM-3: Added resource_ids batch limit (max 100)
  - SR-LOW-1: Added type/category length limits
  - SR-LOW-2: Added page number limit

Features:
- CRUD operations for system resources
- File upload to Supabase Storage
- Audit logging for all changes
- Batch operations support
"""

from datetime import datetime, timezone
import re
import uuid

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query, Request
from typing import List, Optional

from dependencies import require_admin
from api.schemas.admin.system_resources import ResourceCreate, ResourceUpdate, ResourceBatchAction
from core.database import get_supabase_client
from infrastructure.rate_limiter import limiter
from domains.content.resource_helpers import (
    SYSTEM_ASSETS_BUCKET,
    ALLOWED_TYPES,
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE,
    log_resource_audit,
    get_image_dimensions,
)

supabase = get_supabase_client()

router = APIRouter(prefix="/system-resources", tags=["system-resources-v2"])


# =====================================================
# Constants (v3.25)
# =====================================================

# v3.25: SR-MEDIUM-2 - UUID validation pattern
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)

# v3.25: SR-MEDIUM-1 - Max search query length
MAX_SEARCH_LENGTH = 100

# v3.25: SR-MEDIUM-3 - Max batch size
MAX_BATCH_SIZE = 100


def validate_resource_id(resource_id: str) -> None:
    """v3.25: SR-MEDIUM-2 - Validate resource_id is UUID format."""
    if not UUID_PATTERN.match(resource_id):
        raise HTTPException(400, "Invalid resource ID format")


def sanitize_search(search: str) -> str:
    """v3.25: SR-MEDIUM-1 - Sanitize search query to prevent injection."""
    # Remove special PostgreSQL pattern characters
    return search.replace("%", "").replace("_", "").replace("\\", "")


# =====================================================
# API Endpoints
# =====================================================

@router.get("")
@limiter.limit("60/minute")  # v3.25: SR-HIGH-1
async def list_system_resources(
    request: Request,  # v3.25: Required for rate limiter
    type: Optional[str] = Query(None, max_length=50),  # v3.25: SR-LOW-1
    category: Optional[str] = Query(None, max_length=50),  # v3.25: SR-LOW-1
    is_active: Optional[bool] = None,
    search: Optional[str] = Query(None, max_length=MAX_SEARCH_LENGTH),  # v3.25: SR-MEDIUM-1
    page: int = Query(1, ge=1, le=1000),  # v3.25: SR-LOW-2
    limit: int = Query(50, ge=1, le=200),
    admin: dict = Depends(require_admin)
):
    """
    List all system resources (Admin view - includes inactive)

    v3.25: Added rate limiting and parameter validation.
    """
    offset = (page - 1) * limit

    query = supabase.table("system_resources").select("*", count="exact")

    if type:
        query = query.eq("type", type)
    if category:
        query = query.eq("category", category)
    if is_active is not None:
        query = query.eq("is_active", is_active)
    if search:
        # v3.25: SR-MEDIUM-1 - Sanitize search to prevent injection
        safe_search = sanitize_search(search)
        if safe_search:
            query = query.or_(f"name.ilike.%{safe_search}%,description.ilike.%{safe_search}%")

    query = query.order("sort_order", desc=False).order("created_at", desc=True)
    query = query.range(offset, offset + limit - 1)

    result = query.execute()

    return {
        "items": result.data or [],
        "total": result.count or 0,
        "page": page,
        "limit": limit,
        "has_more": (result.count or 0) > offset + limit
    }


@router.get("/stats")
@limiter.limit("30/minute")  # v3.25: SR-HIGH-1
async def get_resource_stats(request: Request, admin: dict = Depends(require_admin)):
    """
    Get statistics about system resources

    v3.25: Added rate limiting.
    """
    # Count active vs inactive
    active_count = supabase.table("system_resources")\
        .select("id", count="exact")\
        .eq("is_active", True)\
        .execute()
    
    inactive_count = supabase.table("system_resources")\
        .select("id", count="exact")\
        .eq("is_active", False)\
        .execute()
    
    # Group by type
    all_resources = supabase.table("system_resources")\
        .select("type, is_active")\
        .execute()
    
    type_breakdown = {}
    for r in all_resources.data or []:
        t = r.get("type", "unknown")
        if t not in type_breakdown:
            type_breakdown[t] = {"total": 0, "active": 0, "inactive": 0}
        type_breakdown[t]["total"] += 1
        if r.get("is_active"):
            type_breakdown[t]["active"] += 1
        else:
            type_breakdown[t]["inactive"] += 1
    
    return {
        "total": (active_count.count or 0) + (inactive_count.count or 0),
        "active": active_count.count or 0,
        "inactive": inactive_count.count or 0,
        "by_type": type_breakdown
    }


@router.get("/{resource_id}")
@limiter.limit("60/minute")  # v3.25: SR-HIGH-1
async def get_resource(request: Request, resource_id: str, admin: dict = Depends(require_admin)):
    """
    Get a single system resource by ID

    v3.25: Added rate limiting and UUID validation.
    """
    # v3.25: SR-MEDIUM-2 - Validate resource_id format
    validate_resource_id(resource_id)

    result = supabase.table("system_resources")\
        .select("*")\
        .eq("id", resource_id)\
        .single()\
        .execute()
    
    if not result.data:
        raise HTTPException(404, "Resource not found")
    
    return result.data


@router.post("")
@limiter.limit("30/minute")  # v3.25: SR-HIGH-1
async def create_resource(
    request: Request,  # v3.25: Required for rate limiter
    file: UploadFile = File(...),
    type: str = Form(...),
    category: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # Comma-separated
    allowed_tiers: Optional[str] = Form("free,starter,pro"),  # Comma-separated
    sort_order: int = Form(0),
    admin: dict = Depends(require_admin)
):
    """
    Create a new system resource with file upload

    v3.25: Added rate limiting.
    """
    # Validate type
    if type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Invalid type. Allowed: {ALLOWED_TYPES}")
    
    # Validate file type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, f"Invalid file type. Allowed: {ALLOWED_MIME_TYPES}")
    
    # Read and validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Maximum: {MAX_FILE_SIZE // 1024 // 1024}MB")
    
    # Generate unique filename
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
    filename = f"{type}/{category or 'general'}/{uuid.uuid4()}.{ext}"
    
    # Upload to Supabase Storage
    try:
        supabase.storage.from_(SYSTEM_ASSETS_BUCKET).upload(
            path=filename,
            file=contents,
            file_options={"content-type": file.content_type}
        )
        url = supabase.storage.from_(SYSTEM_ASSETS_BUCKET).get_public_url(filename)
    except Exception as e:
        raise HTTPException(500, f"Failed to upload file: {str(e)}")
    
    # Get image dimensions
    dimensions = get_image_dimensions(contents)
    
    # Parse tags and tiers
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    tier_list = [t.strip() for t in allowed_tiers.split(",")]
    
    # Create database record
    resource_data = {
        "type": type,
        "category": category,
        "name": name or file.filename,
        "description": description,
        "url": url,
        "thumbnail_url": url,  # Same as URL for now
        "tags": tag_list,
        "allowed_tiers": tier_list,
        "is_active": True,
        "sort_order": sort_order,
        "file_size": len(contents),
        "file_type": file.content_type,
        "dimensions": dimensions,
        "created_by": admin.get("id"),
        "metadata": {
            "original_filename": file.filename,
            "storage_path": filename
        }
    }
    
    result = supabase.table("system_resources").insert(resource_data).execute()
    
    if not result.data:
        raise HTTPException(500, "Failed to create resource record")
    
    # Audit log
    log_resource_audit(
        result.data[0]["id"],
        "create",
        {},
        resource_data,
        admin.get("id")
    )
    
    return result.data[0]


@router.patch("/{resource_id}")
@limiter.limit("30/minute")  # v3.25: SR-HIGH-1
async def update_resource(
    request: Request,  # v3.25: Required for rate limiter
    resource_id: str,
    updates: ResourceUpdate,
    admin: dict = Depends(require_admin)
):
    """
    Update a system resource metadata (not the file)

    v3.25: Added rate limiting and UUID validation.
    """
    # v3.25: SR-MEDIUM-2 - Validate resource_id format
    validate_resource_id(resource_id)

    # Get current data for audit
    current = supabase.table("system_resources")\
        .select("*")\
        .eq("id", resource_id)\
        .single()\
        .execute()
    
    if not current.data:
        raise HTTPException(404, "Resource not found")
    
    # Build update data
    update_data = {k: v for k, v in updates.dict().items() if v is not None}
    update_data["updated_by"] = admin.get("id")
    
    result = supabase.table("system_resources")\
        .update(update_data)\
        .eq("id", resource_id)\
        .execute()
    
    if not result.data:
        raise HTTPException(500, "Failed to update resource")
    
    # Audit log
    log_resource_audit(
        resource_id,
        "update",
        current.data,
        update_data,
        admin.get("id")
    )
    
    return result.data[0]


@router.post("/{resource_id}/replace")
@limiter.limit("10/minute")  # v3.25: SR-HIGH-1 (stricter for file uploads)
async def replace_resource_file(
    request: Request,  # v3.25: Required for rate limiter
    resource_id: str,
    file: UploadFile = File(...),
    admin: dict = Depends(require_admin)
):
    """
    Replace the file for an existing resource (keeps metadata)

    v3.25: Added rate limiting and UUID validation.
    """
    # v3.25: SR-MEDIUM-2 - Validate resource_id format
    validate_resource_id(resource_id)

    # Get current resource
    current = supabase.table("system_resources")\
        .select("*")\
        .eq("id", resource_id)\
        .single()\
        .execute()
    
    if not current.data:
        raise HTTPException(404, "Resource not found")
    
    # Validate file
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, f"Invalid file type. Allowed: {ALLOWED_MIME_TYPES}")
    
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Maximum: {MAX_FILE_SIZE // 1024 // 1024}MB")
    
    # Get current metadata and version history
    current_metadata = current.data.get("metadata", {})
    old_path = current_metadata.get("storage_path")
    old_url = current.data.get("url")
    version_history = current_metadata.get("version_history", [])
    
    # Add current version to history before replacing
    if old_path and old_url:
        version_history.append({
            "version": len(version_history) + 1,
            "url": old_url,
            "storage_path": old_path,
            "file_size": current.data.get("file_size"),
            "replaced_at": datetime.now(timezone.utc).isoformat(),
            "replaced_by": admin.get("id")
        })
    
    # Upload new file
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
    type_val = current.data.get("type", "misc")
    category = current.data.get("category", "general")
    filename = f"{type_val}/{category}/{uuid.uuid4()}.{ext}"
    
    try:
        supabase.storage.from_(SYSTEM_ASSETS_BUCKET).upload(
            path=filename,
            file=contents,
            file_options={"content-type": file.content_type}
        )
        url = supabase.storage.from_(SYSTEM_ASSETS_BUCKET).get_public_url(filename)
    except Exception as e:
        raise HTTPException(500, f"Failed to upload file: {str(e)}")
    
    # Get new dimensions
    dimensions = get_image_dimensions(contents)
    
    # Update record with full version history
    update_data = {
        "url": url,
        "thumbnail_url": url,
        "file_size": len(contents),
        "file_type": file.content_type,
        "dimensions": dimensions,
        "updated_by": admin.get("id"),
        "metadata": {
            **current_metadata,
            "original_filename": file.filename,
            "storage_path": filename,
            "current_version": len(version_history) + 1,
            "version_history": version_history
        }
    }
    
    result = supabase.table("system_resources")\
        .update(update_data)\
        .eq("id", resource_id)\
        .execute()
    
    # Audit log
    log_resource_audit(
        resource_id,
        "replace_file",
        {"url": current.data.get("url")},
        {"url": url},
        admin.get("id")
    )
    
    return result.data[0]


@router.delete("/{resource_id}")
@limiter.limit("30/minute")  # v3.25: SR-HIGH-1
async def delete_resource(
    request: Request,  # v3.25: Required for rate limiter
    resource_id: str,
    admin: dict = Depends(require_admin)
):
    """
    Delete a system resource (soft delete only)

    v3.18: Permanent delete is disabled for security.
    Files are only deactivated, not removed from storage.
    Use scheduled cleanup tasks for actual file removal.

    v3.25: Added rate limiting and UUID validation.
    """
    # v3.25: SR-MEDIUM-2 - Validate resource_id format
    validate_resource_id(resource_id)

    # Get current data
    current = supabase.table("system_resources")\
        .select("*")\
        .eq("id", resource_id)\
        .single()\
        .execute()
    
    if not current.data:
        raise HTTPException(404, "Resource not found")
    
    # v3.18: Only soft delete (deactivate) - no permanent delete allowed
    supabase.table("system_resources")\
        .update({
            "is_active": False, 
            "updated_by": admin.get("id"),
            "updated_at": "now()"
        })\
        .eq("id", resource_id)\
        .execute()
    
    log_resource_audit(resource_id, "deactivate", {"is_active": True}, {"is_active": False}, admin.get("id"))
    
    return {"message": "Resource deactivated (soft delete)", "id": resource_id}


@router.post("/batch")
@limiter.limit("10/minute")  # v3.25: SR-HIGH-1 (stricter for batch ops)
async def batch_action(
    request: Request,  # v3.25: Required for rate limiter
    action: ResourceBatchAction,
    admin: dict = Depends(require_admin)
):
    """
    Perform batch actions on multiple resources

    v3.25: Added rate limiting and batch size validation.
    """
    # v3.25: SR-MEDIUM-3 - Validate batch size
    if len(action.resource_ids) > MAX_BATCH_SIZE:
        raise HTTPException(400, f"Batch size exceeds maximum of {MAX_BATCH_SIZE}")

    # v3.25: Validate all resource_ids are UUID format
    for rid in action.resource_ids:
        if not UUID_PATTERN.match(rid):
            raise HTTPException(400, f"Invalid resource ID format: {rid}")

    if action.action == "activate":
        supabase.table("system_resources")\
            .update({"is_active": True, "updated_by": admin.get("id")})\
            .in_("id", action.resource_ids)\
            .execute()
        return {"message": f"Activated {len(action.resource_ids)} resources"}
    
    elif action.action == "deactivate":
        supabase.table("system_resources")\
            .update({"is_active": False, "updated_by": admin.get("id")})\
            .in_("id", action.resource_ids)\
            .execute()
        return {"message": f"Deactivated {len(action.resource_ids)} resources"}
    
    elif action.action == "delete":
        # Soft delete
        supabase.table("system_resources")\
            .update({"is_active": False, "updated_by": admin.get("id")})\
            .in_("id", action.resource_ids)\
            .execute()
        return {"message": f"Deleted {len(action.resource_ids)} resources"}
    
    else:
        raise HTTPException(400, f"Unknown action: {action.action}")


@router.get("/{resource_id}/audit-log")
@limiter.limit("30/minute")  # v3.25: SR-HIGH-1
async def get_resource_audit_log(
    request: Request,  # v3.25: Required for rate limiter
    resource_id: str,
    limit: int = Query(50, ge=1, le=100),  # v3.25: Reduced max to 100
    admin: dict = Depends(require_admin)
):
    """
    Get audit log for a specific resource

    v3.25: Added rate limiting and UUID validation.
    """
    # v3.25: SR-MEDIUM-2 - Validate resource_id format
    validate_resource_id(resource_id)

    result = supabase.table("system_resource_audit_logs")\
        .select("*")\
        .eq("resource_id", resource_id)\
        .order("changed_at", desc=True)\
        .limit(limit)\
        .execute()
    
    return result.data or []

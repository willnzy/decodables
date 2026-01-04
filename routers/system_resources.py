"""
System Resources Management Router
Admin API for managing system assets (stickers, templates, etc.)

Features:
- CRUD operations for system resources
- File upload to Supabase Storage
- Audit logging for all changes
- Batch operations support
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

from dependencies import get_current_user, require_admin
from services.db_service import supabase

router = APIRouter(prefix="/api/admin/system-resources", tags=["Admin - System Resources"])

# =====================================================
# Constants
# =====================================================

SYSTEM_ASSETS_BUCKET = "md-system-assets"

ALLOWED_TYPES = ["sticker", "template", "background", "frame", "icon", "pattern"]
ALLOWED_MIME_TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif", "image/svg+xml"]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# =====================================================
# Schemas
# =====================================================

class ResourceCreate(BaseModel):
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
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    allowed_tiers: Optional[List[str]] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    metadata: Optional[dict] = None

class ResourceBatchAction(BaseModel):
    resource_ids: List[str]
    action: str  # "activate", "deactivate", "delete"

# =====================================================
# Helper Functions
# =====================================================

def log_resource_audit(
    resource_id: str,
    action: str,
    old_data: dict,
    new_data: dict,
    changed_by: str
):
    """Log resource changes for audit trail"""
    try:
        supabase.table("system_resource_audit_logs").insert({
            "resource_id": resource_id,
            "action": action,
            "old_data": old_data,
            "new_data": new_data,
            "changed_by": changed_by
        }).execute()
    except Exception as e:
        print(f"[AUDIT] Failed to log: {e}")

def get_image_dimensions(file_bytes: bytes) -> dict:
    """Extract image dimensions from file bytes"""
    try:
        from PIL import Image
        from io import BytesIO
        img = Image.open(BytesIO(file_bytes))
        return {"width": img.width, "height": img.height}
    except:
        return None

# =====================================================
# API Endpoints
# =====================================================

@router.get("")
async def list_system_resources(
    type: Optional[str] = None,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    admin: dict = Depends(require_admin)
):
    """
    List all system resources (Admin view - includes inactive)
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
        query = query.or_(f"name.ilike.%{search}%,description.ilike.%{search}%")
    
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
async def get_resource_stats(admin: dict = Depends(require_admin)):
    """
    Get statistics about system resources
    """
    # Count by type
    type_stats = supabase.table("system_resources")\
        .select("type", count="exact")\
        .execute()
    
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
async def get_resource(resource_id: str, admin: dict = Depends(require_admin)):
    """
    Get a single system resource by ID
    """
    result = supabase.table("system_resources")\
        .select("*")\
        .eq("id", resource_id)\
        .single()\
        .execute()
    
    if not result.data:
        raise HTTPException(404, "Resource not found")
    
    return result.data


@router.post("")
async def create_resource(
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
async def update_resource(
    resource_id: str,
    updates: ResourceUpdate,
    admin: dict = Depends(require_admin)
):
    """
    Update a system resource metadata (not the file)
    """
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
async def replace_resource_file(
    resource_id: str,
    file: UploadFile = File(...),
    admin: dict = Depends(require_admin)
):
    """
    Replace the file for an existing resource (keeps metadata)
    """
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
    
    # Delete old file from storage (optional, keeps history)
    old_path = current.data.get("metadata", {}).get("storage_path")
    
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
    
    # Update record
    update_data = {
        "url": url,
        "thumbnail_url": url,
        "file_size": len(contents),
        "file_type": file.content_type,
        "dimensions": dimensions,
        "updated_by": admin.get("id"),
        "metadata": {
            **current.data.get("metadata", {}),
            "original_filename": file.filename,
            "storage_path": filename,
            "previous_path": old_path
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
async def delete_resource(
    resource_id: str,
    permanent: bool = Query(False, description="Permanently delete (including file)"),
    admin: dict = Depends(require_admin)
):
    """
    Delete a system resource (soft delete by default)
    """
    # Get current data
    current = supabase.table("system_resources")\
        .select("*")\
        .eq("id", resource_id)\
        .single()\
        .execute()
    
    if not current.data:
        raise HTTPException(404, "Resource not found")
    
    if permanent:
        # Delete from storage
        storage_path = current.data.get("metadata", {}).get("storage_path")
        if storage_path:
            try:
                supabase.storage.from_(SYSTEM_ASSETS_BUCKET).remove([storage_path])
            except Exception as e:
                print(f"[WARN] Failed to delete file from storage: {e}")
        
        # Delete from database
        supabase.table("system_resources").delete().eq("id", resource_id).execute()
        
        # Audit log
        log_resource_audit(resource_id, "permanent_delete", current.data, {}, admin.get("id"))
        
        return {"message": "Resource permanently deleted", "id": resource_id}
    else:
        # Soft delete (deactivate)
        supabase.table("system_resources")\
            .update({"is_active": False, "updated_by": admin.get("id")})\
            .eq("id", resource_id)\
            .execute()
        
        log_resource_audit(resource_id, "deactivate", {"is_active": True}, {"is_active": False}, admin.get("id"))
        
        return {"message": "Resource deactivated", "id": resource_id}


@router.post("/batch")
async def batch_action(
    action: ResourceBatchAction,
    admin: dict = Depends(require_admin)
):
    """
    Perform batch actions on multiple resources
    """
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
async def get_resource_audit_log(
    resource_id: str,
    limit: int = Query(50, ge=1, le=200),
    admin: dict = Depends(require_admin)
):
    """
    Get audit log for a specific resource
    """
    result = supabase.table("system_resource_audit_logs")\
        .select("*")\
        .eq("resource_id", resource_id)\
        .order("changed_at", desc=True)\
        .limit(limit)\
        .execute()
    
    return result.data or []

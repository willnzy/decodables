"""
System Resources Management Router - Admin API (v3.0.0)
Admin API for managing system assets (stickers, templates, etc.)

@module api.user.system_resources
@version 3.0.0

Changes:
- v3.0.0: DDD architecture upgrade - Full CQRS pattern
  - Created SystemResourcesService v1.0.0 with 9 business methods
  - Added 4 Query Handlers (List, GetById, Stats, AuditLog)
  - Added 5 Command Handlers (Create, Update, Replace, Delete, Batch)
  - Eliminated direct Supabase calls from API layer
  - Moved all business logic to Service layer
  - Improved testability and maintainability

- v3.25: Security improvements (inherited)
  - SR-HIGH-1: Rate limiting on all endpoints
  - SR-MEDIUM-1: Search parameter sanitization
  - SR-MEDIUM-2: UUID validation for resource_id
  - SR-MEDIUM-3: Batch size limit (max 100)
  - SR-LOW-1: Type/category length limits
  - SR-LOW-2: Page number limit

Features:
- CRUD operations for system resources
- File upload to Supabase Storage
- Audit logging for all changes
- Batch operations support
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query, Request
from typing import Optional
import re

from dependencies import require_admin
from container import get_container
from core.middleware import validate_file_size  # P3-005: File upload size validation
from application.queries.system_resources import (
    ListSystemResourcesQuery,
    GetSystemResourceQuery,
    GetResourceStatsQuery,
    GetAuditLogQuery,
)
from application.commands.system_resources import (
    CreateSystemResourceCommand,
    UpdateSystemResourceCommand,
    ReplaceResourceFileCommand,
    DeleteSystemResourceCommand,
    BatchOperationCommand,
)
from api.schemas.admin.system_resources import ResourceUpdate, ResourceBatchAction
from infrastructure.rate_limiter import limiter

router = APIRouter(prefix="/system-resources", tags=["system-resources-v3"])


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
    List all system resources (Admin view - includes inactive).

    v3.0.0: Now uses ListSystemResourcesHandler (Container pattern).
    v3.25: Added rate limiting and parameter validation.
    """
    # v3.25: SR-MEDIUM-1 - Sanitize search
    safe_search = sanitize_search(search) if search else None

    container = get_container()
    handler = container.list_system_resources_handler

    query = ListSystemResourcesQuery(
        resource_type=type,
        category=category,
        is_active=is_active,
        search=safe_search,
        page=page,
        limit=limit,
    )

    result = await handler.handle(query)

    return {
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "limit": result.limit,
        "has_more": result.has_more,
    }


@router.get("/stats")
@limiter.limit("30/minute")  # v3.25: SR-HIGH-1
async def get_resource_stats(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """
    Get statistics about system resources.

    v3.0.0: Now uses GetResourceStatsHandler (Container pattern).
    v3.25: Added rate limiting.
    """
    container = get_container()
    handler = container.get_system_resource_stats_handler

    query = GetResourceStatsQuery()
    result = await handler.handle(query)

    return result.stats


@router.get("/{resource_id}")
@limiter.limit("60/minute")  # v3.25: SR-HIGH-1
async def get_resource(
    request: Request,
    resource_id: str,
    admin: dict = Depends(require_admin)
):
    """
    Get a single system resource by ID.

    v3.0.0: Now uses GetSystemResourceHandler (Container pattern).
    v3.25: Added rate limiting and UUID validation.
    """
    # v3.25: SR-MEDIUM-2 - Validate resource_id format
    validate_resource_id(resource_id)

    container = get_container()
    handler = container.get_system_resource_handler

    query = GetSystemResourceQuery(resource_id=resource_id)
    result = await handler.handle(query)

    if not result.resource:
        raise HTTPException(404, "Resource not found")

    return result.resource


@router.post("")
@limiter.limit("30/minute")  # v3.25: SR-HIGH-1
async def create_resource(
    request: Request,  # v3.25: Required for rate limiter
    file: UploadFile = Depends(validate_file_size),  # P3-005: File size validation (10MB limit)
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
    Create a new system resource with file upload.

    v3.0.0: Now uses CreateSystemResourceHandler (Container pattern).
    v3.25: Added rate limiting.
    P3-005: Added 10MB file size limit via validate_file_size dependency.
    """
    container = get_container()
    handler = container.create_system_resource_handler

    command = CreateSystemResourceCommand(
        file=file,
        type=type,
        category=category,
        name=name,
        description=description,
        tags=tags,
        allowed_tiers=allowed_tiers,
        sort_order=sort_order,
        admin_id=admin.get("id"),
    )

    result = await handler.handle(command)

    return result.result_data


@router.patch("/{resource_id}")
@limiter.limit("30/minute")  # v3.25: SR-HIGH-1
async def update_resource(
    request: Request,  # v3.25: Required for rate limiter
    resource_id: str,
    updates: ResourceUpdate,
    admin: dict = Depends(require_admin)
):
    """
    Update a system resource metadata (not the file).

    v3.0.0: Now uses UpdateSystemResourceHandler (Container pattern).
    v3.25: Added rate limiting and UUID validation.
    """
    # v3.25: SR-MEDIUM-2 - Validate resource_id format
    validate_resource_id(resource_id)

    container = get_container()
    handler = container.update_system_resource_handler

    command = UpdateSystemResourceCommand(
        resource_id=resource_id,
        name=updates.name,
        description=updates.description,
        category=updates.category,
        tags=updates.tags,
        allowed_tiers=updates.allowed_tiers,
        sort_order=updates.sort_order,
        is_active=updates.is_active,
        metadata=updates.metadata,
        admin_id=admin.get("id"),
    )

    result = await handler.handle(command)

    return result.result_data


@router.post("/{resource_id}/replace")
@limiter.limit("10/minute")  # v3.25: SR-HIGH-1 (stricter for file uploads)
async def replace_resource_file(
    request: Request,  # v3.25: Required for rate limiter
    resource_id: str,
    file: UploadFile = Depends(validate_file_size),  # P3-005: File size validation (10MB limit)
    admin: dict = Depends(require_admin)
):
    """
    Replace the file for an existing resource (keeps metadata).

    v3.0.0: Now uses ReplaceResourceFileHandler (Container pattern).
    v3.25: Added rate limiting and UUID validation.
    P3-005: Added 10MB file size limit via validate_file_size dependency.
    """
    # v3.25: SR-MEDIUM-2 - Validate resource_id format
    validate_resource_id(resource_id)

    container = get_container()
    handler = container.replace_resource_file_handler

    command = ReplaceResourceFileCommand(
        resource_id=resource_id,
        file=file,
        admin_id=admin.get("id"),
    )

    result = await handler.handle(command)

    return result.result_data


@router.delete("/{resource_id}")
@limiter.limit("30/minute")  # v3.25: SR-HIGH-1
async def delete_resource(
    request: Request,  # v3.25: Required for rate limiter
    resource_id: str,
    admin: dict = Depends(require_admin)
):
    """
    Delete a system resource (soft delete only).

    v3.18: Permanent delete is disabled for security.
    Files are only deactivated, not removed from storage.
    Use scheduled cleanup tasks for actual file removal.

    v3.0.0: Now uses DeleteSystemResourceHandler (Container pattern).
    v3.25: Added rate limiting and UUID validation.
    """
    # v3.25: SR-MEDIUM-2 - Validate resource_id format
    validate_resource_id(resource_id)

    container = get_container()
    handler = container.delete_system_resource_handler

    command = DeleteSystemResourceCommand(
        resource_id=resource_id,
        admin_id=admin.get("id"),
    )

    result = await handler.handle(command)

    return result.result_data


@router.post("/batch")
@limiter.limit("10/minute")  # v3.25: SR-HIGH-1 (stricter for batch ops)
async def batch_action(
    request: Request,  # v3.25: Required for rate limiter
    action: ResourceBatchAction,
    admin: dict = Depends(require_admin)
):
    """
    Perform batch actions on multiple resources.

    v3.0.0: Now uses BatchOperationHandler (Container pattern).
    v3.25: Added rate limiting and batch size validation.
    """
    # v3.25: SR-MEDIUM-3 - Validate batch size
    if len(action.resource_ids) > MAX_BATCH_SIZE:
        raise HTTPException(400, f"Batch size exceeds maximum of {MAX_BATCH_SIZE}")

    # v3.25: Validate all resource_ids are UUID format
    for rid in action.resource_ids:
        if not UUID_PATTERN.match(rid):
            raise HTTPException(400, f"Invalid resource ID format: {rid}")

    container = get_container()
    handler = container.batch_operation_handler

    command = BatchOperationCommand(
        operation=action.action,
        resource_ids=action.resource_ids,
        admin_id=admin.get("id"),
    )

    result = await handler.handle(command)

    return result.result_data


@router.get("/{resource_id}/audit-log")
@limiter.limit("30/minute")  # v3.25: SR-HIGH-1
async def get_resource_audit_log(
    request: Request,  # v3.25: Required for rate limiter
    resource_id: str,
    limit: int = Query(50, ge=1, le=100),  # v3.25: Reduced max to 100
    admin: dict = Depends(require_admin)
):
    """
    Get audit log for a specific resource.

    v3.0.0: Now uses GetAuditLogHandler (Container pattern).
    v3.25: Added rate limiting and UUID validation.
    """
    # v3.25: SR-MEDIUM-2 - Validate resource_id format
    validate_resource_id(resource_id)

    container = get_container()
    handler = container.get_audit_log_handler

    query = GetAuditLogQuery(
        resource_id=resource_id,
        limit=limit
    )

    result = await handler.handle(query)

    return result.audit_log

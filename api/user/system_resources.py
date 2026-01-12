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
    type: Optional[str] = Query(None, max_length=50, description="Filter by resource type (e.g., 'sticker', 'template')"),
    category: Optional[str] = Query(None, max_length=50, description="Filter by category (e.g., 'animals', 'holidays')"),
    is_active: Optional[bool] = Query(None, description="Filter by active status (true/false/null for all)"),
    search: Optional[str] = Query(None, max_length=MAX_SEARCH_LENGTH, description="Search by name or description (max 200 chars)"),
    page: int = Query(1, ge=1, le=1000, description="Page number (1-1000, default: 1)"),
    limit: int = Query(50, ge=1, le=200, description="Items per page (1-200, default: 50)"),
    admin: dict = Depends(require_admin)
):
    """
    List all system resources with filtering and search (Admin view).

    Retrieves system-wide resources such as stickers, templates, decorations, and
    backgrounds that are available to users based on their tier. Admin view includes
    inactive resources for management purposes. Supports filtering, search, and pagination.

    v3.0.0: Uses ListSystemResourcesHandler (Container pattern).
    v3.25: Added rate limiting and parameter validation (SR-HIGH-1, SR-LOW-1/2, SR-MEDIUM-1).

    Args:
        type: Optional filter by resource type (max 50 chars)
            Common values: "sticker", "template", "decoration", "background", "font"
        category: Optional filter by category (max 50 chars)
            Examples: "animals", "holidays", "school", "nature"
        is_active: Optional filter by active status
            - true: Only active resources (visible to users)
            - false: Only inactive resources (hidden)
            - null: All resources (default)
        search: Optional search query (max 200 chars)
            Searches in: name, description, tags
            Sanitized for SQL injection prevention
        page: Page number for pagination (default: 1, max: 1000)
        limit: Items per page (default: 50, max: 200)

    Returns:
        Dict containing:
            - items: List of resource objects including:
                - id: Resource UUID
                - type: Resource type
                - category: Category classification
                - name: Display name
                - description: Resource description
                - file_url: Download URL for resource file
                - thumbnail_url: Preview thumbnail URL
                - allowed_tiers: List of tiers with access (["free", "starter", "pro"])
                - tags: List of searchable tags
                - sort_order: Display order priority
                - is_active: Whether resource is visible to users
                - created_at: Creation timestamp
                - updated_at: Last modification timestamp
            - total: Total number of resources (respecting filters)
            - page: Current page number
            - limit: Items per page
            - has_more: Whether more pages exist

    Raises:
        400: Invalid type/category length (>50 chars) or search query (>200 chars)
        401: Unauthorized (not admin)
        429: Rate limit exceeded (max 60 requests per minute)
        500: Database error or service unavailable

    Security:
        - Admin role required
        - Rate limit: 60 requests per minute
        - Search query sanitized against SQL injection
        - Parameter length validation (type/category: 50, search: 200)
        - Page number limited to 1000 (prevent excessive queries)

    Example:
        GET /api/v3/user/system-resources?type=sticker&category=animals&is_active=true&limit=20

        Response:
        {
            "items": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "type": "sticker",
                    "category": "animals",
                    "name": "Cute Cat",
                    "description": "A playful cat sticker",
                    "file_url": "https://storage.example.com/stickers/cat_01.png",
                    "thumbnail_url": "https://storage.example.com/thumbnails/cat_01.png",
                    "allowed_tiers": ["free", "starter", "pro"],
                    "tags": ["cat", "animal", "cute"],
                    "sort_order": 100,
                    "is_active": true,
                    "created_at": "2026-01-01T10:00:00Z",
                    "updated_at": "2026-01-10T15:30:00Z"
                }
            ],
            "total": 1,
            "page": 1,
            "limit": 20,
            "has_more": false
        }
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
    type: str = Form(..., description="Resource type (required, e.g., 'sticker', 'template')"),
    category: Optional[str] = Form(None, description="Category classification (optional, e.g., 'animals', 'holidays')"),
    name: Optional[str] = Form(None, description="Display name (optional, defaults to filename)"),
    description: Optional[str] = Form(None, description="Resource description (optional)"),
    tags: Optional[str] = Form(None, description="Comma-separated tags (optional, e.g., 'cat,animal,cute')"),
    allowed_tiers: Optional[str] = Form("free,starter,pro", description="Comma-separated tiers with access (default: all)"),
    sort_order: int = Form(0, description="Display order priority (default: 0, higher = shown first)"),
    admin: dict = Depends(require_admin)
):
    """
    Create a new system resource with file upload.

    Uploads a new resource file (image, template, font, etc.) to Supabase Storage
    and creates a corresponding database record. The resource becomes available
    to users based on tier permissions. Supports tier-based access control.

    v3.0.0: Uses CreateSystemResourceHandler (Container pattern).
    v3.25: Added rate limiting (SR-HIGH-1).
    P3-005: Added 10MB file size limit via validate_file_size dependency.

    Args:
        file: Resource file to upload (required, max 10MB)
            Supported formats depend on type:
                - sticker: PNG, JPG, SVG
                - template: JSON (canvas data)
                - background: PNG, JPG
                - font: TTF, OTF, WOFF
        type: Resource type (required)
            Common values: "sticker", "template", "decoration", "background", "font"
        category: Category classification (optional)
            Examples: "animals", "holidays", "school", "nature", "abstract"
        name: Display name (optional)
            If not provided, uses uploaded filename
        description: Human-readable description (optional)
            Displayed in resource library
        tags: Comma-separated searchable tags (optional)
            Format: "cat,animal,cute,cartoon"
        allowed_tiers: Comma-separated tier access list (default: "free,starter,pro")
            Valid values: "free", "starter", "pro"
            Examples:
                - "pro": Pro users only
                - "starter,pro": Starter and Pro users
                - "free,starter,pro": All users (default)
        sort_order: Display priority (default: 0)
            Higher numbers appear first in lists
            Range: -1000 to 1000

    Returns:
        Dict containing:
            - success: true if resource created
            - resource_id: UUID of created resource
            - file_url: Public URL for resource file
            - thumbnail_url: Public URL for thumbnail (if generated)
            - message: Confirmation message

    Raises:
        400: Invalid file type, file too large (>10MB), or validation error
        401: Unauthorized (not admin)
        413: File size exceeds 10MB limit (validated by validate_file_size)
        429: Rate limit exceeded (max 30 requests per minute)
        500: Upload failed, storage error, or database error

    Security:
        - Admin role required
        - Rate limit: 30 requests per minute
        - File size limited to 10MB (DoS prevention, P3-005)
        - File type validation (MIME type check)
        - Uploaded to isolated Supabase bucket
        - Audit log created with admin_id

    Example:
        POST /api/v3/user/system-resources
        Content-Type: multipart/form-data

        file: cute_cat.png (binary data)
        type: sticker
        category: animals
        name: Cute Cat Sticker
        description: A playful cat for decorating decodables
        tags: cat,animal,cute,cartoon
        allowed_tiers: free,starter,pro
        sort_order: 100

        Response:
        {
            "success": true,
            "resource_id": "550e8400-e29b-41d4-a716-446655440000",
            "file_url": "https://storage.example.com/resources/550e8400.../cute_cat.png",
            "thumbnail_url": "https://storage.example.com/thumbnails/550e8400.../thumb.png",
            "message": "Resource created successfully"
        }
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

    # ✅ Task 9 - Phase 2: Log resource deletion to audit trail
    try:
        from core.database import get_async_db_client
        from infrastructure.repositories.admin_repository import SupabaseAdminUsersRepository

        db_client = await get_async_db_client()
        admin_repo = SupabaseAdminUsersRepository(db_client)
        await admin_repo.admin_log_operation(
            admin_id=admin["id"],
            operation_type="resource_delete",
            target_type="system_resource",
            target_id=resource_id,
            details="System resource deleted (soft delete)",
            source="api",
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to log resource deletion: {e}")

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

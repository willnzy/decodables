"""
SystemResources Service - Business logic for Admin System Resources management.

@module domains.content.system_resources_service
@version 1.0.0

Purpose:
- System resource CRUD business logic
- File upload/delete operations (Supabase Storage)
- Audit logging standardization
- Image dimensions calculation
- Batch operations
"""

import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from fastapi import UploadFile, HTTPException

from infrastructure.repositories.system_resources_admin_repository import (
    SupabaseSystemResourcesAdminRepository
)
from domains.content.resource_helpers import (
    SYSTEM_ASSETS_BUCKET,
    ALLOWED_TYPES,
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE,
    log_resource_audit,
    get_image_dimensions,
)


class SystemResourcesService:
    """
    Domain service for System Resources management.

    Handles all business logic for admin system resource operations.
    """

    def __init__(
        self,
        repository: SupabaseSystemResourcesAdminRepository,
        storage_client
    ):
        """
        Initialize service.

        Args:
            repository: Data access repository
            storage_client: Supabase client for storage operations
        """
        self.repository = repository
        self.storage = storage_client

    # ==========================================
    # Query Methods
    # ==========================================

    async def list_resources(
        self,
        resource_type: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List resources with filters and pagination.

        Args:
            resource_type: Filter by type
            category: Filter by category
            is_active: Filter by active status
            search: Search query (pre-sanitized)
            limit: Max items
            offset: Skip items

        Returns:
            Tuple of (items list, total count)
        """
        return await self.repository.list_resources(
            resource_type=resource_type,
            category=category,
            is_active=is_active,
            search=search,
            limit=limit,
            offset=offset,
        )

    async def get_resource(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """
        Get single resource by ID.

        Args:
            resource_id: Resource UUID

        Returns:
            Resource dict or None
        """
        return await self.repository.get_by_id(resource_id)

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get resource statistics.

        Returns:
            Stats dict with total, active, inactive, by_type
        """
        return await self.repository.get_stats()

    async def get_audit_log(
        self,
        resource_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get audit log for a resource.

        Args:
            resource_id: Resource UUID
            limit: Max items

        Returns:
            List of audit log entries
        """
        return await self.repository.get_audit_log(resource_id, limit)

    # ==========================================
    # Command Methods
    # ==========================================

    async def create_resource(
        self,
        file: UploadFile,
        resource_data: Dict[str, Any],
        admin_id: str,
    ) -> Dict[str, Any]:
        """
        Create resource with file upload.

        Business logic:
        1. Validate file (type, size)
        2. Upload to Supabase Storage
        3. Get image dimensions
        4. Save to database
        5. Log audit

        Args:
            file: Uploaded file
            resource_data: Resource metadata
            admin_id: Admin ID performing action

        Returns:
            Created resource dict

        Raises:
            HTTPException: Validation or upload errors
        """
        resource_type = resource_data.get("type")
        category = resource_data.get("category")

        # 1. Validate type
        if resource_type not in ALLOWED_TYPES:
            raise HTTPException(400, f"Invalid type. Allowed: {ALLOWED_TYPES}")

        # 2. Validate file type
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(400, f"Invalid file type. Allowed: {ALLOWED_MIME_TYPES}")

        # 3. Read and validate file size
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                400,
                f"File too large. Maximum: {MAX_FILE_SIZE // 1024 // 1024}MB"
            )

        # 4. Generate unique filename
        ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
        filename = f"{resource_type}/{category or 'general'}/{uuid.uuid4()}.{ext}"

        # 5. Upload to Supabase Storage
        try:
            self.storage.storage.from_(SYSTEM_ASSETS_BUCKET).upload(
                path=filename,
                file=contents,
                file_options={"content-type": file.content_type}
            )
            url = self.storage.storage.from_(SYSTEM_ASSETS_BUCKET).get_public_url(filename)
        except Exception as e:
            raise HTTPException(500, f"Failed to upload file: {str(e)}")

        # 6. Get image dimensions
        dimensions = get_image_dimensions(contents)

        # 7. Parse tags and tiers
        tags = resource_data.get("tags", "")
        tag_list = [t.strip() for t in tags.split(",")] if tags else []

        allowed_tiers = resource_data.get("allowed_tiers", "free,starter,pro")
        tier_list = [t.strip() for t in allowed_tiers.split(",")]

        # 8. Build database record
        db_data = {
            "type": resource_type,
            "category": category,
            "name": resource_data.get("name") or file.filename,
            "description": resource_data.get("description"),
            "url": url,
            "thumbnail_url": url,
            "tags": tag_list,
            "allowed_tiers": tier_list,
            "is_active": True,
            "sort_order": resource_data.get("sort_order", 0),
            "file_size": len(contents),
            "file_type": file.content_type,
            "dimensions": dimensions,
            "created_by": admin_id,
            "metadata": {
                "original_filename": file.filename,
                "storage_path": filename
            }
        }

        # 9. Create in database
        result = await self.repository.create(db_data)

        # 10. Audit log
        log_resource_audit(
            result["id"],
            "create",
            {},
            db_data,
            admin_id
        )

        return result

    async def update_resource(
        self,
        resource_id: str,
        updates: Dict[str, Any],
        admin_id: str,
    ) -> Dict[str, Any]:
        """
        Update resource metadata (not file).

        Args:
            resource_id: Resource UUID
            updates: Fields to update
            admin_id: Admin ID

        Returns:
            Updated resource dict

        Raises:
            HTTPException: If resource not found
        """
        # Get current data for audit
        current = await self.repository.get_by_id(resource_id)
        if not current:
            raise HTTPException(404, "Resource not found")

        # Add updated_by
        update_data = {k: v for k, v in updates.items() if v is not None}
        update_data["updated_by"] = admin_id

        # Update in database
        result = await self.repository.update(resource_id, update_data)

        # Audit log
        log_resource_audit(
            resource_id,
            "update",
            current,
            update_data,
            admin_id
        )

        return result

    async def replace_file(
        self,
        resource_id: str,
        new_file: UploadFile,
        admin_id: str,
    ) -> Dict[str, Any]:
        """
        Replace resource file (keeps metadata).

        Business logic:
        1. Get current resource
        2. Validate new file
        3. Upload new file
        4. Update database with version history
        5. Log audit

        Args:
            resource_id: Resource UUID
            new_file: New file to upload
            admin_id: Admin ID

        Returns:
            Updated resource dict

        Raises:
            HTTPException: Validation or not found errors
        """
        # 1. Get current resource
        current = await self.repository.get_by_id(resource_id)
        if not current:
            raise HTTPException(404, "Resource not found")

        # 2. Validate file
        if new_file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(400, f"Invalid file type. Allowed: {ALLOWED_MIME_TYPES}")

        contents = await new_file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                400,
                f"File too large. Maximum: {MAX_FILE_SIZE // 1024 // 1024}MB"
            )

        # 3. Get current metadata and version history
        current_metadata = current.get("metadata", {})
        old_path = current_metadata.get("storage_path")
        old_url = current.get("url")
        version_history = current_metadata.get("version_history", [])

        # 4. Add current version to history
        if old_path and old_url:
            version_history.append({
                "version": len(version_history) + 1,
                "url": old_url,
                "storage_path": old_path,
                "file_size": current.get("file_size"),
                "replaced_at": datetime.now(timezone.utc).isoformat(),
                "replaced_by": admin_id
            })

        # 5. Upload new file
        ext = new_file.filename.split('.')[-1] if '.' in new_file.filename else 'png'
        type_val = current.get("type", "misc")
        category = current.get("category", "general")
        filename = f"{type_val}/{category}/{uuid.uuid4()}.{ext}"

        try:
            self.storage.storage.from_(SYSTEM_ASSETS_BUCKET).upload(
                path=filename,
                file=contents,
                file_options={"content-type": new_file.content_type}
            )
            url = self.storage.storage.from_(SYSTEM_ASSETS_BUCKET).get_public_url(filename)
        except Exception as e:
            raise HTTPException(500, f"Failed to upload file: {str(e)}")

        # 6. Get new dimensions
        dimensions = get_image_dimensions(contents)

        # 7. Update database with version history
        update_data = {
            "url": url,
            "thumbnail_url": url,
            "file_size": len(contents),
            "file_type": new_file.content_type,
            "dimensions": dimensions,
            "updated_by": admin_id,
            "metadata": {
                **current_metadata,
                "original_filename": new_file.filename,
                "storage_path": filename,
                "current_version": len(version_history) + 1,
                "version_history": version_history
            }
        }

        result = await self.repository.update(resource_id, update_data)

        # 8. Audit log
        log_resource_audit(
            resource_id,
            "replace_file",
            {"url": current.get("url")},
            {"url": url},
            admin_id
        )

        return result

    async def delete_resource(
        self,
        resource_id: str,
        admin_id: str,
    ) -> Dict[str, str]:
        """
        Soft delete resource (deactivate only).

        Args:
            resource_id: Resource UUID
            admin_id: Admin ID

        Returns:
            Status message dict

        Raises:
            HTTPException: If resource not found
        """
        # Check if exists
        current = await self.repository.get_by_id(resource_id)
        if not current:
            raise HTTPException(404, "Resource not found")

        # Soft delete (deactivate)
        await self.repository.soft_delete(resource_id, admin_id)

        # Audit log
        log_resource_audit(
            resource_id,
            "deactivate",
            {"is_active": True},
            {"is_active": False},
            admin_id
        )

        return {"message": "Resource deactivated (soft delete)", "id": resource_id}

    async def batch_operation(
        self,
        operation: str,
        resource_ids: List[str],
        admin_id: str,
    ) -> Dict[str, str]:
        """
        Batch operations on multiple resources.

        Args:
            operation: "activate" | "deactivate" | "delete"
            resource_ids: List of resource UUIDs
            admin_id: Admin ID

        Returns:
            Status message dict

        Raises:
            HTTPException: Invalid operation
        """
        if operation == "activate":
            await self.repository.batch_update(
                resource_ids,
                {"is_active": True, "updated_by": admin_id}
            )
            return {"message": f"Activated {len(resource_ids)} resources"}

        elif operation == "deactivate":
            await self.repository.batch_update(
                resource_ids,
                {"is_active": False, "updated_by": admin_id}
            )
            return {"message": f"Deactivated {len(resource_ids)} resources"}

        elif operation == "delete":
            # Soft delete
            await self.repository.batch_update(
                resource_ids,
                {"is_active": False, "updated_by": admin_id}
            )
            return {"message": f"Deleted {len(resource_ids)} resources"}

        else:
            raise HTTPException(400, f"Unknown action: {operation}")

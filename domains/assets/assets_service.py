"""
Assets Service - Business logic for user assets management.

@module domains.assets.assets_service
@version 1.1.0 (DDD Exception Compliance)

Changes:
- v1.1.0: DDD-compliant exceptions
  - Removed all HTTPException (replaced with domain exceptions)
  - API layer now responsible for HTTP status code mapping
- v1.0.0: Initial implementation

Purpose:
- Asset CRUD business logic
- File upload validation and storage
- SSRF protection for external URLs
- URL validity checking
- Dashboard statistics aggregation
"""

import uuid
import logging
import ipaddress
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from fastapi import UploadFile

from infrastructure.repositories.asset_repository import SupabaseAssetRepository
from domains.assets.exceptions import (
    InvalidUrlException,
    SsrfException,
    UrlNotAccessibleException,
    InvalidFileTypeException,
    FileTooLargeException,
    NotImageException,
    ProTierRequiredException,
    AssetNotFoundException,
    StorageNotConfiguredException,
    UploadFailedException,
)

logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_FILE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']
MAX_URL_LENGTH = 2048
BUCKET_NAME = "make-decodables-u"  # User content bucket (same as shared.ai.image_generator)


class AssetsService:
    """
    Domain service for Assets management.

    Handles all business logic for user asset operations.
    """

    def __init__(self, repository: SupabaseAssetRepository, storage_client):
        """
        Initialize service.

        Args:
            repository: Data access repository
            storage_client: Supabase client for storage operations
        """
        self.repository = repository
        self.storage = storage_client

    # ==========================================
    # Helper Methods - SSRF Protection
    # ==========================================

    def _is_private_ip(self, hostname: str) -> bool:
        """Check if hostname resolves to private/internal IP."""
        import socket
        try:
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)

            return (
                ip_obj.is_private or
                ip_obj.is_loopback or
                ip_obj.is_link_local or
                ip_obj.is_reserved or
                ip_obj.is_multicast
            )
        except (socket.gaierror, ValueError):
            return True

    def _validate_url_safe(self, url: str) -> None:
        """
        Validate URL is safe (no SSRF).

        Raises:
            InvalidUrlException: If URL format is invalid
            SsrfException: If URL points to internal network
        """
        if len(url) > MAX_URL_LENGTH:
            raise InvalidUrlException("URL too long")

        if not url.startswith(('http://', 'https://')):
            raise InvalidUrlException("Invalid URL protocol")

        try:
            parsed = urlparse(url)
            hostname = parsed.hostname

            if not hostname:
                raise InvalidUrlException("Invalid URL format")

            if self._is_private_ip(hostname):
                raise SsrfException()

            blocked_hostnames = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
            if hostname.lower() in blocked_hostnames:
                raise SsrfException()

        except (InvalidUrlException, SsrfException):
            raise
        except Exception:
            raise InvalidUrlException("Invalid URL format")

    # ==========================================
    # Query Methods
    # ==========================================

    async def get_user_assets(
        self,
        user_id: str,
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user assets with optional project filter (legacy, no pagination).

        Args:
            user_id: User ID
            project_id: Optional project ID filter

        Returns:
            List of asset dicts
        """
        return await self.repository.get_assets(user_id, project_id)

    async def get_user_assets_paginated(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get user assets with pagination.

        Args:
            user_id: User ID
            project_id: Optional project ID filter
            offset: Number of items to skip
            limit: Max items to return

        Returns:
            Dict with items, total, has_more
        """
        items, total = await self.repository.get_assets_paginated(
            user_id, project_id, offset=offset, limit=limit
        )
        return {
            "items": items,
            "total": total,
            "has_more": offset + len(items) < total
        }

    async def check_url_validity(self, url: str) -> Dict[str, Any]:
        """
        Check if URL is valid and points to an image.

        Business logic:
        1. Validate URL length
        2. Check SSRF (private IP)
        3. Validate URL format
        4. Check URL accessibility
        5. Verify content type

        Args:
            url: URL to check

        Returns:
            Dict with valid status, content_type, status_code
        """
        import httpx

        # Length check
        if len(url) > MAX_URL_LENGTH:
            return {"valid": False, "error": "URL too long"}

        if not url.startswith(('http://', 'https://')):
            return {"valid": False, "error": "Invalid URL format"}

        # SSRF check
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            if not hostname or self._is_private_ip(hostname):
                return {"valid": False, "error": "Invalid URL"}
        except Exception:
            return {"valid": False, "error": "Invalid URL"}

        # Accessibility check
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
            return {"valid": False, "error": "Failed to access URL"}

    async def get_dashboard_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get asset dashboard statistics.

        Args:
            user_id: User ID

        Returns:
            Dashboard stats dict
        """
        return await self.repository.get_dashboard_stats(user_id)

    async def get_seller_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get seller marketplace statistics.

        Args:
            user_id: User ID

        Returns:
            Seller stats dict
        """
        return await self.repository.get_seller_stats(user_id)

    async def get_deleted_assets(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get soft-deleted assets (recoverable only) - legacy method.

        Only returns assets within recovery period.
        Expired assets are automatically filtered out.

        Args:
            user_id: User ID
            limit: Max results per page
            offset: Results to skip for pagination

        Returns:
            Tuple of (list of asset dicts, total count)
        """
        # Use BaseRepository method to auto-filter expired records
        assets, total = await self.repository.list_deleted_recoverable(
            user_id=user_id,
            offset=offset,
            limit=limit
        )

        # Convert Asset entities to dicts for backward compatibility
        asset_dicts = []
        for asset in assets:
            asset_dicts.append({
                "id": asset.id,
                "filename": asset.filename,
                "file_type": asset.file_type,
                "file_url": asset.file_url,
                "thumbnail_url": asset.thumbnail_url,
                "deleted_at": asset.deleted_at,
                "recovery_expires_at": asset.recovery_expires_at,
            })

        return asset_dicts, total

    async def get_deleted_assets_paginated(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get soft-deleted assets with pagination response format.

        Args:
            user_id: User ID
            offset: Number of items to skip
            limit: Max items to return

        Returns:
            Dict with items, total, has_more
        """
        items, total = await self.get_deleted_assets(user_id, limit=limit, offset=offset)
        return {
            "items": items,
            "total": total,
            "has_more": offset + len(items) < total
        }

    # ==========================================
    # Command Methods
    # ==========================================

    async def upload_asset(
        self,
        user_id: str,
        user_tier: str,
        file: UploadFile,
        project_id: Optional[str],
        timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """
        Upload asset with Pro check and file validation.

        Business logic:
        1. Check Pro tier requirement
        2. Validate file type
        3. Validate file size
        4. Upload to Storage
        5. Save to database

        Args:
            user_id: User ID
            user_tier: User tier (must be "t3")
            file: Uploaded file
            project_id: Optional project ID
            timezone: User timezone

        Returns:
            Dict with url and filename

        Raises:
            ProTierRequiredException: If user is not Pro tier
            InvalidFileTypeException: If file type is not allowed
            FileTooLargeException: If file exceeds size limit
            StorageNotConfiguredException: If storage is not available
            UploadFailedException: If upload fails
        """
        # 1. Pro tier check
        if user_tier.lower() != "t3":
            raise ProTierRequiredException()

        # 2. File type validation
        if file.content_type not in ALLOWED_FILE_TYPES:
            raise InvalidFileTypeException(content_type=file.content_type)

        # 3. File size validation
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise FileTooLargeException(max_size_mb=5)

        # 4. Storage check
        if not self.storage:
            raise StorageNotConfiguredException()

        # 5. Generate unique filename
        ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
        filename = f"{user_id}/uploads/{uuid.uuid4()}.{ext}"

        # 6. Upload to Storage
        try:
            await self.storage.storage.from_(BUCKET_NAME).upload(
                path=filename,
                file=contents,
                file_options={"content-type": file.content_type}
            )
            url = self.storage.storage.from_(BUCKET_NAME).get_public_url(filename)
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise UploadFailedException(reason=str(e))

        # 7. Save to database
        await self.repository.save_asset(
            user_id,
            url,
            "uploaded",
            project_id,
            tz=timezone
        )

        return {"url": url, "filename": filename}

    async def add_asset_from_url(
        self,
        user_id: str,
        url: str,
        project_id: Optional[str],
        timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """
        Add asset from external URL with SSRF protection.

        Business logic:
        1. Validate URL safety (SSRF)
        2. Check URL accessibility
        3. Verify content type (image)
        4. Save to database

        Args:
            user_id: User ID
            url: External URL
            project_id: Optional project ID
            timezone: User timezone

        Returns:
            Dict with status and asset

        Raises:
            InvalidUrlException: If URL format is invalid
            SsrfException: If URL points to internal network
            UrlNotAccessibleException: If URL cannot be accessed
            NotImageException: If URL does not point to an image
        """
        import httpx

        # 1. SSRF validation
        self._validate_url_safe(url)

        # 2. Check URL accessibility
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.head(url, follow_redirects=True)
                if response.status_code != 200:
                    raise UrlNotAccessibleException(status_code_http=response.status_code)

                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    raise NotImageException()
        except httpx.RequestError:
            raise UrlNotAccessibleException(reason="Failed to access URL")

        # 3. Save to database
        asset = await self.repository.save_asset(
            user_id,
            url,
            "external",
            project_id,
            tz=timezone
        )

        return {"status": "ok", "asset": asset}

    async def delete_asset(
        self,
        asset_id: str,
        user_id: str,
        permanent: bool = False
    ) -> Dict[str, str]:
        """
        Delete asset (soft or permanent).

        Args:
            asset_id: Asset ID
            user_id: User ID
            permanent: If True, permanently delete; otherwise soft delete

        Returns:
            Dict with status, action, asset_id

        Raises:
            AssetNotFoundException: If asset not found or not owned by user
        """
        if permanent:
            result = await self.repository.permanently_hide_asset(asset_id, user_id)
            action = "permanently deleted"
        else:
            result = await self.repository.soft_delete_asset(asset_id, user_id)
            action = "moved to trash"

        if not result:
            raise AssetNotFoundException(asset_id=asset_id)

        return {"status": "ok", "action": action, "asset_id": asset_id}

    async def increment_asset_usage(
        self,
        asset_id: str,
        user_id: str
    ) -> int:
        """
        Increment asset usage count.

        Args:
            asset_id: Asset ID
            user_id: User ID

        Returns:
            New usage count

        Raises:
            AssetNotFoundException: If asset not found
        """
        result = await self.repository.increment_asset_usage(asset_id, user_id)
        if not result:
            raise AssetNotFoundException(asset_id=asset_id)

        return result.get("usage_count", 0)

    async def restore_asset(
        self,
        asset_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Restore soft-deleted asset.

        Args:
            asset_id: Asset ID
            user_id: User ID

        Returns:
            Restored asset dict

        Raises:
            AssetNotFoundException: If asset not found in trash
        """
        result = await self.repository.restore_asset(asset_id, user_id)
        if not result:
            raise AssetNotFoundException(asset_id=asset_id, in_trash=True)

        return result

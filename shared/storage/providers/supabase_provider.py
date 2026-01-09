"""
Supabase Storage Provider - Concrete implementation of IStorageService.

This provider wraps Supabase Storage API to provide a class-based interface
compatible with the shared layer.

@module shared.storage.providers.supabase_provider
@version 1.0.0
"""

from typing import Optional, List, Union, BinaryIO
import logging
import httpx
import os

from shared.storage.interfaces import IStorageService
from shared.storage.types import (
    StorageVisibility,
    UploadResult,
    DeleteResult,
    FileInfo,
)

logger = logging.getLogger(__name__)


class SupabaseStorageProvider(IStorageService):
    """
    Supabase storage provider implementation.

    This class wraps the Supabase Storage API to provide a clean interface
    that matches IStorageService.

    Note: Supabase client is imported from domains.platform.config_service to avoid
    duplication of initialization logic.
    """

    provider_name: str = "supabase"

    def __init__(self, supabase_client=None):
        """
        Initialize Supabase storage provider.

        Args:
            supabase_client: Optional Supabase client instance.
                           If None, will create from environment variables
        """
        if supabase_client:
            self._client = supabase_client
        else:
            # Create Supabase client from environment variables
            from supabase import create_client
            supabase_url = os.environ.get("SUPABASE_URL")
            supabase_key = os.environ.get("SUPABASE_KEY")

            if supabase_url and supabase_key:
                # Ensure URL has trailing slash
                if not supabase_url.endswith('/'):
                    supabase_url = supabase_url + '/'
                self._client = create_client(supabase_url, supabase_key)
            else:
                self._client = None
                logger.warning("[SupabaseStorageProvider] Supabase credentials not found in environment")

        if not self._client:
            logger.warning("[SupabaseStorageProvider] Supabase client not initialized")

    # ==========================================
    # File Upload
    # ==========================================

    async def upload_file(
        self,
        bucket: str,
        path: str,
        file_data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
        visibility: StorageVisibility = StorageVisibility.PUBLIC
    ) -> UploadResult:
        """
        Upload a file to Supabase storage.

        Args:
            bucket: Bucket name
            path: File path within bucket
            file_data: File content as bytes or file-like object
            content_type: MIME type
            visibility: File visibility level (always public in Supabase)

        Returns:
            UploadResult with URL and metadata
        """
        try:
            # Read file data if it's a file-like object
            if hasattr(file_data, 'read'):
                file_data = file_data.read()

            # Upload to Supabase
            result = self._client.storage.from_(bucket).upload(
                path=path,
                file=file_data,
                file_options={"content-type": content_type} if content_type else None
            )

            # Get public URL
            url = self._client.storage.from_(bucket).get_public_url(path)

            return UploadResult(
                success=True,
                url=url,
                path=path,
                size=len(file_data) if isinstance(file_data, bytes) else None
            )

        except Exception as e:
            logger.error(f"[SupabaseStorage] Upload error for {bucket}/{path}: {e}")
            return UploadResult(
                success=False,
                error=str(e)
            )

    async def upload_from_url(
        self,
        bucket: str,
        path: str,
        source_url: str,
        content_type: Optional[str] = None
    ) -> UploadResult:
        """
        Upload a file from a URL.

        Args:
            bucket: Bucket name
            path: Destination path
            source_url: Source file URL to download from
            content_type: MIME type

        Returns:
            UploadResult with URL and metadata
        """
        try:
            # Download file from URL
            async with httpx.AsyncClient() as client:
                response = await client.get(source_url, timeout=30.0)
                response.raise_for_status()
                file_data = response.content

            # Upload to Supabase
            return await self.upload_file(
                bucket=bucket,
                path=path,
                file_data=file_data,
                content_type=content_type or response.headers.get('content-type')
            )

        except Exception as e:
            logger.error(f"[SupabaseStorage] Upload from URL error: {e}")
            return UploadResult(
                success=False,
                error=str(e)
            )

    # ==========================================
    # File Retrieval
    # ==========================================

    def get_public_url(
        self,
        bucket: str,
        path: str
    ) -> str:
        """
        Get public URL for a file.

        Args:
            bucket: Bucket name
            path: File path within bucket

        Returns:
            Public URL string
        """
        try:
            return self._client.storage.from_(bucket).get_public_url(path)
        except Exception as e:
            logger.error(f"[SupabaseStorage] Get public URL error: {e}")
            return ""

    async def get_file_info(
        self,
        bucket: str,
        path: str
    ) -> Optional[FileInfo]:
        """
        Get file metadata.

        Note: Supabase doesn't have a direct metadata API,
        so we return basic info with the public URL.
        """
        try:
            url = self.get_public_url(bucket, path)
            return FileInfo(
                path=path,
                url=url
            )
        except Exception as e:
            logger.error(f"[SupabaseStorage] Get file info error: {e}")
            return None

    async def download_file(
        self,
        bucket: str,
        path: str
    ) -> Optional[bytes]:
        """
        Download file content.

        Args:
            bucket: Bucket name
            path: File path within bucket

        Returns:
            File content as bytes, or None if not found
        """
        try:
            result = self._client.storage.from_(bucket).download(path)
            return result
        except Exception as e:
            logger.error(f"[SupabaseStorage] Download error: {e}")
            return None

    # ==========================================
    # File Management
    # ==========================================

    async def delete_file(
        self,
        bucket: str,
        path: str
    ) -> DeleteResult:
        """
        Delete a file.

        Args:
            bucket: Bucket name
            path: File path within bucket

        Returns:
            DeleteResult with success status
        """
        try:
            self._client.storage.from_(bucket).remove([path])

            return DeleteResult(
                success=True,
                path=path
            )

        except Exception as e:
            logger.error(f"[SupabaseStorage] Delete error: {e}")
            return DeleteResult(
                success=False,
                path=path,
                error=str(e)
            )

    async def list_files(
        self,
        bucket: str,
        prefix: Optional[str] = None,
        limit: int = 100
    ) -> List[FileInfo]:
        """
        List files in a bucket/prefix.

        Args:
            bucket: Bucket name
            prefix: Path prefix to filter by
            limit: Maximum number of files to return

        Returns:
            List of FileInfo objects
        """
        try:
            result = self._client.storage.from_(bucket).list(
                path=prefix or "",
                options={"limit": limit}
            )

            files = []
            for item in result:
                files.append(FileInfo(
                    path=item.get("name", ""),
                    size=item.get("metadata", {}).get("size"),
                    created_at=item.get("created_at"),
                    updated_at=item.get("updated_at")
                ))

            return files

        except Exception as e:
            logger.error(f"[SupabaseStorage] List files error: {e}")
            return []

    # ==========================================
    # Bucket Management
    # ==========================================

    async def create_bucket(
        self,
        bucket: str,
        public: bool = True
    ) -> bool:
        """
        Create a new storage bucket.

        Args:
            bucket: Bucket name
            public: Whether bucket should be public

        Returns:
            True if created successfully
        """
        try:
            self._client.storage.create_bucket(
                id=bucket,
                options={"public": public}
            )
            return True

        except Exception as e:
            logger.error(f"[SupabaseStorage] Create bucket error: {e}")
            return False

    async def bucket_exists(
        self,
        bucket: str
    ) -> bool:
        """
        Check if a bucket exists.

        Args:
            bucket: Bucket name

        Returns:
            True if bucket exists
        """
        try:
            buckets = self._client.storage.list_buckets()
            return any(b.id == bucket for b in buckets)

        except Exception as e:
            logger.error(f"[SupabaseStorage] Bucket exists check error: {e}")
            return False

    # ==========================================
    # Utility
    # ==========================================

    def is_configured(self) -> bool:
        """
        Check if Supabase is properly configured.

        Returns True if client is initialized.
        """
        return self._client is not None and bool(os.environ.get("SUPABASE_URL"))

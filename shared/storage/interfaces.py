"""
Storage Service Interfaces - Abstract base classes for storage providers.

Defines the contracts that all storage service providers must implement.
This enables dependency inversion: domains depend on these abstractions,
not on concrete implementations (Supabase, S3, Azure Blob, etc.).

@module shared.storage.interfaces
@version 1.0.0
"""

from abc import ABC, abstractmethod
from typing import Optional, List, BinaryIO, Union
from .types import UploadResult, DeleteResult, FileInfo, StorageVisibility


# ==========================================
# Abstract Interfaces
# ==========================================

class IStorageService(ABC):
    """
    Abstract interface for storage services.

    All storage providers (Supabase, S3, Azure, etc.) must implement this
    interface to be compatible with the domain layer.
    """

    provider_name: str = "base"

    # ==========================================
    # File Upload
    # ==========================================

    @abstractmethod
    async def upload_file(
        self,
        bucket: str,
        path: str,
        file_data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
        visibility: StorageVisibility = StorageVisibility.PUBLIC
    ) -> UploadResult:
        """
        Upload a file to storage.

        Args:
            bucket: Bucket/container name
            path: File path within bucket (e.g., "images/user123/avatar.png")
            file_data: File content as bytes or file-like object
            content_type: MIME type (e.g., "image/png")
            visibility: File visibility level

        Returns:
            UploadResult with URL and metadata

        Raises:
            May raise provider-specific exceptions
        """
        pass

    @abstractmethod
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
            bucket: Bucket/container name
            path: Destination path
            source_url: Source file URL to download from
            content_type: MIME type

        Returns:
            UploadResult with URL and metadata

        Raises:
            May raise provider-specific exceptions
        """
        pass

    # ==========================================
    # File Retrieval
    # ==========================================

    @abstractmethod
    def get_public_url(
        self,
        bucket: str,
        path: str
    ) -> str:
        """
        Get public URL for a file.

        Args:
            bucket: Bucket/container name
            path: File path within bucket

        Returns:
            Public URL string

        Note:
            This should work for both public and signed URLs
        """
        pass

    @abstractmethod
    async def get_file_info(
        self,
        bucket: str,
        path: str
    ) -> Optional[FileInfo]:
        """
        Get file metadata.

        Args:
            bucket: Bucket/container name
            path: File path within bucket

        Returns:
            FileInfo or None if file doesn't exist

        Raises:
            May raise provider-specific exceptions
        """
        pass

    @abstractmethod
    async def download_file(
        self,
        bucket: str,
        path: str
    ) -> Optional[bytes]:
        """
        Download file content.

        Args:
            bucket: Bucket/container name
            path: File path within bucket

        Returns:
            File content as bytes, or None if not found

        Raises:
            May raise provider-specific exceptions
        """
        pass

    # ==========================================
    # File Management
    # ==========================================

    @abstractmethod
    async def delete_file(
        self,
        bucket: str,
        path: str
    ) -> DeleteResult:
        """
        Delete a file.

        Args:
            bucket: Bucket/container name
            path: File path within bucket

        Returns:
            DeleteResult with success status

        Raises:
            May raise provider-specific exceptions
        """
        pass

    @abstractmethod
    async def list_files(
        self,
        bucket: str,
        prefix: Optional[str] = None,
        limit: int = 100
    ) -> List[FileInfo]:
        """
        List files in a bucket/prefix.

        Args:
            bucket: Bucket/container name
            prefix: Path prefix to filter by (e.g., "images/user123/")
            limit: Maximum number of files to return

        Returns:
            List of FileInfo objects

        Raises:
            May raise provider-specific exceptions
        """
        pass

    # ==========================================
    # Bucket Management
    # ==========================================

    @abstractmethod
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

        Raises:
            May raise provider-specific exceptions
        """
        pass

    @abstractmethod
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

        Raises:
            May raise provider-specific exceptions
        """
        pass

    # ==========================================
    # Utility
    # ==========================================

    def is_configured(self) -> bool:
        """
        Check if storage provider is properly configured.

        Returns:
            True if provider can be used (credentials configured, etc.)
        """
        return True

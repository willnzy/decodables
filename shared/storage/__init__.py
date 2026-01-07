"""
Shared Storage Service Layer - Abstractions for storage providers.

This module provides:
- Abstract interfaces for storage services
- Standardized request/response types
- Provider-agnostic file operations
- Common data structures for uploads, downloads, and metadata

@module shared.storage
@version 1.0.0
"""

from .interfaces import IStorageService

from .types import (
    StorageVisibility,
    UploadResult,
    DeleteResult,
    FileInfo,
)

__all__ = [
    # Interfaces
    "IStorageService",
    # Enums
    "StorageVisibility",
    # Types
    "UploadResult",
    "DeleteResult",
    "FileInfo",
]

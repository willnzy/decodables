"""
Storage Service Types - Common data structures for storage operations.

@module shared.storage.types
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


# ==========================================
# Enums
# ==========================================

class StorageVisibility(str, Enum):
    """File visibility level."""
    PUBLIC = "public"
    PRIVATE = "private"


# ==========================================
# Data Classes
# ==========================================

@dataclass
class UploadResult:
    """
    File upload result.

    Attributes:
        success: Whether upload succeeded
        url: Public URL to access the file
        path: Storage path of the file
        size: File size in bytes
        error: Error message if failed
    """
    success: bool
    url: Optional[str] = None
    path: Optional[str] = None
    size: Optional[int] = None
    error: Optional[str] = None


@dataclass
class DeleteResult:
    """
    File deletion result.

    Attributes:
        success: Whether deletion succeeded
        path: Path of deleted file
        error: Error message if failed
    """
    success: bool
    path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class FileInfo:
    """
    File metadata information.

    Attributes:
        path: File path in storage
        url: Public URL (if public)
        size: File size in bytes
        content_type: MIME type
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    path: str
    url: Optional[str] = None
    size: Optional[int] = None
    content_type: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

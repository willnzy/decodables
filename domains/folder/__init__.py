"""
Folder Domain

Domain layer for folder management.

@module domains.folder
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 2.6)
"""

from domains.folder.entities import Folder, FolderColor, FolderType
from domains.folder.repository import IFolderRepository
from domains.folder.service import FolderService

__all__ = [
    "Folder",
    "FolderColor",
    "FolderType",
    "IFolderRepository",
    "FolderService",
]

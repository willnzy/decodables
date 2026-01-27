"""
Workspace Domain

Phase 1: Silent backend support for user workspaces.
Users don't see workspace UI, but data is organized by workspace.

@module domains.workspace
@version 1.0.0 (created for v3.33 Workspace + Tag Phase 1)
"""

from .entities import Workspace
from .repository import IWorkspaceRepository
from .service import WorkspaceService

__all__ = [
    "Workspace",
    "IWorkspaceRepository",
    "WorkspaceService",
]

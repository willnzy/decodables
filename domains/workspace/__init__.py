"""
Workspace Domain

Phase 1: Silent backend support for user workspaces.
Phase 2: Multi-workspace creation with tier-based quota.
Phase 5: Member invitation and management.

@module domains.workspace
@version 2.0.0 (Phase 5: Member management)
"""

from .entities import Workspace
from .repository import IWorkspaceRepository
from .service import WorkspaceService
from .member_entities import WorkspaceMember, WorkspaceInvitation
from .member_repository import IMemberRepository
from .member_service import MemberService

__all__ = [
    "Workspace",
    "IWorkspaceRepository",
    "WorkspaceService",
    "WorkspaceMember",
    "WorkspaceInvitation",
    "IMemberRepository",
    "MemberService",
]

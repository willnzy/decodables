"""
Workspace Members Router - Member management endpoints (v3.33 Phase 5)

@module api.user.workspace_members
@version 1.0.0

Endpoints:
- GET    /api/v2/user/workspaces/{id}/members         - List workspace members
- POST   /api/v2/user/workspaces/{id}/members/invite   - Invite a member
- PATCH  /api/v2/user/workspaces/{id}/members/{mid}     - Update member role
- DELETE /api/v2/user/workspaces/{id}/members/{mid}     - Remove member
- GET    /api/v2/user/workspaces/{id}/invitations       - List workspace invitations
"""

from typing import Optional

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel, Field

from domains.identity.aggregates.user_profile import UserProfile
from infrastructure.logging.activity_logger import log_activity_async
from infrastructure.rate_limiter import limiter
from dependencies import get_current_user
from container import get_container
from core.utils.validation import validate_uuid

router = APIRouter(prefix="/workspaces", tags=["workspace-members-v1"])

# WS4: UUID validation centralized to core.utils.validation


# ==========================================
# Request Models
# ==========================================

class InviteMemberRequest(BaseModel):
    """Request to invite a member by email."""
    email: str = Field(min_length=3, max_length=254)
    role: str = Field(default="member", pattern="^member$")


class UpdateMemberRoleRequest(BaseModel):
    """Request to update a member's role."""
    role: str = Field(pattern="^member$")


# ==========================================
# Member Endpoints
# ==========================================

@router.get("/{workspace_id}/members")
@limiter.limit("60/minute")
async def list_members(
    request: Request,
    workspace_id: str,
    user: UserProfile = Depends(get_current_user),
):
    """
    List all members of a workspace.

    Requires: User must be a member or owner.
    """
    validate_uuid(workspace_id, "workspace_id")

    container = get_container()
    member_service = await container.get_member_service()

    try:
        members = await member_service.list_members(workspace_id, user.user_id)
    except ValueError as e:
        raise HTTPException(403, str(e))

    # Also include workspace owner info
    workspace_service = await container.get_workspace_service()
    workspace = await workspace_service.get_by_id(workspace_id)

    return {
        "items": [m.to_dict() for m in members],
        "total": len(members),
        "workspace_owner_id": workspace.owner_id if workspace else None,
    }


@router.post("/{workspace_id}/members/invite")
@limiter.limit("20/minute")
async def invite_member(
    request: Request,
    workspace_id: str,
    data: InviteMemberRequest,
    user: UserProfile = Depends(get_current_user),
):
    """
    Invite a member to a workspace by email.

    Requires: User must be the workspace owner.
    """
    validate_uuid(workspace_id, "workspace_id")

    container = get_container()
    member_service = await container.get_member_service()

    try:
        invitation = await member_service.invite_member(
            workspace_id=workspace_id,
            inviter_id=user.user_id,
            email=data.email,
            role=data.role,
        )
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))

    await log_activity_async(
        user_id=user.user_id,
        action="workspace_member_invited",
        metadata={
            "workspace_id": workspace_id,
            "invited_email": data.email,
        },
    )

    return invitation.to_dict()


@router.patch("/{workspace_id}/members/{member_id}")
@limiter.limit("20/minute")
async def update_member_role(
    request: Request,
    workspace_id: str,
    member_id: str,
    data: UpdateMemberRoleRequest,
    user: UserProfile = Depends(get_current_user),
):
    """
    Update a workspace member's role.

    Requires: User must be the workspace owner.
    """
    validate_uuid(workspace_id, "workspace_id")
    validate_uuid(member_id, "member_id")

    container = get_container()
    member_service = await container.get_member_service()

    try:
        updated = await member_service.update_member_role(
            workspace_id=workspace_id,
            updater_id=user.user_id,
            target_member_id=member_id,
            new_role=data.role,
        )
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))

    return updated.to_dict()


@router.delete("/{workspace_id}/members/{member_id}")
@limiter.limit("20/minute")
async def remove_member(
    request: Request,
    workspace_id: str,
    member_id: str,
    user: UserProfile = Depends(get_current_user),
):
    """
    Remove a member from a workspace.

    Requires: User must be the workspace owner.
    """
    validate_uuid(workspace_id, "workspace_id")
    validate_uuid(member_id, "member_id")

    container = get_container()
    member_service = await container.get_member_service()

    try:
        await member_service.remove_member(
            workspace_id=workspace_id,
            remover_id=user.user_id,
            target_member_id=member_id,
        )
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))

    await log_activity_async(
        user_id=user.user_id,
        action="workspace_member_removed",
        metadata={
            "workspace_id": workspace_id,
            "member_id": member_id,
        },
    )

    return {"success": True, "message": "Member removed"}


@router.get("/{workspace_id}/invitations")
@limiter.limit("30/minute")
async def list_workspace_invitations(
    request: Request,
    workspace_id: str,
    user: UserProfile = Depends(get_current_user),
):
    """
    List all invitations for a workspace.

    Requires: User must be the workspace owner.
    """
    validate_uuid(workspace_id, "workspace_id")

    container = get_container()
    member_service = await container.get_member_service()

    try:
        invitations = await member_service.list_workspace_invitations(
            workspace_id, user.user_id
        )
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "items": [inv.to_dict() for inv in invitations],
        "total": len(invitations),
    }
